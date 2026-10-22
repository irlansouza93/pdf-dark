"""Componentes visuais minimalistas para a interface escura em Tkinter."""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable, Sequence

# ---------------------------------------------------------------------- #
# Paleta
# ---------------------------------------------------------------------- #
BG = "#0a0b0f"
SURFACE = "#14161c"
SURFACE_ALT = "#1d2028"
SURFACE_HOVER = "#232733"
BORDER = "#252a36"
TEXT = "#e7e9f0"
SOFT = "#c3c8d4"
MUTED = "#8b91a3"
DISABLED = "#5a6070"
ACCENT = "#7aa2f7"
ACCENT_HOVER = "#9cb9ff"
ACCENT_DIM = "#1b2740"
READER_BG = "#07080b"
PAGE = "#121419"
DANGER = "#f7768e"

_FONT_CACHE: dict[tuple[int, str], tkfont.Font] = {}
_FAMILY: str | None = None


def family() -> str:
    """Família de fonte do sistema, escolhida uma única vez."""
    global _FAMILY
    if _FAMILY is None:
        try:
            _FAMILY = tkfont.nametofont("TkDefaultFont").actual("family")
        except tk.TclError:  # pragma: no cover - ambiente sem Tk inicializado
            _FAMILY = "TkDefaultFont"
    return _FAMILY


def ui_font(size: int = 10, weight: str = "normal") -> tkfont.Font:
    key = (size, weight)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = tkfont.Font(family=family(), size=size, weight=weight)
    return _FONT_CACHE[key]


