from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

JOB_START = "JOB_START"
PART = "PART"
JOB_DONE = "JOB_DONE"
LINK_READY = "LINK_READY"


@dataclass
class ProtocolMessage:
    kind: str
    payload: dict[str, Any]


def dumps(kind: str, payload: dict[str, Any]) -> str:
    return f"{kind} {json.dumps(payload, separators=(',', ':'), ensure_ascii=False)}"


def loads(raw: str) -> ProtocolMessage | None:
    if not raw:
        return None

    first_space = raw.find(" ")
    if first_space == -1:
        return None

    kind = raw[:first_space].strip()
    blob = raw[first_space + 1 :].strip()
    if kind not in {JOB_START, PART, JOB_DONE, LINK_READY}:
        return None

    try:
        payload = json.loads(blob)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    return ProtocolMessage(kind=kind, payload=payload)
