"""Conversão de PDF: rasteriza cada página, aplica o tema e grava o resultado."""

from __future__ import annotations

import io
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

from .pdfwriter import PdfWriter
from .theme import DEFAULT_THEME, apply_theme, get_theme

ProgressCallback = Callable[[int, int], None]

MIN_DPI = 72
MAX_DPI = 600
MIN_QUALITY = 40
MAX_QUALITY = 100


class ConversionError(Exception):
    """Erro amigável exibido ao usuário (arquivo inválido, protegido, etc.)."""


@dataclass
class Options:
    """Ajustes da conversão."""

    dpi: int = 150
    quality: int = 85
    theme: str = DEFAULT_THEME
    contrast: float = 1.0
    keep_images: bool = True
    keep_color: bool = False
    password: str | None = None


def default_output_path(source: str | Path) -> Path:
    """``livro.pdf`` -> ``livro-dark.pdf`` (na mesma pasta)."""
    source = Path(source)
    return source.with_name(f"{source.stem}-dark.pdf")


def convert_pdf(
    source: str | Path,
    destination: str | Path | None = None,
    options: Options | None = None,
    progress: ProgressCallback | None = None,
) -> Path:
    """Converte ``source`` para modo escuro e devolve o caminho gerado.

    A gravação é atômica: o arquivo final só aparece quando a conversão
    termina com sucesso.
    """
    opts = options or Options()
    get_theme(opts.theme)  # valida o nome do tema antes de abrir o PDF

    dpi = _clamp(int(opts.dpi), MIN_DPI, MAX_DPI)
    quality = _clamp(int(opts.quality), MIN_QUALITY, MAX_QUALITY)
    if opts.contrast <= 0:
        raise ConversionError("o contraste precisa ser maior que zero")

    source_path = Path(source)
    if not source_path.is_file():
        raise ConversionError(f"arquivo não encontrado: {source_path}")

    target = Path(destination) if destination else default_output_path(source_path)
    if source_path.resolve() == target.resolve():
        raise ConversionError("a saída não pode sobrescrever o arquivo de entrada")
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)

    temporary = target.with_name(target.name + ".part")
    try:
        document = pdfium.PdfDocument(str(source_path), password=opts.password or None)
    except Exception as exc:  # pypdfium2 não expõe uma exceção única e estável
        raise ConversionError(
            f"não foi possível abrir {source_path.name}: {_describe(exc)}"
        ) from exc

    try:
        total = len(document)
        if total == 0:
            raise ConversionError(f"{source_path.name} não possui páginas")

        scale = dpi / 72
        with open(temporary, "wb") as handle:
            writer = PdfWriter(handle)
            for index in range(total):
                page = document[index]
                try:
                    image = _render_page(page, scale, opts)
                    width_pt, height_pt = page.get_size()
                    jpeg = _encode_page(image, quality)
                    writer.add_page(
                        jpeg,
                        image.width,
                        image.height,
                        width_pt,
                        height_pt,
                        grayscale=image.mode == "L",
                    )
                finally:
                    page.close()
                if progress is not None:
                    progress(index + 1, total)
            writer.close()
        os.replace(temporary, target)
    except ConversionError:
        _discard(temporary)
        raise
    except Exception as exc:
        _discard(temporary)
        raise ConversionError(
            f"falha ao converter {source_path.name}: {_describe(exc)}"
        ) from exc
    finally:
        document.close()

    return target


# ---------------------------------------------------------------------- #
# Renderização
# ---------------------------------------------------------------------- #
def _render_page(
    page: pdfium.PdfPage,
    scale: float,
    opts: Options,
) -> Image.Image:
    """Rasteriza a página e aplica o tema, preservando fotos coloridas."""
    boxes = _image_boxes(page, scale) if opts.keep_images else []
    bitmap = page.render(scale=scale)
    try:
        original = bitmap.to_pil().convert("RGB")
    finally:
        bitmap.close()

    themed = apply_theme(
        original,
        opts.theme,
        contrast=opts.contrast,
        keep_color=opts.keep_color,
        force_rgb=bool(boxes),
    )
    if boxes:
        _paste_original_images(original, themed, boxes)
    return themed


def _paste_original_images(
    original: Image.Image,
    themed: Image.Image,
    boxes: list[tuple[int, int, int, int]],
) -> None:
    """Recorta as imagens (fotos, gráficos) do PDF original por cima do tema.

    Sem isso, fotos ficariam com as cores invertidas (aspecto de negativo).
    """
    for box in boxes:
        clamped = _clamp_box(box, themed.size)
        if clamped is None:
            continue
        themed.paste(original.crop(clamped), clamped[:2])


def _image_boxes(
    page: pdfium.PdfPage, scale: float
) -> list[tuple[int, int, int, int]]:
    """Posições (em pixels) das imagens da página, já com a rotação aplicada."""
    try:
        objects = list(page.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE]))
    except Exception:
        return []
    if not objects:
        return []

    width_pt, height_pt = page.get_size()
    rotation = page.get_rotation() % 360
    swapped = rotation in (90, 270)
    # get_size() já considera a rotação; get_bounds() usa a página sem rotação.
    base_width = height_pt if swapped else width_pt
    base_height = width_pt if swapped else height_pt

    boxes: list[tuple[int, int, int, int]] = []
    for obj in objects:
        try:
            left, bottom, right, top = obj.get_bounds()
        except Exception:
            continue
        finally:
            obj.close()

        corners = [
            _to_display(left, bottom, rotation, base_width, base_height),
            _to_display(left, top, rotation, base_width, base_height),
            _to_display(right, bottom, rotation, base_width, base_height),
            _to_display(right, top, rotation, base_width, base_height),
        ]
        xs = [point[0] for point in corners]
        ys = [point[1] for point in corners]
        box = (
            max(0, round(min(xs) * scale)),
            max(0, round(min(ys) * scale)),
            round(max(xs) * scale),
            round(max(ys) * scale),
        )
        if box[2] - box[0] >= 2 and box[3] - box[1] >= 2:
            boxes.append(box)

    # Páginas digitalizadas costumam ser uma única imagem cobrindo tudo.
    # Nesse caso preservar a "foto" desfaria o modo escuro, então ignoramos.
    page_area = (width_pt * scale) * (height_pt * scale)
    covered = sum((b[2] - b[0]) * (b[3] - b[1]) for b in boxes)
    if page_area > 0 and covered / page_area > 0.85:
        return []
    return boxes


def _to_display(
    x: float, y: float, rotation: int, width_pt: float, height_pt: float
) -> tuple[float, float]:
    """Converte coordenadas do PDF (origem embaixo) para pixels (origem no topo)."""
    if rotation == 90:
        return y, x
    if rotation == 180:
        return width_pt - x, height_pt - y
    if rotation == 270:
        return height_pt - y, width_pt - x
    return x, height_pt - y


def _clamp_box(
    box: tuple[int, int, int, int], size: tuple[int, int]
) -> tuple[int, int, int, int] | None:
    left = max(0, box[0])
    top = max(0, box[1])
    right = min(size[0], box[2])
    bottom = min(size[1], box[3])
    if right - left < 2 or bottom - top < 2:
        return None
    return left, top, right, bottom


# ---------------------------------------------------------------------- #
# Utilidades
# ---------------------------------------------------------------------- #
def _encode_page(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=True,
        subsampling=0,
    )
    return buffer.getvalue()


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _discard(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _describe(exc: BaseException) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__
