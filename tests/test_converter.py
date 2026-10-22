"""Testes do núcleo de conversão."""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium
import pytest
from PIL import Image, ImageDraw

from pdf_dark import ConversionError, Options, convert_pdf, default_output_path
from pdf_dark.theme import THEMES, apply_theme, get_theme


def make_pdf(path: Path, pages: int = 2, size: tuple[int, int] = (595, 842)) -> Path:
    images = []
    for index in range(pages):
        image = Image.new("RGB", size, "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 40, size[0] - 40, 120), fill="black")
        draw.rectangle((40, 200, size[0] - 40, 260), fill=(0, 80, 160))
        draw.text((60, 300), f"Pagina {index + 1}", fill="black")
        images.append(image)
    images[0].save(
        path,
        format="PDF",
        save_all=True,
        append_images=images[1:],
        resolution=72,
    )
    return path


def make_scanned_pdf(path: Path, size: tuple[int, int] = (595, 842)) -> Path:
    """PDF parecido com uma digitalização: uma imagem ocupando a página toda."""
    image = Image.new("RGB", size, (252, 252, 250))
    draw = ImageDraw.Draw(image)
    for row in range(12):
        y = 60 + row * 60
        draw.rectangle((50, y, size[0] - 50, y + 22), fill=(30, 30, 30))
    image.save(path, format="PDF", resolution=72)
    return path


def render_first_page(path: Path, dpi: int = 72) -> Image.Image:
    document = pdfium.PdfDocument(str(path))
    try:
        page = document[0]
        try:
            bitmap = page.render(scale=dpi / 72)
            try:
                return bitmap.to_pil().convert("RGB")
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        document.close()


def page_count(path: Path) -> int:
    document = pdfium.PdfDocument(str(path))
    try:
        return len(document)
    finally:
        document.close()


def mean_luminance(image: Image.Image) -> float:
    gray = image.convert("L")
    histogram = gray.histogram()
    total = sum(histogram)
    return sum(value * count for value, count in enumerate(histogram)) / total


# ---------------------------------------------------------------------- #
# Tema
# ---------------------------------------------------------------------- #
def test_apply_theme_inverts_light_and_dark() -> None:
    page = Image.new("RGB", (8, 8), "white")
    page.putpixel((0, 0), (0, 0, 0))
    themed = apply_theme(page, "dark").convert("RGB")
    assert themed.getpixel((4, 4))[0] < 40  # fundo branco virou escuro
    assert themed.getpixel((0, 0))[0] > 180  # texto preto virou claro


def test_apply_theme_amoled_uses_pure_black() -> None:
    themed = apply_theme(Image.new("RGB", (4, 4), "white"), "amoled").convert("RGB")
    assert themed.getpixel((1, 1)) == (0, 0, 0)


def test_sepia_keeps_tint() -> None:
    themed = apply_theme(Image.new("RGB", (4, 4), "white"), "sepia").convert("RGB")
    red, green, blue = themed.getpixel((1, 1))
    assert red > green > blue


def test_unknown_theme_raises() -> None:
    with pytest.raises(ValueError):
        get_theme("inexistente")


def test_keep_color_returns_rgb() -> None:
    page = Image.new("RGB", (8, 8), (0, 120, 255))
    themed = apply_theme(page, "dark", keep_color=True)
    assert themed.mode == "RGB"


def test_contrast_applies_in_color_mode() -> None:
    page = Image.linear_gradient("L").convert("RGB")
    base = apply_theme(page, "dark", keep_color=True).tobytes()
    boosted = apply_theme(page, "dark", keep_color=True, contrast=2.0).tobytes()
    assert base != boosted


# ---------------------------------------------------------------------- #
# Conversão
# ---------------------------------------------------------------------- #
def test_convert_pdf_generates_dark_file(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "livro.pdf", pages=3)
    target = convert_pdf(source, options=Options(dpi=100))
    assert target == tmp_path / "livro-dark.pdf"
    assert target.stat().st_size > 0
    assert page_count(target) == 3

    rendered = render_first_page(target)
    assert rendered.size == render_first_page(source).size
    assert mean_luminance(rendered) < 120
    histogram = rendered.convert("L").histogram()
    assert any(count for value, count in enumerate(histogram) if value > 180)


def test_progress_callback_reports_every_page(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "progresso.pdf", pages=3)
    seen: list[tuple[int, int]] = []
    convert_pdf(source, options=Options(dpi=72), progress=lambda a, b: seen.append((a, b)))
    assert seen == [(1, 3), (2, 3), (3, 3)]


def test_grayscale_option_produces_smaller_file(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "cores.pdf", pages=1)
    colored = convert_pdf(
        source, tmp_path / "cor.pdf", Options(dpi=100, keep_color=True)
    )
    gray = convert_pdf(
        source, tmp_path / "cinza.pdf", Options(dpi=100, keep_color=False)
    )
    assert gray.stat().st_size < colored.stat().st_size


def test_scanned_page_is_also_darkened(tmp_path: Path) -> None:
    source = make_scanned_pdf(tmp_path / "scan.pdf")
    target = convert_pdf(source, options=Options(dpi=100))
    assert mean_luminance(render_first_page(target)) < 120


def test_pages_with_different_sizes_are_preserved(tmp_path: Path) -> None:
    small = Image.new("RGB", (400, 400), "white")
    large = Image.new("RGB", (900, 600), "white")
    source = tmp_path / "misto.pdf"
    small.save(source, format="PDF", save_all=True, append_images=[large], resolution=72)

    target = convert_pdf(source, options=Options(dpi=72))
    document = pdfium.PdfDocument(str(target))
    try:
        sizes = [document[i].get_size() for i in range(len(document))]
    finally:
        document.close()
    assert sizes[0][0] == pytest.approx(400, abs=1)
    assert sizes[1][1] == pytest.approx(600, abs=1)


def test_default_output_path() -> None:
    assert default_output_path("artigos/meu texto.pdf") == Path("artigos/meu texto-dark.pdf")


def test_missing_file_raises() -> None:
    with pytest.raises(ConversionError):
        convert_pdf("nao-existe.pdf")


def test_output_cannot_overwrite_input(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "mesmo.pdf", pages=1)
    with pytest.raises(ConversionError):
        convert_pdf(source, source)


def test_invalid_pdf_raises(tmp_path: Path) -> None:
    broken = tmp_path / "quebrado.pdf"
    broken.write_bytes(b"isto nao e um pdf")
    with pytest.raises(ConversionError):
        convert_pdf(broken)


def test_options_keep_color_default() -> None:
    assert Options().keep_color is False
    assert set(THEMES) >= {"dark", "amoled", "sepia"}
