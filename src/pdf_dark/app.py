"""Aplicativo PDF Dark: leitura com canvas próprio e conversão integrada."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, ttk

from . import __version__
from .converter import ConversionError, Options, convert_pdf, default_output_path
from .theme import DEFAULT_THEME, THEMES
from .viewer import PdfViewer
from .widgets import (
    ACCENT,
    BG,
    BORDER,
    DANGER,
    MUTED,
    READER_BG,
    SOFT,
    SURFACE,
    SURFACE_ALT,
    TEXT,
    ChipGroup,
    FlatButton,
    Pill,
    PrimaryButton,
    apply_dark_titlebar,
    rounded_rect,
    set_app_icon,
    truncate,
    ui_font,
)

SHEET_WIDTH = 348
THEME_SHORT = {"dark": "Cinza", "amoled": "Preto", "sepia": "Sépia"}


# ---------------------------------------------------------------------- #
# Início (nenhum documento aberto)
# ---------------------------------------------------------------------- #
class StartScreen(tk.Frame):
    """Tela inicial minimalista, exibida enquanto nenhum PDF está aberto."""

    def __init__(self, master: tk.Misc, on_open: Callable[[], None]) -> None:
        super().__init__(master, bg=READER_BG)
        wrap = tk.Frame(self, bg=READER_BG)
        wrap.place(relx=0.5, rely=0.47, anchor="center")

        art = tk.Canvas(
            wrap, width=250, height=150, bg=READER_BG, highlightthickness=0, bd=0
        )
        art.pack(pady=(0, 26))
        self._draw_pages(art)

        title = tk.Frame(wrap, bg=READER_BG)
        title.pack()
        tk.Label(
            title, text="PDF ", bg=READER_BG, fg=TEXT, font=ui_font(26, "bold")
        ).pack(side="left")
        tk.Label(
            title, text="Dark", bg=READER_BG, fg=ACCENT, font=ui_font(26, "bold")
        ).pack(side="left")

        tk.Label(
            wrap,
            text="Leia com conforto. Alterne entre claro e escuro quando quiser.",
            bg=READER_BG,
            fg=MUTED,
            font=ui_font(10),
        ).pack(pady=(6, 24))

        PrimaryButton(
            wrap,
            "Abrir um PDF",
            on_open,
            bg=READER_BG,
            width=214,
            height=46,
            radius=14,
            size=11,
        ).pack()

        tk.Label(
            wrap,
            text="Ctrl+O  abrir      D  tema      F10  ocultar barra      F11  tela cheia",
            bg=READER_BG,
            fg="#5c6274",
            font=ui_font(9),
        ).pack(pady=(22, 0))

    @staticmethod
    def _draw_pages(canvas: tk.Canvas) -> None:
        """Ilustração: uma página clara ao lado de sua versão escura."""
        rounded_rect(canvas, 34, 8, 146, 134, 9, fill="#e9ecf3", outline="")
        for line in range(5):
            canvas.create_line(
                52, 32 + line * 17, 128, 32 + line * 17, fill="#bcc3d2", width=3
            )
        rounded_rect(canvas, 112, 20, 224, 146, 9, fill="#101218", outline=ACCENT, width=1)
        for line in range(5):
            canvas.create_line(
                130, 44 + line * 17, 206, 44 + line * 17, fill="#3b4254", width=3
            )


# ---------------------------------------------------------------------- #
# Painel de conversão
# ---------------------------------------------------------------------- #
class ConvertSheet(tk.Frame):
    """Painel lateral com os ajustes de exportação do PDF escuro."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_close: Callable[[], None],
        on_appearance: Callable[[str, bool, bool], None],
        on_notify: Callable[..., None],
    ) -> None:
        super().__init__(master, bg=SURFACE)
        self._on_close = on_close
        self._on_appearance = on_appearance
        self._notify = on_notify
        self._source: Path | None = None
        self._result: Path | None = None
        self._busy = False
        self._queue: queue.Queue = queue.Queue()
        self._keep_images = True
        self._keep_color = False
        self._build()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        pad = 22

        header = tk.Frame(self, bg=SURFACE)
        header.pack(fill="x", padx=pad, pady=(20, 2))
        tk.Label(
            header, text="Converter", bg=SURFACE, fg=TEXT, font=ui_font(14, "bold")
        ).pack(side="left")
        FlatButton(header, "✕", self._on_close, bg=SURFACE, padx=8).pack(side="right")

        self.hint = tk.Label(
            self,
            text="Exporte uma cópia com o tema escuro aplicado.",
            bg=SURFACE,
            fg=MUTED,
            font=ui_font(9),
            justify="left",
            wraplength=300,
        )
        self.hint.pack(fill="x", padx=pad, pady=(0, 16))

        self._caption("Tema")
        self.theme = ChipGroup(
            self,
            [(key, THEME_SHORT.get(key, key)) for key in THEMES],
            DEFAULT_THEME,
            bg=SURFACE,
            command=lambda _value: self._appearance_changed(),
        )
        self.theme.pack(fill="x", padx=pad, pady=(0, 15))

        self._caption("Resolução")
        self.dpi = ChipGroup(
            self,
            [(120, "120"), (150, "150"), (200, "200"), (300, "300")],
            150,
            bg=SURFACE,
        )
        self.dpi.pack(fill="x", padx=pad, pady=(0, 15))

        self._caption("Qualidade")
        self.quality = ChipGroup(
            self,
            [(75, "75"), (85, "85"), (95, "95")],
            85,
            bg=SURFACE,
        )
        self.quality.pack(fill="x", padx=pad, pady=(0, 15))

        self._caption("Imagens")
        toggles = tk.Frame(self, bg=SURFACE)
        toggles.pack(fill="x", padx=pad, pady=(0, 4))
        self.images_btn = FlatButton(
            toggles, "", self._toggle_images, bg=SURFACE, padx=0, size=9
        )
        self.images_btn.pack(anchor="w")
        self.color_btn = FlatButton(
            toggles, "", self._toggle_color, bg=SURFACE, padx=0, size=9
        )
        self.color_btn.pack(anchor="w", pady=(2, 0))
        self._paint_toggles()

        self.action = PrimaryButton(
            self,
            "Converter agora",
            self.start,
            bg=SURFACE,
            width=300,
            height=44,
            radius=12,
        )
        self.action.pack(fill="x", padx=pad, pady=(18, 10))

        self.progress = ttk.Progressbar(
            self, style="Dark.Horizontal.TProgressbar", maximum=100, mode="determinate"
        )
        self.progress.pack(fill="x", padx=pad)

        self.status = tk.Label(
            self,
            text="Abra um PDF para começar.",
            bg=SURFACE,
            fg=MUTED,
            font=ui_font(9),
            justify="left",
            wraplength=300,
            anchor="w",
        )
        self.status.pack(fill="x", padx=pad, pady=(9, 0))

        self.results = tk.Frame(self, bg=SURFACE)
        self.results.pack(fill="x", padx=pad, pady=(10, 0))
        self.open_btn = FlatButton(
            self.results, "Abrir arquivo", self._open_result, bg=SURFACE, fg=ACCENT,
            padx=0, size=9,
        )
        self.folder_btn = FlatButton(
            self.results, "Mostrar na pasta", self._reveal, bg=SURFACE, padx=0, size=9
        )

        tk.Frame(self, bg=SURFACE).pack(fill="both", expand=True)
        tk.Label(
            self,
            text=f"Os ajustes de tema também valem para o leitor.",
            bg=SURFACE,
            fg="#5c6274",
            font=ui_font(8),
        ).pack(anchor="w", padx=pad, pady=(0, 16))

    def _caption(self, text: str) -> None:
        tk.Label(
            self,
            text=text.upper(),
            bg=SURFACE,
            fg=MUTED,
            font=ui_font(8, "bold"),
        ).pack(anchor="w", padx=22, pady=(0, 6))

    # ------------------------------------------------------------------ #
    # Estado
    # ------------------------------------------------------------------ #
    @property
    def theme_key(self) -> str:
        return str(self.theme.get())

    @property
    def keep_images(self) -> bool:
        return self._keep_images

    @property
    def keep_color(self) -> bool:
        return self._keep_color

    def set_source(self, path: Path | None) -> None:
        self._source = Path(path) if path else None
        if not self._busy:
            self._result = None
            self.open_btn.pack_forget()
            self.folder_btn.pack_forget()
            self.progress.configure(value=0)
            self.action.set_text("Converter agora")
        if self._source is None:
            self.hint.configure(text="Exporte uma cópia com o tema escuro aplicado.")
            self.status.configure(text="Abra um PDF para começar.", fg=MUTED)
        else:
            target = default_output_path(self._source)
            self.hint.configure(
                text=(
                    f"Vai gerar {target.name}, na mesma pasta do original, "
                    "com o tema escolhido."
                )
            )
            if not self._busy:
                self.status.configure(text=self._source.name, fg=MUTED)

    def _paint_toggles(self) -> None:
        self.images_btn.set_text(
            ("✓ " if self._keep_images else "    ") + "Preservar fotos"
        )
        self.images_btn.set_active(self._keep_images)
        self.color_btn.set_text(
            ("✓ " if self._keep_color else "    ") + "Manter cores de gráficos"
        )
        self.color_btn.set_active(self._keep_color)

    def _toggle_images(self) -> None:
        self._keep_images = not self._keep_images
        self._paint_toggles()
        self._appearance_changed()

    def _toggle_color(self) -> None:
        self._keep_color = not self._keep_color
        self._paint_toggles()
        self._appearance_changed()

    def _appearance_changed(self) -> None:
        self._on_appearance(self.theme_key, self._keep_color, self._keep_images)

    # ------------------------------------------------------------------ #
    # Conversão
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        if self._busy or self._source is None:
            return
        source = self._source
        target = default_output_path(source)
        options = Options(
            dpi=int(self.dpi.get()),
            quality=int(self.quality.get()),
            theme=self.theme_key,
            keep_images=self._keep_images,
            keep_color=self._keep_color,
        )
        self._busy = True
        self._result = None
        self.open_btn.pack_forget()
        self.folder_btn.pack_forget()
        self.action.set_enabled(False)
        self.action.set_text("Convertendo…")
        self.progress.configure(value=0)
        self.status.configure(text="Preparando…", fg=MUTED)
        threading.Thread(
            target=self._run, args=(source, target, options), daemon=True
        ).start()
        self.after(80, self._poll)

    def _run(self, source: Path, target: Path, options: Options) -> None:
        started = time.perf_counter()
        try:
            result = convert_pdf(
                source,
                target,
                options,
                progress=lambda done, total: self._queue.put(("progress", done, total)),
            )
        except ConversionError as exc:
            self._queue.put(("error", str(exc)))
        except Exception as exc:  # pragma: no cover - rede de segurança da GUI
            self._queue.put(("error", f"erro inesperado: {exc}"))
        else:
            self._queue.put(("done", result, time.perf_counter() - started))

    def _poll(self) -> None:
        try:
            while True:
                message = self._queue.get_nowait()
                kind = message[0]
                if kind == "progress":
                    _, done, total = message
                    self.progress.configure(value=done * 100 / max(total, 1))
                    self.status.configure(text=f"Convertendo… {done}/{total} páginas")
                elif kind == "done":
                    self._finish(message[1], message[2])
                    return
                elif kind == "error":
                    self._fail(message[1])
                    return
        except queue.Empty:
            pass
        if self._busy:
            self.after(80, self._poll)

    def _finish(self, result: Path, elapsed: float) -> None:
        self._busy = False
        self._result = result
        self.action.set_enabled(True)
        self.action.set_text("Converter novamente")
        self.progress.configure(value=100)
        size = result.stat().st_size / (1024 * 1024)
        self.status.configure(
            text=f"Pronto: {result.name} · {size:.1f} MB · {elapsed:.1f}s", fg=SOFT
        )
        self.open_btn.pack(side="left")
        self.folder_btn.pack(side="left", padx=(10, 0))
        self._notify(f"PDF escuro gerado: {result.name}")

    def _fail(self, message: str) -> None:
        self._busy = False
        self.action.set_enabled(True)
        self.action.set_text("Converter agora")
        self.progress.configure(value=0)
        self.status.configure(text=message, fg=DANGER)
        self._notify(message, error=True)

    def _open_result(self) -> None:
        if self._result is not None and self._result.exists():
            _open_path(self._result)

    def _reveal(self) -> None:
        if self._result is not None and self._result.exists():
            _reveal_path(self._result)


