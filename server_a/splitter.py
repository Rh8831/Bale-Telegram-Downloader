from __future__ import annotations

from pathlib import Path


def split_file(file_path: str | Path, output_dir: str | Path, part_size_bytes: int) -> list[Path]:
    source = Path(file_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    parts: list[Path] = []
    with source.open("rb") as src:
        idx = 0
        while True:
            chunk = src.read(part_size_bytes)
            if not chunk:
                break
            part_path = out / f"{source.name}.part{idx:04d}"
            with part_path.open("wb") as dst:
                dst.write(chunk)
            parts.append(part_path)
            idx += 1
    return parts