def mix(first: str, second: str, ratio: float) -> str:
    """Mistura duas cores hexadecimais (0.0 = primeira, 1.0 = segunda)."""
    a = tuple(int(first[index : index + 2], 16) for index in (1, 3, 5))
    b = tuple(int(second[index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(round(x + (y - x) * ratio) for x, y in zip(a, b))
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    **kwargs: object,
) -> int:
    """Desenha um retângulo de cantos arredondados (polígono suavizado)."""
    radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


# ---------------------------------------------------------------------- #
# Botão plano (texto)
# ---------------------------------------------------------------------- #
class FlatButton(tk.Label):
    """Rótulo clicável com estados de hover e ativo, sem bordas nativas."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None] | None = None,
        *,
        bg: str = BG,
        active: bool = False,
        padx: int = 10,
        pady: int = 6,
        size: int = 10,
        weight: str = "normal",
        fg: str | None = None,
    ) -> None:
        self._base_bg = bg
        self._command = command
        self._active = active
        self._hover = False
        self._enabled = True
        self._custom_fg = fg
        super().__init__(
            master,
            text=text,
            bg=bg,
            fg=fg or MUTED,
            font=ui_font(size, weight),
            padx=padx,
            pady=pady,
            bd=0,
            cursor="hand2",
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._refresh()

    # -- API ----------------------------------------------------------- #
    def set_active(self, active: bool) -> None:
        self._active = active
        self._refresh()

    def set_text(self, text: str) -> None:
        self.configure(text=text)

    def set_command(self, command: Callable[[], None]) -> None:
        self._command = command

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._refresh()

    # -- Estados ------------------------------------------------------- #
    def _refresh(self) -> None:
        if not self._enabled:
            background, foreground = self._base_bg, DISABLED
        elif self._active:
            background, foreground = ACCENT_DIM, ACCENT
        elif self._hover:
            background, foreground = SURFACE_HOVER, TEXT
        else:
            background = self._base_bg
            foreground = self._custom_fg or SOFT
        self.configure(bg=background, fg=foreground)

    def _on_enter(self, _event: tk.Event) -> None:
        self._hover = True
        self._refresh()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hover = False
        self._refresh()

    def _on_press(self, _event: tk.Event) -> None:
        if self._enabled:
            self.configure(bg=mix(self._base_bg, ACCENT, 0.18))

    def _on_release(self, event: tk.Event) -> None:
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self._refresh()
        if self._enabled and inside and self._command is not None:
            self._command()


# ---------------------------------------------------------------------- #
# Botão principal (preenchido, cantos arredondados)
# ---------------------------------------------------------------------- #
class PrimaryButton(tk.Canvas):
    """Botão de destaque desenhado em Canvas, com cantos arredondados."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        bg: str = BG,
        fill: str = ACCENT,
        fg: str = BG,
        width: int = 200,
        height: int = 42,
        radius: int = 12,
        size: int = 11,
        weight: str = "bold",
    ) -> None:
        super().__init__(
            master, width=width, height=height, bg=bg, highlightthickness=0, bd=0,
            cursor="hand2",
        )
        self._command = command
        self._fill = fill
        self._fg = fg
        self._radius = radius
        self._size = size
        self._weight = weight
        self._hover = False
        self._enabled = True
        self._text = text
        self._width = width
        self._height = height
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", lambda _e: self._draw(pressed=True))
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def _set_hover(self, hover: bool) -> None:
        self._hover = hover
        self._draw()

    def _on_release(self, event: tk.Event) -> None:
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self._draw()
        if self._enabled and inside:
            self._command()

    def _draw(self, pressed: bool = False) -> None:
        self.delete("all")
        width = max(self.winfo_width(), self._width)
        height = max(self.winfo_height(), self._height)
        if not self._enabled:
            fill, fg = SURFACE_ALT, DISABLED
        elif pressed:
            fill, fg = mix(self._fill, "#000000", 0.15), self._fg
        elif self._hover:
            fill, fg = mix(self._fill, "#ffffff", 0.15), self._fg
        else:
            fill, fg = self._fill, self._fg
        rounded_rect(self, 1, 1, width - 1, height - 1, self._radius, fill=fill, outline="")
        self.create_text(
            width / 2, height / 2, text=self._text, fill=fg,
            font=ui_font(self._size, self._weight),
        )


# ---------------------------------------------------------------------- #
# Grupo de chips (seleção única)
# ---------------------------------------------------------------------- #
class ChipGroup(tk.Frame):
    """Conjunto de botões em que apenas um fica ativo."""

    def __init__(
        self,
        master: tk.Misc,
        options: Sequence[tuple[object, str]],
        value: object,
        *,
        bg: str = SURFACE,
        command: Callable[[object], None] | None = None,
        size: int = 9,
    ) -> None:
        super().__init__(master, bg=bg)
        self._command = command
        self._buttons: dict[object, FlatButton] = {}
        self._value = value
        for key, label in options:
            button = FlatButton(
                self, label, bg=bg, padx=11, pady=5, size=size,
                command=lambda k=key: self.select(k),
            )
            button.pack(side="left", padx=(0, 6))
            self._buttons[key] = button
        self._paint()

    def select(self, value: object, *, notify: bool = True) -> None:
        self._value = value
        self._paint()
        if notify and self._command is not None:
            self._command(value)

    def get(self) -> object:
        return self._value

    def _paint(self) -> None:
        for key, button in self._buttons.items():
            button.set_active(key == self._value)


# ---------------------------------------------------------------------- #
# Contêiner arredondado (barra flutuante)
# ---------------------------------------------------------------------- #
class Pill(tk.Canvas):
    """Cartão de cantos arredondados usado na barra flutuante do modo imersivo."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        bg: str = READER_BG,
        fill: str = SURFACE,
        radius: int = 16,
        padx: int = 10,
        pady: int = 6,
        outline: str = BORDER,
    ) -> None:
        super().__init__(master, bg=bg, highlightthickness=0, bd=0)
        self._radius = radius
        self._padx = padx
        self._pady = pady
        self._fill = fill
        self._outline = outline
        self.inner = tk.Frame(self, bg=fill)
        self._window = self.create_window(padx, pady, window=self.inner, anchor="nw")

    def fit(self) -> None:
        """Ajusta o tamanho do cartão ao conteúdo já posicionado em ``inner``."""
        self.update_idletasks()
        width = self.inner.winfo_reqwidth() + self._padx * 2
        height = self.inner.winfo_reqheight() + self._pady * 2
        self.configure(width=width, height=height)
        self.delete("shape")
        rounded_rect(
            self, 0.5, 0.5, width - 0.5, height - 0.5, self._radius,
            fill=self._fill, outline=self._outline, width=1,
        )
        self.tag_lower("shape")
        self.itemconfigure(self._window, width=self.inner.winfo_reqwidth())


# ---------------------------------------------------------------------- #
# Barra de título escura no Windows
# ---------------------------------------------------------------------- #
def apply_dark_titlebar(window: tk.Misc) -> None:
    """Pede ao Windows que pinte a barra de título nativa em tom escuro."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            return
        enabled = ctypes.c_int(1)
        for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (Win11/Win10)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)
            ) == 0:
                break
        caption = ctypes.c_int(0x000F0B0A)  # COLORREF de BG (#0a0b0f)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption)
        )
        text = ctypes.c_int(0x00F0E9E7)  # COLORREF de TEXT (#e7e9f0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 36, ctypes.byref(text), ctypes.sizeof(text)
        )
    except Exception:
        pass


def set_app_icon(window: tk.Misc) -> None:
    """Aplica o ícone do pacote na janela (ignora falhas)."""
    try:
        from importlib.resources import files

        icon = files("pdf_dark").joinpath("assets/icon.png")
        with icon.open("rb") as handle:
            image = tk.PhotoImage(data=handle.read())
        window.iconphoto(True, image)  # type: ignore[attr-defined]
        window._icon_image = image  # type: ignore[attr-defined]
    except Exception:
        pass


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
