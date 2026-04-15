from __future__ import annotations

from pathlib import Path
from typing import Any

import requests


class BaleBot:
    def __init__(self, token: str, api_base: str, timeout: int = 30) -> None:
        base = api_base.rstrip("/")
        self.base = f"{base}/bot{token}"
        self.file_base = f"{base}/file/bot{token}"
        self.timeout = timeout

    def get_updates(self, offset: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"timeout": self.timeout}
        if offset is not None:
            params["offset"] = offset
        resp = requests.get(f"{self.base}/getUpdates", params=params, timeout=self.timeout + 5)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", []) if data.get("ok") else []

    def send_text(self, chat_id: int | str, text: str) -> None:
        resp = requests.post(
            f"{self.base}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=30,
        )
        resp.raise_for_status()

    def get_file_path(self, file_id: str) -> str:
        resp = requests.get(f"{self.base}/getFile", params={"file_id": file_id}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError("Bale getFile failed")
        return data["result"]["file_path"]

    def download_file(self, file_id: str, output_path: str | Path) -> Path:
        remote = self.get_file_path(file_id)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        with requests.get(f"{self.file_base}/{remote}", stream=True, timeout=120) as r:
            r.raise_for_status()
            with out.open("wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        return out
