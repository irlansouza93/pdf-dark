"""Ponto de entrada usado pelo PyInstaller.

Quando o executável é aberto com duplo clique (sem argumentos), a interface
gráfica inicia e o console do Windows é escondido para não incomodar.
"""

from __future__ import annotations

import sys

from pdf_dark.cli import main


def _hide_console_when_gui() -> None:
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    if len(sys.argv) > 1:
        return
    try:
        import ctypes

        handle = ctypes.windll.kernel32.GetConsoleWindow()
        if handle:
            ctypes.windll.user32.ShowWindow(handle, 0)
    except Exception:
        pass


if __name__ == "__main__":
    _hide_console_when_gui()
    raise SystemExit(main())
