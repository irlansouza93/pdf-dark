"""Interface de linha de comando."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from .converter import (
    MAX_DPI,
    MAX_QUALITY,
    MIN_DPI,
    MIN_QUALITY,
    ConversionError,
    Options,
    convert_pdf,
    default_output_path,
)
from .theme import DEFAULT_THEME, THEMES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-dark",
        description=(
            "Converte PDFs de fundo branco para um modo escuro, mais confortável "
            "para leituras longas."
        ),
        epilog=(
            "Exemplos:\n"
            "  pdf-dark livro.pdf\n"
            "  pdf-dark livro.pdf -o livro-escuro.pdf --dpi 200\n"
            "  pdf-dark artigos/ -o saida/ --theme sepia\n"
            "  pdf-dark            # abre a interface gráfica\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        metavar="PDF",
        help="arquivos ou pastas com PDFs para converter",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="CAMINHO",
        help=(
            "arquivo de saída (um PDF) ou pasta de saída (vários PDFs). "
            "Padrão: <nome>-dark.pdf ao lado do original"
        ),
    )
    parser.add_argument(
        "-t",
        "--theme",
        choices=list(THEMES),
        default=DEFAULT_THEME,
        help=f"tema de cores (padrão: {DEFAULT_THEME})",
    )
    parser.add_argument(
        "-d",
        "--dpi",
        type=int,
        default=150,
        metavar="N",
        help=f"resolução da página, de {MIN_DPI} a {MAX_DPI} (padrão: 150)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=85,
        metavar="N",
        help=f"qualidade JPEG, de {MIN_QUALITY} a {MAX_QUALITY} (padrão: 85)",
    )
    parser.add_argument(
        "-c",
        "--contrast",
        type=float,
        default=1.0,
        metavar="F",
        help="realce do contraste do texto, ex.: 1.2 (padrão: 1.0)",
    )
    parser.add_argument(
        "--color",
        dest="keep_color",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "mantém o matiz de códigos, gráficos e links; sem esta opção o "
            "resultado fica em tons de cinza (padrão: desligado)"
        ),
    )
    parser.add_argument(
        "--keep-images",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "preserva fotos e ilustrações nas cores originais; use "
            "--no-keep-images para escurecê-las também (padrão: ligado)"
        ),
    )
    parser.add_argument(
        "--password",
        metavar="SENHA",
        help="senha do PDF, quando protegido",
    )
    parser.add_argument(
        "-f",
        "--overwrite",
        action="store_true",
        help="sobrescreve o arquivo de saída se ele já existir",
    )
    parser.add_argument(
        "--open",
        dest="open_result",
        action="store_true",
        help="abre o PDF gerado ao terminar",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="abre a interface gráfica",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"pdf-dark {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.gui or not args.inputs:
        from .gui import main as gui_main

        gui_main()
        return 0

    try:
        files = _expand_inputs(args.inputs)
    except ConversionError as exc:
        _error(str(exc))
        return 2
    if not files:
        _error("nenhum arquivo PDF encontrado nos caminhos informados")
        return 2

    output = args.output
    if len(files) > 1 and output and Path(output).suffix.lower() == ".pdf":
        _error("com vários PDFs, use -o apontando para uma pasta")
        return 2

    options = Options(
        dpi=args.dpi,
        quality=args.quality,
        theme=args.theme,
        contrast=args.contrast,
        keep_images=args.keep_images,
        keep_color=args.keep_color,
        password=args.password,
    )

    generated: list[Path] = []
    failed = 0
    interactive = sys.stdout.isatty()

    for position, source in enumerate(files, start=1):
        target = _resolve_target(source, output, multiple=len(files) > 1)
        if not args.overwrite and target.exists():
            _warn(f"{target.name} já existe, pulando (use -f para sobrescrever)")
            failed += 1
            continue
        if len(files) > 1:
            print(f"[{position}/{len(files)}] {source.name}")

        last_update = 0.0

        def progress(done: int, total: int, *, _name: str = source.name) -> None:
            nonlocal last_update
            if not interactive:
                return
            now = time.monotonic()
            if done < total and now - last_update < 0.1:
                return
            last_update = now
            percent = int(done * 100 / total)
            print(f"\r  {_name}: {percent:3d}% ({done}/{total} páginas)", end="", flush=True)
            if done == total:
                print()

        started = time.perf_counter()
        try:
            result = convert_pdf(source, target, options, progress=progress)
        except ConversionError as exc:
            if interactive:
                print()
            _error(str(exc))
            failed += 1
            continue
        elapsed = time.perf_counter() - started
        generated.append(result)
        print(f"  ok: {_display_path(result)} ({_human_size(result.stat().st_size)}, {elapsed:.1f}s)")

    if args.open_result and generated:
        _open_path(generated[0])

    if len(files) > 1:
        print(f"\n{len(generated)} PDF(s) convertido(s), {failed} com problema.")
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------- #
# Utilidades
# ---------------------------------------------------------------------- #
def _expand_inputs(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_dir():
            found = sorted(
                item for item in path.iterdir() if item.suffix.lower() == ".pdf"
            )
            files.extend(found)
        elif path.is_file():
            files.append(path)
        else:
            raise ConversionError(f"caminho não encontrado: {raw}")
    return files


def _resolve_target(source: Path, output: str | None, *, multiple: bool) -> Path:
    if not output:
        return default_output_path(source)
    out = Path(output).expanduser()
    looks_like_folder = multiple or out.is_dir() or output.endswith(("/", "\\"))
    if looks_like_folder:
        return out / default_output_path(source).name
    if out.suffix.lower() != ".pdf":
        out = out.with_suffix(".pdf")
    return out


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"  # pragma: no cover


def _error(message: str) -> None:
    print(f"erro: {message}", file=sys.stderr)


def _warn(message: str) -> None:
    print(f"aviso: {message}", file=sys.stderr)


def _open_path(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
