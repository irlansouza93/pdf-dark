"""Gera o ícone do aplicativo (PNG para a janela e ICO para o executável).

Uso: uv run python scripts/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "src" / "pdf_dark" / "assets"

BACKGROUND = (17, 24, 39)
PAGE = (238, 241, 245)
INK = (100, 116, 139)
ACCENT = (250, 191, 36)

SIZE = 1024


def draw_icon(size: int = SIZE) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    s = size

    draw.rounded_rectangle(
        (0, 0, s, s), radius=int(s * 0.22), fill=BACKGROUND + (255,)
    )

    # Folha de papel
    left, top, right, bottom = int(s * 0.20), int(s * 0.15), int(s * 0.68), int(s * 0.84)
    draw.rounded_rectangle(
        (left, top, right, bottom), radius=int(s * 0.045), fill=PAGE + (255,)
    )
    # Cantinho dobrado
    fold = int(s * 0.15)
    draw.polygon(
        [(right - fold, top), (right, top + fold), (right - fold, top + fold)],
        fill=INK + (255,),
    )
    # Linhas de texto
    line_left = left + int(s * 0.06)
    line_right = right - int(s * 0.06)
    for index in range(4):
        y = top + int(s * 0.28) + index * int(s * 0.11)
        width = line_right - (int(s * 0.12) if index == 3 else 0)
        draw.rounded_rectangle(
            (line_left, y, width, y + int(s * 0.035)),
            radius=int(s * 0.018),
            fill=INK + (255,),
        )

    # Lua crescente (modo escuro)
    cx, cy, radius = int(s * 0.735), int(s * 0.70), int(s * 0.165)
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius), fill=ACCENT + (255,)
    )
    offset = int(s * 0.055)
    draw.ellipse(
        (
            cx - radius + offset,
            cy - radius - offset,
            cx + radius + offset,
            cy + radius - offset,
        ),
        fill=BACKGROUND + (255,),
    )
    return image


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    master = draw_icon()
    master.resize((256, 256), Image.LANCZOS).save(ASSETS / "icon.png")
    master.save(
        ASSETS / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"ícones gravados em {ASSETS}")


if __name__ == "__main__":
    main()
