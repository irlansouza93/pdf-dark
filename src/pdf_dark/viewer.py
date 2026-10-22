"""Leitor de PDF com canvas próprio e alternância claro/escuro ao vivo."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageTk

from .converter import Options, render_page
from .widgets import BORDER, MUTED, PAGE, READER_BG, ui_font

MAX_RENDER_DPI = 300
CACHE_LIMIT = 10
MIN_ZOOM = 0.5
MAX_ZOOM = 5.0
ZOOM_STEP = 1.2

StateCallback = Callable[[dict], None]


@dataclass(frozen=True)
class PageBox:
    """Posição e tamanho de uma página no canvas, em pixels."""

    index: int
    x: float
    y: float
    width: int
    height: int


def fit_scale(
    sizes: list[tuple[float, float]], viewport_width: int, margin: int = 26
) -> float:
    """Escala (pixels por ponto) que faz a página mais larga caber na janela."""
    if not sizes:
        return 1.0
    widest = max(width for width, _ in sizes)
    if widest <= 0:
        return 1.0
    return max(0.05, (viewport_width - margin * 2) / widest)


def compute_layout(
    sizes: list[tuple[float, float]],
    scale: float,
    viewport_width: int,
    margin: int = 26,
    gap: int = 16,
) -> tuple[list[PageBox], int, int]:
    """Empilha as páginas verticalmente, centralizadas, com espaço entre elas.

    Devolve ``(caixas, largura_do_conteúdo, altura_do_conteúdo)``.
    """
    boxes: list[PageBox] = []
    y = float(margin)
    for index, (width_pt, height_pt) in enumerate(sizes):
        width = max(1, round(width_pt * scale))
        height = max(1, round(height_pt * scale))
        x = max(float(margin), (viewport_width - width) / 2)
        boxes.append(PageBox(index, x, y, width, height))
        y += height + gap
    if not boxes:
        return [], 0, 0
    content_height = round(y - gap + margin)
    content_width = max(box.width for box in boxes)
    return boxes, content_width, content_height


class PdfViewer(tk.Frame):
    """Canvas com rolagem contínua, zoom e renderização assíncrona das páginas."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_state: StateCallback | None = None,
        options: Options | None = None,
    ) -> None:
        super().__init__(master, bg=READER_BG)
        self._on_state = on_state
        self._render_options = options or Options()
        self._dark = True
        self._zoom = 1.0
        self._margin = 26
        self._gap = 16

        self._doc: pdfium.PdfDocument | None = None
        self._path: str | None = None
        self._sizes: list[tuple[float, float]] = []
        self._boxes: list[PageBox] = []
        self._items: list[dict] = []
        self._scale = 1.0
        self._current = -1

        self._cache: OrderedDict[tuple, ImageTk.PhotoImage] = OrderedDict()
        self._pending: set[tuple] = set()
        self._generation = 0
        self._drag_origin: tuple[float, float, float, float] | None = None
        self._resize_job: str | None = None
        self._poll_job: str | None = None
        self._destroyed = False

        self._jobs: queue.Queue = queue.Queue()
        self._results: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None

        self.canvas = tk.Canvas(
            self,
            bg=READER_BG,
            highlightthickness=0,
            bd=0,
            xscrollincrement=28,
            yscrollincrement=28,
            takefocus=True,
        )
        self.canvas.pack(fill="both", expand=True)
        self._bind_events()
        self._poll_job = self.after(50, self._poll)

    # ------------------------------------------------------------------ #
    # Documento
    # ------------------------------------------------------------------ #
    @property
    def has_document(self) -> bool:
        return bool(self._sizes)

    @property
    def page_count(self) -> int:
        return len(self._sizes)

    @property
    def is_dark(self) -> bool:
        return self._dark

    @property
    def page_number(self) -> int:
        return self._current + 1 if self._current >= 0 else 0

    def load(self, path: str | Path, password: str | None = None) -> int:
        """Abre um PDF e devolve o número de páginas.

        O documento atual só é fechado depois que o novo abre com sucesso,
        então um arquivo inválido não derruba a leitura em andamento.
        """
        document = pdfium.PdfDocument(str(path), password=password or None)
        total = len(document)
        if total == 0:
            document.close()
            raise ValueError("o PDF não possui páginas")

        sizes: list[tuple[float, float]] = []
        try:
            for index in range(total):
                page = document[index]
                try:
                    sizes.append(page.get_size())
                finally:
                    page.close()
        except Exception:
            document.close()
            raise

        self.close_document()
        self._doc = document
        self._path = str(path)
        self._sizes = sizes
        self._generation += 1
        self._cache.clear()
        self._pending.clear()
        self._ensure_worker()
        self._jobs.put(("load", self._generation, str(path), password))
        self.canvas.yview_moveto(0)
        self.relayout(preserve=False)
        self._current = 0 if sizes else -1
        self._notify()
        self.canvas.focus_set()
        return total

    def close_document(self) -> None:
        self._generation += 1
        self._cache.clear()
        self._pending.clear()
        self._jobs.put(("close",))
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
        self._doc = None
        self._path = None
        self._sizes = []
        self._boxes = []
        self._items = []
        self._current = -1
        try:
            self.canvas.delete("all")
            self.canvas.configure(scrollregion=(0, 0, 1, 1))
            self.canvas.yview_moveto(0)
        except tk.TclError:  # pragma: no cover - janela já destruída
            pass
        self._notify()

    # ------------------------------------------------------------------ #
    # Aparência
    # ------------------------------------------------------------------ #
    def set_dark(self, dark: bool) -> None:
        if dark == self._dark:
            return
        self._dark = dark
        self.relayout(preserve=True)
        self._notify()

    def toggle_dark(self) -> bool:
        self.set_dark(not self._dark)
        return self._dark

    def set_options(self, options: Options) -> None:
        self._render_options = options
        self._cache.clear()
        self.relayout(preserve=True)

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        self.relayout(preserve=True)
        self._notify()

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom * ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom / ZOOM_STEP)

    def fit_width(self) -> None:
        self.set_zoom(1.0)

    # ------------------------------------------------------------------ #
    # Navegação
    # ------------------------------------------------------------------ #
    def goto_page(self, index: int) -> None:
        if not self._boxes:
            return
        index = max(0, min(len(self._boxes) - 1, index))
        box = self._boxes[index]
        self.canvas.yview_moveto(max(0.0, min(1.0, box.y / max(1, self._total_height()))))
        self._update_current()
        self._request_visible()

    def next_page(self) -> None:
        self.goto_page(self._current + 1)

    def previous_page(self) -> None:
        self.goto_page(self._current - 1)

    def scroll_pages(self, amount: int) -> None:
        self.canvas.yview_scroll(amount, "pages")
        self._on_scrolled()

    def scroll_lines(self, amount: int) -> None:
        self.canvas.yview_scroll(amount, "units")
        self._on_scrolled()

    # ------------------------------------------------------------------ #
    # Layout e renderização
    # ------------------------------------------------------------------ #
    def relayout(self, preserve: bool = True) -> None:
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1 or height <= 1 or not self._sizes:
            return

        anchor = self._scroll_anchor() if preserve else None
        base = fit_scale(self._sizes, width, self._margin)
        self._scale = base * self._zoom
        boxes, content_width, content_height = compute_layout(
            self._sizes, self._scale, width, self._margin, self._gap
        )
        self._boxes = boxes

        self.canvas.delete("all")
        self._items = []
        scroll_width = max(width, content_width + self._margin)
        self.canvas.configure(scrollregion=(0, 0, scroll_width, max(content_height, height)))
        for box in boxes:
            rect = self.canvas.create_rectangle(
                box.x, box.y, box.x + box.width, box.y + box.height,
                fill=PAGE, outline=BORDER, width=1,
            )
            label = self.canvas.create_text(
                box.x + box.width / 2,
                box.y + box.height / 2,
                text=str(box.index + 1),
                fill=MUTED,
                font=ui_font(11),
            )
            self._items.append({"rect": rect, "label": label, "image": None, "photo": None})

        self._restore_anchor(anchor)
        self._request_visible()

    def _request_visible(self) -> None:
        if not self._boxes:
            return
        top = self.canvas.canvasy(0)
        bottom = top + max(self.canvas.winfo_height(), 1)
        for box in self._boxes:
            if box.y + box.height < top - 350:
                continue
            if box.y > bottom + 350:
                break
            self._request(box.index)

    def _request(self, index: int) -> None:
        key = self._cache_key(index)
        if key in self._cache:
            self._draw_page(index)
            return
        if key in self._pending or self._destroyed:
            return
        self._pending.add(key)
        scale = min(self._scale, MAX_RENDER_DPI / 72)
        self._jobs.put(
            (
                "render",
                self._generation,
                index,
                scale,
                self._dark,
                self._render_options,
                key,
            )
        )

    def _cache_key(self, index: int) -> tuple:
        options = self._render_options
        return (
            index,
            round(self._scale, 3),
            self._dark,
            options.theme,
            round(options.contrast, 2),
            options.keep_color,
            options.keep_images,
        )

    def _draw_page(self, index: int) -> None:
        if index >= len(self._items) or index >= len(self._boxes):
            return
        photo = self._cache.get(self._cache_key(index))
        if photo is None:
            return
        box = self._boxes[index]
        items = self._items[index]
        if items["image"] is None:
            items["image"] = self.canvas.create_image(
                box.x, box.y, anchor="nw", image=photo
            )
        else:
            self.canvas.itemconfigure(items["image"], image=photo)
        items["photo"] = photo
        if items["label"] is not None:
            self.canvas.itemconfigure(items["label"], state="hidden")

    def _ensure_worker(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._work, name="pdf-render", daemon=True)
        self._worker.start()

    def _work(self) -> None:
        document: pdfium.PdfDocument | None = None
        while True:
            job = self._jobs.get()
            if job is None:
                break
            kind = job[0]
            try:
                if kind == "close":
                    if document is not None:
                        document.close()
                        document = None
                    continue
                if kind == "load":
                    _, _, path, password = job
                    if document is not None:
                        document.close()
                        document = None
                    document = pdfium.PdfDocument(path, password=password or None)
                    continue

                _, generation, index, scale, dark, options, key = job
                if document is None:
                    continue
                page = document[index]
                try:
                    image = render_page(page, scale, options, dark=dark)
                finally:
                    page.close()
                self._results.put((generation, index, key, image))
            except Exception as exc:  # página problemática não derruba o leitor
                if kind == "render":
                    self._results.put((job[1], job[2], job[6], exc))
        if document is not None:
            try:
                document.close()
            except Exception:
                pass

    def _poll(self) -> None:
        if self._destroyed:
            return
        try:
            while True:
                generation, index, key, payload = self._results.get_nowait()
                self._pending.discard(key)
                if generation != self._generation or isinstance(payload, Exception):
                    continue
                self._store(index, key, payload)
                self._draw_page(index)
        except queue.Empty:
            pass
        self._update_current()
        self._poll_job = self.after(60, self._poll)

    def _store(self, index: int, key: tuple, image: Image.Image) -> None:
        box = self._boxes[index]
        if image.size != (box.width, box.height):
            image = image.resize((box.width, box.height), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        self._cache[key] = photo
        self._cache.move_to_end(key)
        while len(self._cache) > CACHE_LIMIT:
            self._cache.popitem(last=False)

    # ------------------------------------------------------------------ #
    # Rolagem
    # ------------------------------------------------------------------ #
    def _scroll_anchor(self) -> tuple[int, float] | None:
        if not self._boxes:
            return None
        top = self.canvas.canvasy(0)
        for box in self._boxes:
            if box.y <= top <= box.y + box.height:
                return box.index, (top - box.y) / max(box.height, 1)
        return self._current if self._current >= 0 else 0, 0.0

    def _restore_anchor(self, anchor: tuple[int, float] | None) -> None:
        if anchor is None or not self._boxes:
            return
        index, ratio = anchor
        index = max(0, min(len(self._boxes) - 1, index))
        box = self._boxes[index]
        target = box.y + ratio * box.height
        self.canvas.yview_moveto(
            max(0.0, min(1.0, target / max(1, self._total_height())))
        )

    def _total_height(self) -> int:
        try:
            return int(self.canvas.cget("scrollregion").split()[3])
        except (IndexError, ValueError):
            return 1

    def _update_current(self) -> None:
        if not self._boxes:
            if self._current != -1:
                self._current = -1
                self._notify()
            return
        top = self.canvas.canvasy(0) + self.canvas.winfo_height() * 0.35
        current = 0
        for box in self._boxes:
            if top >= box.y:
                current = box.index
            else:
                break
        if current != self._current:
            self._current = current
            self._notify()

    def _on_scrolled(self) -> None:
        self._update_current()
        self._request_visible()

    def _on_configure(self, _event: tk.Event) -> None:
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except tk.TclError:
                pass
        self._resize_job = self.after(120, self._apply_resize)

    def _apply_resize(self) -> None:
        self._resize_job = None
        self.relayout(preserve=True)

    # ------------------------------------------------------------------ #
    # Eventos
    # ------------------------------------------------------------------ #
    def _bind_events(self) -> None:
        canvas = self.canvas
        canvas.bind("<Configure>", self._on_configure)
        canvas.bind("<MouseWheel>", self._on_wheel)
        canvas.bind("<Shift-MouseWheel>", self._on_wheel_horizontal)
        canvas.bind("<Button-4>", lambda event: self._wheel_linux(event, -1))
        canvas.bind("<Button-5>", lambda event: self._wheel_linux(event, 1))
        canvas.bind("<Control-MouseWheel>", self._on_wheel_zoom)
        canvas.bind("<ButtonPress-1>", self._pan_start)
        canvas.bind("<B1-Motion>", self._pan_move)
        canvas.bind("<ButtonRelease-1>", self._pan_end)

    def _on_wheel(self, event: tk.Event) -> None:
        delta = int(getattr(event, "delta", 0))
        steps = int(-delta / 120 * 3) or (-1 if delta > 0 else 1)
        self.canvas.yview_scroll(steps, "units")
        self._on_scrolled()

    def _on_wheel_horizontal(self, event: tk.Event) -> None:
        delta = int(getattr(event, "delta", 0))
        steps = int(-delta / 120 * 3) or (-1 if delta > 0 else 1)
        self.canvas.xview_scroll(steps, "units")

    def _on_wheel_zoom(self, event: tk.Event) -> None:
        if int(getattr(event, "delta", 0)) > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        return "break"

    def _wheel_linux(self, event: tk.Event, _direction: int) -> None:
        if getattr(event, "num", None) == 4:
            self.zoom_in() if event.state & 0x0004 else self.scroll_lines(-3)
        else:
            self.zoom_out() if event.state & 0x0004 else self.scroll_lines(3)

    def _pan_start(self, event: tk.Event) -> None:
        self.canvas.scan_mark(event.x, event.y)
        self._drag_origin = (
            self.canvas.canvasx(event.x),
            self.canvas.canvasy(event.y),
            event.x,
            event.y,
        )
        self.canvas.configure(cursor="fleur")

    def _pan_move(self, event: tk.Event) -> None:
        if self._drag_origin is None:
            return
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _pan_end(self, _event: tk.Event) -> None:
        self._drag_origin = None
        self.canvas.configure(cursor="")
        self._on_scrolled()

    # ------------------------------------------------------------------ #
    # Sinais
    # ------------------------------------------------------------------ #
    def _notify(self) -> None:
        if self._on_state is None or self._destroyed:
            return
        self._on_state(
            {
                "page": self.page_number,
                "pages": self.page_count,
                "zoom": self._zoom,
                "dark": self._dark,
                "ready": self.has_document,
                "path": self._path,
            }
        )

    def destroy(self) -> None:  # pragma: no cover - ciclo de vida da janela
        self._destroyed = True
        if self._poll_job is not None:
            try:
                self.after_cancel(self._poll_job)
            except tk.TclError:
                pass
        self._jobs.put(None)
        self.close_document()
        super().destroy()
