from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from server_b.bale_listener import BaleBot
from server_b.file_host import FileHost
from server_b.reassembler import all_parts_present, reassemble
from server_b.state import JsonState
from shared import protocol
from shared.utils import sha256_file


def setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def on_job_start(payload: dict, state: JsonState) -> None:
    job_id = payload["job_id"]
    state.set(
        job_id,
        {
            "meta": payload,
            "parts": {},
            "done": False,
        },
    )


def on_part(payload: dict, document: dict, bot: BaleBot, parts_root: Path, state: JsonState) -> None:
    job_id = payload["job_id"]
    part_index = int(payload["part_index"])

    job = state.get(job_id)
    if not job:
        logging.warning("Ignoring part for unknown job %s", job_id)
        return

    part_dir = parts_root / job_id
    file_id = document["file_id"]
    local_part = bot.download_file(file_id, part_dir / f"part_{part_index:04d}")

    job["parts"][str(part_index)] = str(local_part)
    state.set(job_id, job)


def on_job_done(payload: dict, state: JsonState, downloads_dir: Path, bot: BaleBot, reply_chat: str, public_base_url: str) -> None:
    job_id = payload["job_id"]
    job = state.get(job_id)
    if not job:
        logging.warning("Unknown job done %s", job_id)
        return

    meta = job["meta"]
    total_parts = int(meta["total_parts"])
    part_dir = Path(job["parts"].get("0", "")).parent if job["parts"] else Path("missing")

    if not all_parts_present(part_dir, total_parts):
        logging.warning("Not all parts arrived for %s", job_id)
        return

    output_name = f"{job_id}_{meta['original_filename']}"
    output_path = reassemble(part_dir, downloads_dir / output_name, total_parts)
    built_hash = sha256_file(output_path)
    if built_hash != meta["sha256"]:
        logging.error("SHA mismatch for %s", job_id)
        return

    download_url = f"{public_base_url.rstrip('/')}/{output_path.name}"
    msg = protocol.dumps(protocol.LINK_READY, {"job_id": job_id, "download_url": download_url})
    bot.send_text(reply_chat, msg)

    job["done"] = True
    state.set(job_id, job)
    logging.info("Job %s completed", job_id)


def main() -> None:
    load_dotenv()
    setup_logging()

    bale_token = os.environ["BALE_BOT_TOKEN"]
    bale_api_base = os.environ["BALE_API_BASE"]
    bale_chat_id = os.environ["BALE_CHAT_ID"]
    public_base_url = os.environ["PUBLIC_BASE_URL"]

    work_dir = Path(os.getenv("B_WORK_DIR", "data/server_b"))
    parts_dir = work_dir / "parts"
    downloads_dir = work_dir / "downloads"
    state = JsonState(work_dir / "jobs.json")

    host = FileHost(
        directory=downloads_dir,
        host=os.getenv("FILE_HOST", "0.0.0.0"),
        port=int(os.getenv("FILE_PORT", "8080")),
    )
    host.start()

    bot = BaleBot(bale_token, bale_api_base)
    offset: int | None = None

    logging.info("Server B started")

    while True:
        try:
            for update in bot.get_updates(offset):
                offset = update["update_id"] + 1
                message = update.get("message", {})

                if text := message.get("text"):
                    parsed = protocol.loads(text)
                    if not parsed:
                        continue
                    if parsed.kind == protocol.JOB_START:
                        on_job_start(parsed.payload, state)
                    elif parsed.kind == protocol.JOB_DONE:
                        on_job_done(parsed.payload, state, downloads_dir, bot, bale_chat_id, public_base_url)

                if doc := message.get("document"):
                    parsed = protocol.loads(message.get("caption", ""))
                    if parsed and parsed.kind == protocol.PART:
                        on_part(parsed.payload, doc, bot, parts_dir, state)
        except Exception:
            logging.exception("Main loop error on server B")
            time.sleep(2)


if __name__ == "__main__":
    main()
