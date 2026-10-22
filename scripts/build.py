"""Gera o executável standalone com PyInstaller.

Uso:
    uv run python scripts/build.py            # CLI + GUI em um único arquivo
    uv run python scripts/build.py --windowed # só GUI (sem console)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "src" / "pdf_dark" / "assets"


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="pdf-dark", help="nome do executável")
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="gera uma versão sem janela de console (apenas interface gráfica)",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "dist"),
        help="pasta onde o executável será gravado",
    )
    args = parser.parse_args(argv)

    if not (ASSETS / "icon.png").exists():
        print("gerando ícones…")
        import subprocess

        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "make_icon.py")], check=True
        )

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        args.name,
        "--paths",
        str(ROOT / "src"),
        "--add-data",
        f"{ASSETS}{os.pathsep}pdf_dark/assets",
        "--collect-all",
        "pypdfium2",
        "--collect-all",
        "pypdfium2_raw",
        "--hidden-import",
        "pdf_dark.app",
        "--collect-submodules",
        "pdf_dark",
        "--distpath",
        args.output,
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT / "build"),
        str(ROOT / "scripts" / "entry.py"),
    ]

    icon = ASSETS / "icon.ico"
    if sys.platform == "win32" and icon.exists():
        command += ["--icon", str(icon)]

    command.append("--windowed" if args.windowed else "--console")

    import subprocess

    print("executando:", " ".join(command))
    subprocess.run(command, check=True)

    suffix = ".exe" if sys.platform == "win32" else ""
    artifact = Path(args.output) / f"{args.name}{suffix}"
    if artifact.exists():
        size = artifact.stat().st_size / (1024 * 1024)
        print(f"\nexecutável pronto: {artifact} ({size:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
