from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from server_a.bale_client import BaleClient
from server_a.splitter import split_file
from server_a.state import JsonState
from server_a.telegram_bot import TelegramBot
from shared import protocol
from shared.utils import file_size, make_job_id, sha256_file

PART_SIZE = 20 * 1024 * 1024


def setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def handle_telegram_file(
    message: dict,
    tg: TelegramBot,
    bale: BaleClient,
    job_state: JsonState,
    bale_chat_id: str,
    work_dir: Path,
) -> None:
    doc = message.get("document")
    if not doc:
        return

    chat_id = message["chat"]["id"]
    file_id = doc["file_id"]
    filename = doc.get("file_name") or f"file_{file_id}"

    incoming_dir = work_dir / "incoming"
    parts_dir = work_dir / "parts"

    job_id = make_job_id()
    local_path = tg.download_file(file_id, incoming_dir / filename)
    checksum = sha256_file(local_path)
    size = file_size(local_path)

    job_part_dir = parts_dir / job_id
    parts = split_file(local_path, job_part_dir, PART_SIZE)

    start_text = protocol.dumps(
        protocol.JOB_START,
        {
            "job_id": job_id,
            "original_filename": filename,
            "total_parts": len(parts),
            "original_size": size,
            "sha256": checksum,
        },
    )
    bale.send_text(bale_chat_id, start_text)

    for i, part_path in enumerate(parts):
        caption = protocol.dumps(
            protocol.PART,
            {
                "job_id": job_id,
                "part_index": i,
                "total_parts": len(parts),
                "part_filename": part_path.name,
            },
        )
        bale.send_document(bale_chat_id, part_path, caption)

    bale.send_text(bale_chat_id, protocol.dumps(protocol.JOB_DONE, {"job_id": job_id}))
    job_state.set(job_id, {"telegram_chat_id": chat_id, "filename": filename})
    tg.send_text(chat_id, f"Upload received. Job {job_id} sent to relay.")


def handle_bale_text(update: dict, tg: TelegramBot, job_state: JsonState) -> None:
    message = update.get("message", {})
    text = message.get("text")
    parsed = protocol.loads(text or "")
    if not parsed or parsed.kind != protocol.LINK_READY:
        return

    job_id = parsed.payload.get("job_id")
    download_url = parsed.payload.get("download_url")
    if not job_id or not download_url:
        return

    mapping = job_state.get(job_id)
    if not mapping:
        logging.warning("No job mapping for %s", job_id)
        return

    tg.send_text(mapping["telegram_chat_id"], f"Your file is ready:\n{download_url}")
    job_state.delete(job_id)


def main() -> None:
    load_dotenv()
    setup_logging()

    tg_token = os.environ["TELEGRAM_BOT_TOKEN"]
    bale_token = os.environ["BALE_BOT_TOKEN"]
    bale_api_base = os.environ["BALE_API_BASE"]
    bale_chat_id = os.environ["BALE_CHAT_ID"]

    work_dir = Path(os.getenv("A_WORK_DIR", "data/server_a"))
    work_dir.mkdir(parents=True, exist_ok=True)

    tg = TelegramBot(tg_token)
    bale = BaleClient(bale_token, bale_api_base)
    job_state = JsonState(work_dir / "jobs.json")

    tg_offset: int | None = None
    bale_offset: int | None = None

    logging.info("Server A started")

    while True:
        try:
            for update in tg.get_updates(tg_offset):
                tg_offset = update["update_id"] + 1
                message = update.get("message", {})
                if message.get("document"):
                    handle_telegram_file(message, tg, bale, job_state, bale_chat_id, work_dir)

            for update in bale.get_updates(bale_offset):
                bale_offset = update["update_id"] + 1
                handle_bale_text(update, tg, job_state)

        except Exception:
            logging.exception("Main loop error on server A")
            time.sleep(2)


if __name__ == "__main__":
    main()
