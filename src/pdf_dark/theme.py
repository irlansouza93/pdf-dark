"""Temas de cor e transformação das páginas renderizadas.

A ideia central: o PDF é rasterizado e cada página é tratada como uma
"tinta" (ink). O papel branco vira o fundo escuro do tema e o texto preto
vira a cor de frente clara, preservando o contraste e o antisserrilhado
das letras.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageEnhance, ImageOps

RGB = tuple[int, int, int]


def _luma(color: RGB) -> float:
    """Luminância perceptual (ITU-R BT.601)."""
    red, green, blue = color
    return 0.299 * red + 0.587 * green + 0.114 * blue


def _spread(color: RGB) -> int:
    return max(color) - min(color)


@dataclass(frozen=True)
class Theme:
    """Um par de cores (fundo do papel / cor da tinta) usado na conversão."""

    key: str
    label: str
    background: RGB
    foreground: RGB

    @property
    def neutral(self) -> bool:
        """True quando o tema não tem matiz (permite salvar em tons de cinza)."""
        return _spread(self.background) <= 6 and _spread(self.foreground) <= 6


THEMES: dict[str, Theme] = {
    "dark": Theme(
        key="dark",
        label="Escuro (cinza)",
        background=(24, 24, 24),
        foreground=(228, 228, 228),
    ),
    "amoled": Theme(
        key="amoled",
        label="Preto puro (OLED)",
        background=(0, 0, 0),
        foreground=(235, 235, 235),
    ),
    "sepia": Theme(
        key="sepia",
        label="Sépia (papel envelhecido)",
        background=(30, 26, 20),
        foreground=(226, 212, 186),
    ),
}

DEFAULT_THEME = "dark"


def get_theme(name: str) -> Theme:
    """Devolve o tema pelo nome, aceitando maiúsculas/minúsculas."""
    try:
        return THEMES[name.strip().lower()]
    except KeyError:
        valid = ", ".join(THEMES)
        raise ValueError(f"tema desconhecido: {name!r} (opções: {valid})") from None


def theme_choices() -> list[tuple[str, str]]:
    """Lista ``(chave, rótulo)`` para menus e comboboxes."""
    return [(theme.key, theme.label) for theme in THEMES.values()]


def _ink(image: Image.Image, contrast: float) -> Image.Image:
    """Converte a página em um mapa de tinta: papel branco = 0, texto preto = 255."""
    ink = ImageOps.invert(image.convert("L"))
    if contrast != 1.0:
        ink = ImageEnhance.Contrast(ink).enhance(contrast)
    return ink


def _ink_ramp(theme: Theme) -> list[int]:
    """Tabela que leva a tinta (0..255) para a luminância final do tema."""
    background = _luma(theme.background)
    foreground = _luma(theme.foreground)
    return [round(background + (foreground - background) * (i / 255)) for i in range(256)]


def _chroma_ramp(saturation: float) -> list[int]:
    """Tabela que aproxima (ou afasta) as componentes de cor do cinza neutro."""
    return [max(0, min(255, round(128 + (i - 128) * saturation))) for i in range(256)]


def apply_theme(
    image: Image.Image,
    theme: str | Theme = DEFAULT_THEME,
    *,
    contrast: float = 1.0,
    keep_color: bool = False,
    saturation: float = 0.8,
    force_rgb: bool = False,
) -> Image.Image:
    """Aplica o tema escuro em uma página já rasterizada.

    Args:
        image: página renderizada (qualquer modo do Pillow).
        theme: chave do tema ou objeto :class:`Theme`.
        contrast: fator de contraste aplicado sobre a tinta (1.0 = original).
        keep_color: preserva o matiz de gráficos e links invertendo a
            luminosidade no espaço de cor Lab.
        saturation: quanto do matiz original manter quando ``keep_color``.
        force_rgb: devolve sempre RGB (necessário quando imagens coloridas
            serão coladas sobre o resultado).
    """
    active = get_theme(theme) if isinstance(theme, str) else theme
    if contrast <= 0:
        raise ValueError("contraste deve ser maior que zero")

    ramp = _ink_ramp(active)

    if keep_color:
        lab = image.convert("LAB")
        lightness, a_channel, b_channel = lab.split()
        if contrast != 1.0:
            lightness = ImageEnhance.Contrast(lightness).enhance(contrast)
        light_ramp = [ramp[255 - value] for value in range(256)]
        chroma = _chroma_ramp(saturation)
        lab = Image.merge(
            "LAB",
            (
                lightness.point(light_ramp),
                a_channel.point(chroma),
                b_channel.point(chroma),
            ),
        )
        return lab.convert("RGB")

    ink = _ink(image, contrast)
    colored = ImageOps.colorize(ink, black=active.background, white=active.foreground)
    if force_rgb or not active.neutral:
        return colored
    return colored.convert("L")