# ---------------------------------------------------------------------- #
# Janela principal
# ---------------------------------------------------------------------- #
class App(tk.Tk):
    """Janela única: leitor, tela inicial, painel de conversão e modo imersivo."""

    def __init__(self, initial_file: str | Path | None = None) -> None:
        super().__init__()
        self.withdraw()
        self.title(f"PDF Dark {__version__}")
        self.configure(bg=BG)
        self.minsize(560, 380)

        self._file: Path | None = None
        self._fullscreen = False
        self._toolbar_hidden = False
        self._sheet_open = False
        self._sheet_width = SHEET_WIDTH
        self._overlay: Pill | None = None
        self._overlay_job: str | None = None
        self._toast: tk.Frame | None = None
        self._toast_job: str | None = None
        self._header_flags: tuple[bool, ...] = (True, True, True, True, True)
        self._actions_visible = False

        self._build_style()
        self._build()
        self._bind_keys()
        self._center()

        self.update_idletasks()
        apply_dark_titlebar(self)
        set_app_icon(self)
        self.deiconify()
        self.bind("<Map>", lambda _event: apply_dark_titlebar(self))

        if initial_file is not None:
            self.after(120, lambda: self.open_path(initial_file))

    # ------------------------------------------------------------------ #
    # Construção
    # ------------------------------------------------------------------ #
    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:  # pragma: no cover - tema indisponível
            pass
        style.configure(
            "Dark.Horizontal.TProgressbar",
            troughcolor=SURFACE_ALT,
            background=ACCENT,
            bordercolor=SURFACE,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            borderwidth=0,
            thickness=4,
        )

    def _build(self) -> None:
        self.header = tk.Frame(self, bg=BG)
        self.header.pack(side="top", fill="x")
        self.header.bind("<Configure>", self._on_header_configure)

        line = tk.Frame(self.header, bg=BORDER, height=1)
        line.pack(side="bottom", fill="x")

        left = tk.Frame(self.header, bg=BG)
        left.pack(side="left", padx=(18, 0), pady=7)
        self.wordmark = tk.Frame(left, bg=BG)
        self.wordmark.pack(side="left")
        first = tk.Label(
            self.wordmark, text="PDF ", bg=BG, fg=TEXT, font=ui_font(11, "bold")
        )
        first.pack(side="left")
        second = tk.Label(
            self.wordmark, text="Dark", bg=BG, fg=ACCENT, font=ui_font(11, "bold")
        )
        second.pack(side="left")
        self.filename = tk.Label(
            left, text="", bg=BG, fg=MUTED, font=ui_font(9)
        )
        self.filename.pack(side="left", padx=(10, 0))
        self.open_btn = FlatButton(left, "Abrir", self.open_dialog)
        self.open_btn.pack(side="left", padx=(14, 0))

        self.page_label = tk.Label(
            self.header, text="", bg=BG, fg=MUTED, font=ui_font(9)
        )
        self.page_label.place(relx=0.5, rely=0.5, anchor="center")

        self.full_btn = FlatButton(
            self.header, "⛶", self.toggle_fullscreen, padx=9, size=14
        )
        self.full_btn.pack(side="right", padx=(0, 14), pady=7)
        self.toolbar_btn = FlatButton(
            self.header, "⌃", self.hide_toolbar, padx=9, size=15
        )
        self.toolbar_btn.pack(side="right", pady=7, padx=(0, 2))

        self.reader_actions = tk.Frame(self.header, bg=BG)
        actions = self.reader_actions
        self.theme_btn = FlatButton(actions, "● Escuro", self.toggle_dark, active=True)
        self._action_sep1 = tk.Frame(actions, bg=BORDER, width=1)
        self._zoom_out_btn = FlatButton(actions, "−", self.zoom_out, padx=9, size=12)
        self.zoom_label = tk.Label(
            actions, text="100%", bg=BG, fg=MUTED, font=ui_font(9), width=5
        )
        self._zoom_in_btn = FlatButton(actions, "+", self.zoom_in, padx=9, size=11)
        self.fit_btn = FlatButton(actions, "Ajustar", self.fit_width)
        self._action_sep2 = tk.Frame(actions, bg=BORDER, width=1)
        self.convert_btn = FlatButton(actions, "Converter", self.open_sheet, fg=ACCENT)

        self.body = tk.Frame(self, bg=READER_BG)
        self.body.pack(fill="both", expand=True)

        self.viewer = PdfViewer(self.body, on_state=self._on_viewer_state)
        self.viewer.pack(fill="both", expand=True)

        self.start = StartScreen(self.body, self.open_dialog)
        self.start.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.sheet = ConvertSheet(
            self.body,
            on_close=self.close_sheet,
            on_appearance=self._on_appearance,
            on_notify=self.toast,
        )

    # ------------------------------------------------------------------ #
    # Barra de ferramentas ocultável
    # ------------------------------------------------------------------ #
    def hide_toolbar(self) -> None:
        self._set_toolbar_hidden(True)

    def toggle_toolbar(self) -> str:
        self._set_toolbar_hidden(not self._toolbar_hidden)
        return "break"

    def _set_toolbar_hidden(self, hidden: bool) -> None:
        if hidden == self._toolbar_hidden:
            return
        self._toolbar_hidden = hidden
        if hidden:
            self.header.pack_forget()
            self.toast("Barra de ferramentas oculta · F10 para mostrar", ms=3800)
        elif not self._fullscreen:
            self.header.pack(side="top", fill="x", before=self.body)

    # ------------------------------------------------------------------ #
    # Cabeçalho responsivo
    # ------------------------------------------------------------------ #
    def _on_header_configure(self, event: tk.Event) -> None:
        if event.width > 1:
            self._layout_header(event.width)

    def _layout_header(self, width: int) -> None:
        """Mostra ou esconde itens conforme a janela fica estreita."""
        flags = (
            width >= 620,   # rótulo do zoom
            width >= 640,   # marca "PDF Dark"
            width >= 880,   # botão "Ajustar"
            width >= 1060,  # nome do arquivo
            width >= 680,   # indicador de página
        )
        if flags == self._header_flags:
            return
        self._header_flags = flags
        self._paint_left()
        if flags[4]:
            self.page_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.page_label.place_forget()
        self._layout_actions()

    def _paint_left(self) -> None:
        show_mark = self._header_flags[1]
        show_name = self._header_flags[3]
        for widget in (self.wordmark, self.filename, self.open_btn):
            widget.pack_forget()
        if show_mark:
            self.wordmark.pack(side="left")
        if show_name:
            self.filename.pack(side="left", padx=(10, 0))
        self.open_btn.pack(side="left", padx=(14, 0))

    def _layout_actions(self) -> None:
        """Reorganiza os controles do leitor na ordem, escondendo os menos essenciais."""
        if not self._actions_visible:
            return
        show_zoom = self._header_flags[0]
        show_fit = self._header_flags[2]
        items: list[tuple[tk.Widget, dict]] = [
            (self.theme_btn, {}),
            (self._action_sep1, {"fill": "y", "padx": 8, "pady": 12}),
            (self._zoom_out_btn, {}),
        ]
        if show_zoom:
            items.append((self.zoom_label, {}))
        items.append((self._zoom_in_btn, {}))
        if show_fit:
            items.append((self.fit_btn, {"padx": (4, 0)}))
        items += [
            (self._action_sep2, {"fill": "y", "padx": 8, "pady": 12}),
            (self.convert_btn, {}),
        ]
        for widget in (
            self.theme_btn,
            self._action_sep1,
            self._zoom_out_btn,
            self.zoom_label,
            self._zoom_in_btn,
            self.fit_btn,
            self._action_sep2,
            self.convert_btn,
        ):
            widget.pack_forget()
        for widget, options in items:
            widget.pack(side="left", **options)

    def _center(self) -> None:
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(1180, max(560, screen_w - 120))
        height = min(800, max(380, screen_h - 140))
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2 - 24)
        self.geometry(f"{width}x{height}+{x}+{y}")

    # ------------------------------------------------------------------ #
    # Documento
    # ------------------------------------------------------------------ #
    def open_dialog(self) -> None:
        initial = str(self._file.parent) if self._file else None
        path = filedialog.askopenfilename(
            parent=self,
            title="Abrir PDF",
            initialdir=initial,
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str | Path) -> None:
        target = Path(path).expanduser()
        try:
            total = self.viewer.load(target)
        except Exception as exc:
            self.toast(f"Não foi possível abrir: {_describe(exc)}", error=True)
            return

        self._file = target
        self.title(f"{target.name} — PDF Dark")
        self.filename.configure(text="· " + truncate(target.name, 34))
        self.start.place_forget()
        self.sheet.set_source(target)
        self._show_reader_actions(True)
        if self._fullscreen:
            self._show_overlay()
        pages = "página" if total == 1 else "páginas"
        self.toast(f"{truncate(target.name, 40)} · {total} {pages}")

    def _on_viewer_state(self, state: dict) -> None:
        ready = bool(state.get("ready"))
        self._show_reader_actions(ready)
        if ready:
            self.page_label.configure(text=f"{state['page']} / {state['pages']}")
        else:
            self.page_label.configure(text="")
        self.zoom_label.configure(text=f"{round(state['zoom'] * 100)}%")
        dark = bool(state.get("dark"))
        self.theme_btn.set_text("● Escuro" if dark else "○ Claro")
        self.theme_btn.set_active(dark)
        if self._overlay is not None:
            for button in self._overlay_buttons:
                if button[0] == "theme":
                    button[1].set_text("● Escuro" if dark else "○ Claro")
                    button[1].set_active(dark)
                elif button[0] == "page":
                    button[1].configure(
                        text=f"{state['page']} / {state['pages']}" if ready else ""
                    )

    def _show_reader_actions(self, visible: bool) -> None:
        if visible:
            if not self._actions_visible:
                self.reader_actions.pack(side="right", pady=7, padx=(0, 4))
                self._actions_visible = True
            self._layout_actions()
        elif self._actions_visible:
            self.reader_actions.pack_forget()
            self._actions_visible = False

    # ------------------------------------------------------------------ #
    # Ações do leitor
    # ------------------------------------------------------------------ #
    def toggle_dark(self) -> None:
        if not self._file:
            return
        dark = self.viewer.toggle_dark()
        self.toast("Modo escuro" if dark else "Modo claro", ms=1300)

    def zoom_in(self) -> None:
        if self._file:
            self.viewer.zoom_in()

    def zoom_out(self) -> None:
        if self._file:
            self.viewer.zoom_out()

    def fit_width(self) -> None:
        if self._file:
            self.viewer.fit_width()

    def _on_appearance(self, theme: str, keep_color: bool, keep_images: bool) -> None:
        self.viewer.set_options(
            Options(theme=theme, keep_color=keep_color, keep_images=keep_images)
        )

    # ------------------------------------------------------------------ #
    # Painel de conversão
    # ------------------------------------------------------------------ #
    def open_sheet(self) -> None:
        if not self._file:
            self.open_dialog()
            return
        if self._fullscreen:
            self.toggle_fullscreen()
        width = max(560, self.winfo_width())
        self._sheet_width = min(SHEET_WIDTH, max(320, width - 48))
        self._sheet_open = True
        self.sheet.place(
            relx=1.0,
            rely=0.0,
            anchor="ne",
            relheight=1.0,
            width=self._sheet_width,
        )
        self.sheet.lift()
        reserve = self._sheet_width if width >= self._sheet_width + 280 else 0
        self.viewer.pack_configure(padx=(0, reserve))
        self._show_reader_actions(True)

    def close_sheet(self) -> None:
        if not self._sheet_open:
            return
        self._sheet_open = False
        self.sheet.place_forget()
        self.viewer.pack_configure(padx=0)

    # ------------------------------------------------------------------ #
    # Modo imersivo / tela cheia
    # ------------------------------------------------------------------ #
    def toggle_fullscreen(self) -> str:
        self._fullscreen = not self._fullscreen
        self.attributes("-fullscreen", self._fullscreen)
        if self._fullscreen:
            self.header.pack_forget()
            self.after(220, self._show_overlay)
        else:
            if not self._toolbar_hidden:
                self.header.pack(side="top", fill="x", before=self.body)
            self._hide_overlay()
        return "break"

    def _build_overlay(self) -> None:
        self._overlay_buttons: list[tuple[str, tk.Widget]] = []
        self._overlay = Pill(self.body, bg=READER_BG)
        inner = self._overlay.inner

        theme_btn = FlatButton(inner, "● Escuro", self.toggle_dark, bg=SURFACE, active=True)
        theme_btn.pack(side="left", padx=(2, 0))
        self._overlay_buttons.append(("theme", theme_btn))

        page = tk.Label(
            inner, text="", bg=SURFACE, fg=MUTED, font=ui_font(9), width=9
        )
        page.pack(side="left", padx=(10, 4))
        self._overlay_buttons.append(("page", page))

        FlatButton(inner, "−", self.zoom_out, bg=SURFACE, padx=8, size=12).pack(side="left")
        FlatButton(inner, "+", self.zoom_in, bg=SURFACE, padx=8, size=11).pack(side="left")
        FlatButton(inner, "Ajustar", self.fit_width, bg=SURFACE).pack(side="left", padx=(2, 0))

        tk.Frame(inner, bg=BORDER, width=1).pack(side="left", fill="y", padx=8, pady=10)
        FlatButton(inner, "Converter", self.open_sheet, bg=SURFACE, fg=ACCENT).pack(side="left")
        FlatButton(
            inner, "✕", self.toggle_fullscreen, bg=SURFACE, padx=9, size=11
        ).pack(side="left", padx=(4, 0))

        self._overlay.fit()

    def _show_overlay(self) -> None:
        if not self._fullscreen:
            return
        if self._overlay is None:
            self._build_overlay()
        self._overlay.place(relx=0.5, y=16, anchor="n")
        tk.Misc.lift(self._overlay)
        self._arm_overlay()

    def _arm_overlay(self) -> None:
        if self._overlay_job is not None:
            try:
                self.after_cancel(self._overlay_job)
            except tk.TclError:
                pass
        self._overlay_job = self.after(2600, self._hide_overlay)

    def _hide_overlay(self) -> None:
        if self._overlay is not None:
            self._overlay.place_forget()
        self._overlay_job = None

    def _on_motion(self, event: tk.Event) -> None:
        if not self._fullscreen:
            return
        self._show_overlay()
        self._arm_overlay()

    # ------------------------------------------------------------------ #
    # Atalhos
    # ------------------------------------------------------------------ #
    def _bind_keys(self) -> None:
        self.bind("<Control-o>", lambda _event: self._key(self.open_dialog))
        self.bind("<Control-O>", lambda _event: self._key(self.open_dialog))
        self.bind("d", lambda _event: self._key(self.toggle_dark))
        self.bind("D", lambda _event: self._key(self.toggle_dark))
        self.bind("<F10>", lambda _event: self.toggle_toolbar())
        self.bind("<F11>", lambda _event: self.toggle_fullscreen())
        self.bind("<Escape>", lambda _event: self._key(self._escape))
        self.bind("<Control-plus>", lambda _event: self._key(self.zoom_in))
        self.bind("<Control-equal>", lambda _event: self._key(self.zoom_in))
        self.bind("<Control-KP_Add>", lambda _event: self._key(self.zoom_in))
        self.bind("<Control-minus>", lambda _event: self._key(self.zoom_out))
        self.bind("<Control-KP_Subtract>", lambda _event: self._key(self.zoom_out))
        self.bind("<Control-0>", lambda _event: self._key(self.fit_width))
        self.bind("<Control-KP_0>", lambda _event: self._key(self.fit_width))
        self.bind("<Prior>", lambda _event: self._key(self._page_up))
        self.bind("<Next>", lambda _event: self._key(self._page_down))
        self.bind("<Home>", lambda _event: self._key(lambda: self._goto(0)))
        self.bind("<End>", lambda _event: self._key(lambda: self._goto(10**9)))
        self.bind("<Left>", lambda _event: self._key(self._page_up))
        self.bind("<Right>", lambda _event: self._key(self._page_down))
        self.bind("<space>", lambda _event: self._key(self._page_down))
        self.bind("<Shift-space>", lambda _event: self._key(self._page_up))
        self.bind("<MouseWheel>", self._on_motion, add="+")
        self.bind_all("<Motion>", self._on_motion, add="+")

    def _key(self, action: Callable[[], None]) -> str:
        action()
        return "break"

    def _escape(self) -> None:
        if self._sheet_open:
            self.close_sheet()
        elif self._fullscreen:
            self.toggle_fullscreen()

    def _goto(self, index: int) -> None:
        if self._file and not self._sheet_open:
            self.viewer.goto_page(index)

    def _page_up(self) -> None:
        if self._file and not self._sheet_open:
            self.viewer.previous_page()

    def _page_down(self) -> None:
        if self._file and not self._sheet_open:
            self.viewer.next_page()

    # ------------------------------------------------------------------ #
    # Avisos
    # ------------------------------------------------------------------ #
    def toast(self, message: str, *, error: bool = False, ms: int = 3400) -> None:
        if self._toast is not None:
            try:
                self._toast.destroy()
            except tk.TclError:
                pass
        frame = tk.Frame(
            self.body,
            bg=SURFACE_ALT,
            highlightthickness=1,
            highlightbackground=DANGER if error else BORDER,
        )
        tk.Label(
            frame,
            text=message,
            bg=SURFACE_ALT,
            fg=DANGER if error else TEXT,
            font=ui_font(9),
            padx=16,
            pady=9,
            wraplength=520,
            justify="left",
        ).pack()
        frame.place(relx=0.5, rely=1.0, y=-26, anchor="s")
        frame.lift()
        self._toast = frame
        if self._toast_job is not None:
            try:
                self.after_cancel(self._toast_job)
            except tk.TclError:
                pass
        self._toast_job = self.after(ms, self._clear_toast)

    def _clear_toast(self) -> None:
        self._toast_job = None
        if self._toast is not None:
            try:
                self._toast.destroy()
            except tk.TclError:
                pass
            self._toast = None


# ---------------------------------------------------------------------- #
# Utilidades
# ---------------------------------------------------------------------- #
def _describe(exc: BaseException) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


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


def _reveal_path(path: Path) -> None:
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent)])
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    initial = Path(argv[0]) if argv else None
    try:
        app = App(initial)
    except tk.TclError as exc:  # pragma: no cover - ambiente sem display
        print(f"não foi possível abrir o aplicativo: {exc}", file=sys.stderr)
        print("use a linha de comando: pdf-dark arquivo.pdf", file=sys.stderr)
        return 1
    app.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
