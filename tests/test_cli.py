"""Testes da interface de linha de comando."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw

from pdf_dark.cli import build_parser, main


def make_pdf(path: Path, pages: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    size = (400, 600)
    images = []
    for _ in range(pages):
        image = Image.new("RGB", size, "white")
        ImageDraw.Draw(image).text((40, 40), "teste", fill="black")
        images.append(image)
    images[0].save(
        path, format="PDF", save_all=True, append_images=images[1:], resolution=72
    )
    return path


def test_color_and_image_flags() -> None:
    parser = build_parser()
    defaults = parser.parse_args(["a.pdf"])
    assert defaults.keep_color is False
    assert defaults.keep_images is True

    custom = parser.parse_args(["a.pdf", "--color", "--no-keep-images"])
    assert custom.keep_color is True
    assert custom.keep_images is False


def test_cli_converts_with_default_name(tmp_path: Path, capsys) -> None:
    source = make_pdf(tmp_path / "livro.pdf")
    assert main([str(source), "--dpi", "72"]) == 0
    target = tmp_path / "livro-dark.pdf"
    assert target.exists()
    assert "ok:" in capsys.readouterr().out


def test_cli_creates_output_directory(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "artigo.pdf")
    output = tmp_path / "saida"
    assert main([str(source), "-o", str(output) + os.sep]) == 0
    assert (output / "artigo-dark.pdf").exists()


def test_cli_skips_existing_without_overwrite(tmp_path: Path, capsys) -> None:
    source = make_pdf(tmp_path / "livro.pdf")
    target = tmp_path / "pronto.pdf"
    target.write_bytes(b"existente")
    assert main([str(source), "-o", str(target)]) == 1
    assert target.read_bytes() == b"existente"
    assert "já existe" in capsys.readouterr().err

    assert main([str(source), "-o", str(target), "--overwrite"]) == 0
    assert target.read_bytes().startswith(b"%PDF")


def test_cli_batch_requires_directory_output(tmp_path: Path, capsys) -> None:
    first = make_pdf(tmp_path / "a.pdf")
    second = make_pdf(tmp_path / "b.pdf")
    assert main([str(first), str(second), "-o", str(tmp_path / "unico.pdf")]) == 2
    assert "pasta" in capsys.readouterr().err


def test_cli_batch_converts_all(tmp_path: Path) -> None:
    first = make_pdf(tmp_path / "a.pdf")
    second = make_pdf(tmp_path / "b.pdf")
    output = tmp_path / "lote"
    assert main([str(first), str(second), "-o", str(output)]) == 0
    assert sorted(p.name for p in output.iterdir()) == ["a-dark.pdf", "b-dark.pdf"]


def test_cli_missing_input(tmp_path: Path, capsys) -> None:
    assert main([str(tmp_path / "nao-existe.pdf")]) == 2
    assert "não encontrado" in capsys.readouterr().err


def test_cli_expands_directories(tmp_path: Path) -> None:
    make_pdf(tmp_path / "entrada" / "x.pdf")
    assert main([str(tmp_path / "entrada"), "-o", str(tmp_path / "saida") + os.sep]) == 0
    assert (tmp_path / "saida" / "x-dark.pdf").exists()
