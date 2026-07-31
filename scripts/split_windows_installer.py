#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import math
import os
import shutil
from pathlib import Path


DEFAULT_CHUNK_SIZE = 59 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def split_installer(source: Path, output_dir: Path, chunk_size: int) -> list[Path]:
    if not source.is_file():
        raise FileNotFoundError(f"No existe el instalador: {source}")
    if chunk_size <= 0:
        raise ValueError("El tamaño de fragmento debe ser mayor que cero.")

    output_dir.mkdir(parents=True, exist_ok=True)
    total = math.ceil(source.stat().st_size / chunk_size)
    parts: list[Path] = []
    with source.open("rb") as input_handle:
        for index in range(1, total + 1):
            version = os.environ.get("TLAMATINI_APP_VERSION", "5.2.6").strip() or "5.2.6"
            part = output_dir / f"tlamatini-{version}-windows-installer.chunk-{index:03d}-of-{total:03d}"
            remaining = chunk_size
            with part.open("wb") as output_handle:
                while remaining:
                    block = input_handle.read(min(1024 * 1024, remaining))
                    if not block:
                        break
                    output_handle.write(block)
                    remaining -= len(block)
            parts.append(part)
    return parts


def main() -> int:
    parser = argparse.ArgumentParser(description="Divide el instalador Windows para una release de GitHub.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    args = parser.parse_args()

    parts = split_installer(args.source, args.output_dir, args.chunk_size)
    installer_hash = sha256_file(args.source)
    (args.output_dir / "SHA256-WINDOWS-INSTALADOR.txt").write_text(
        f"{installer_hash}  TLAMATINI-Windows-Instalador-Full.exe\n",
        encoding="ascii",
    )
    part_lines = [f"{sha256_file(part)}  {part.name}" for part in parts]
    (args.output_dir / "SHA256-WINDOWS-PARTES.txt").write_text("\n".join(part_lines) + "\n", encoding="ascii")

    project_root = Path(__file__).resolve().parent.parent
    for helper in ("INSTALAR-TLAMATINI-WINDOWS.ps1", "INSTALAR-TLAMATINI-WINDOWS.cmd"):
        shutil.copy2(project_root / "scripts" / helper, args.output_dir / helper)

    print(f"Instalador dividido en {len(parts)} partes.")
    print(f"SHA256: {installer_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
