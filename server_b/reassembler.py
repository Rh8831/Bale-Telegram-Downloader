from __future__ import annotations

from pathlib import Path


def all_parts_present(parts_dir: str | Path, total_parts: int) -> bool:
    p = Path(parts_dir)
    for idx in range(total_parts):
        if not (p / f"part_{idx:04d}").exists():
            return False
    return True


def reassemble(parts_dir: str | Path, output_path: str | Path, total_parts: int) -> Path:
    parts = Path(parts_dir)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("wb") as dst:
        for idx in range(total_parts):
            with (parts / f"part_{idx:04d}").open("rb") as src:
                dst.write(src.read())
    return output
