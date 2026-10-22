"""pdf-dark: leitura confortável de PDFs em modo escuro."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .converter import ConversionError, Options, convert_pdf, default_output_path
from .theme import DEFAULT_THEME, THEMES, Theme

try:  # pragma: no cover - depende do pacote estar instalado
    __version__ = version("pdf-dark")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    "ConversionError",
    "DEFAULT_THEME",
    "Options",
    "THEMES",
    "Theme",
    "convert_pdf",
    "default_output_path",
    "__version__",
]
