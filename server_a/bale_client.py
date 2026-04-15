from __future__ import annotations

from pathlib import Path
from typing import Any

import requests


class BaleClient:
    def __init__(self, token: str, api_base: str, timeout: int = 30) -> None:
        base = api_base.rstrip("/")
        self.base = f"{base}/bot{token}"
        self.timeout = timeout

    def get_updates(self, offset: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"timeout": self.timeout}
        if offset is not None:
            params["offset"] = offset
        resp = requests.get(f"{self.base}/getUpdates", params=params, timeout=self.timeout + 5)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            return []
        return data.get("result", [])

    def send_text(self, chat_id: int | str, text: str) -> None:
        resp = requests.post(
            f"{self.base}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=30,
        )
        resp.raise_for_status()

    def send_document(self, chat_id: int | str, file_path: str | Path, caption: str) -> None:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id, "caption": caption}
            resp = requests.post(f"{self.base}/sendDocument", data=data, files=files, timeout=180)
            resp.raise_for_status()
