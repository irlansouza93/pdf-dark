"""Verificações estruturais do pacote."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

import pdf_dark


def test_all_sources_compile() -> None:
    package_dir = Path(pdf_dark.__file__).parent
    for path in sorted(package_dir.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")


def test_all_modules_import() -> None:
    pytest.importorskip("tkinter")
    for module in pkgutil.iter_modules(pdf_dark.__path__):
        if module.name == "__main__":
            continue
        importlib.import_module(f"pdf_dark.{module.name}")


def test_icons_are_packaged() -> None:
    assets = Path(pdf_dark.__file__).parent / "assets"
    assert (assets / "icon.png").stat().st_size > 0
    assert (assets / "icon.ico").stat().st_size > 0
