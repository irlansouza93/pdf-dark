"""Interface gráfica simples em Tkinter (sem dependências extras)."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

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


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"PDF Dark {__version__}")
        self.minsize(620, 400)
        self.option_add("*tearOff", False)
        self._auto_output = ""
        self._queue: queue.Queue[tuple] = queue.Queue()
        self._busy = False
        self._result: Path | None = None

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.theme_var = tk.StringVar(value=THEMES[DEFAULT_THEME].label)
        self.dpi_var = tk.StringVar(value="150")
        self.quality_var = tk.StringVar(value="85")
        self.keep_color_var = tk.BooleanVar(value=False)
        self.keep_images_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Escolha um PDF para começar.")

        self._build()
        self._set_icon()
        self.input_var.trace_add("write", self._on_input_change)
        self.bind("<Return>", lambda _event: self.start())

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)

        heading = ttk.Label(
            root,
            text="PDF Dark",
            font=("Segoe UI", 18, "bold"),
        )
        heading.grid(row=0, column=0, columnspan=3, sticky="w")
        subtitle = ttk.Label(
            root,
            text="Transforme PDFs de fundo branco em um modo escuro confortável.",
            foreground="#555555",
        )
        subtitle.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))

        ttk.Label(root, text="Arquivo PDF:").grid(row=2, column=0, sticky="w", pady=4)
        self.input_entry = ttk.Entry(root, textvariable=self.input_var)
        self.input_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(root, text="Escolher…", command=self.pick_input).grid(
            row=2, column=2, pady=4
        )

        ttk.Label(root, text="Salvar como:").grid(row=3, column=0, sticky="w", pady=4)
        self.output_entry = ttk.Entry(root, textvariable=self.output_var)
        self.output_entry.grid(row=3, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(root, text="Salvar em…", command=self.pick_output).grid(
            row=3, column=2, pady=4
        )

        options = ttk.LabelFrame(root, text="Ajustes", padding=10)
        options.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(14, 4))
        options.grid_columnconfigure(1, weight=1)

        ttk.Label(options, text="Tema:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.theme_box = ttk.Combobox(
            options,
            state="readonly",
            values=[theme.label for theme in THEMES.values()],
            textvariable=self.theme_var,
            width=26,
        )
        self.theme_box.grid(row=0, column=1, sticky="w")

        resolution = ttk.Frame(options)
        resolution.grid(row=0, column=2, sticky="e")
        ttk.Label(resolution, text="DPI:").pack(side="left", padx=(0, 4))
        ttk.Spinbox(
            resolution,
            from_=MIN_DPI,
            to=MAX_DPI,
            increment=10,
            width=6,
            textvariable=self.dpi_var,
        ).pack(side="left", padx=(0, 12))
        ttk.Label(resolution, text="Qualidade:").pack(side="left", padx=(0, 4))
        ttk.Spinbox(
            resolution,
            from_=MIN_QUALITY,
            to=MAX_QUALITY,
            increment=5,
            width=5,
            textvariable=self.quality_var,
        ).pack(side="left")

        ttk.Checkbutton(
            options,
            text="Manter cores (código, gráficos e links)",
            variable=self.keep_color_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Checkbutton(
            options,
            text="Preservar fotos e ilustrações",
            variable=self.keep_images_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        ttk.Separator(root).grid(
            row=5, column=0, columnspan=3, sticky="ew", pady=14
        )

        self.progress = ttk.Progressbar(root, mode="determinate", maximum=100)
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew")
        ttk.Label(root, textvariable=self.status_var, wraplength=560).grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

        actions = ttk.Frame(root)
        actions.grid(row=8, column=0, columnspan=3, sticky="e", pady=(16, 0))
        self.open_button = ttk.Button(
            actions,
            text="Abrir PDF gerado",
            command=self.open_result,
            state="disabled",
        )
        self.open_button.pack(side="left", padx=(0, 8))
        self.convert_button = ttk.Button(
            actions, text="Converter", command=self.start, style="Accent.TButton"
        )
        self.convert_button.pack(side="left")

        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _set_icon(self) -> None:
        try:
            from importlib.resources import files

            icon = files("pdf_dark").joinpath("assets/icon.png")
            with icon.open("rb") as handle:
                self._icon_image = tk.PhotoImage(data=handle.read())
            self.iconphoto(True, self._icon_image)
        except Exception:  # ícone é opcional
            pass

    # ------------------------------------------------------------------ #
    # Ações
    # ------------------------------------------------------------------ #
    def pick_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Escolha um PDF",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self.input_var.set(path)
            self.input_entry.icursor("end")

    def pick_output(self) -> None:
        initial = self.output_var.get() or "documento-dark.pdf"
        path = filedialog.asksaveasfilename(
            title="Salvar PDF em modo escuro",
            defaultextension=".pdf",
            initialfile=Path(initial).name,
            initialdir=str(Path(initial).parent) if Path(initial).parent else None,
            filetypes=[("Arquivos PDF", "*.pdf")],
        )
        if path:
            self.output_var.set(path)

    def _on_input_change(self, *_args: object) -> None:
        raw = self.input_var.get().strip()
        if not raw:
            return
        auto = str(default_output_path(raw))
        if self.output_var.get().strip() in ("", self._auto_output):
            self.output_var.set(auto)
        self._auto_output = auto

    def start(self) -> None:
        if self._busy:
            return
        source = Path(self.input_var.get().strip())
        if not source.is_file():
            messagebox.showwarning("PDF Dark", "Escolha um arquivo PDF válido.")
            return
        if source.suffix.lower() != ".pdf":
            messagebox.showwarning("PDF Dark", "O arquivo escolhido não é um PDF.")
            return

        target_text = self.output_var.get().strip()
        target = Path(target_text) if target_text else default_output_path(source)
        if target.resolve() == source.resolve():
            messagebox.showwarning(
                "PDF Dark", "Escolha um nome de saída diferente do arquivo original."
            )
            return
        if target.exists() and not messagebox.askyesno(
            "Sobrescrever?", f"{target.name} já existe. Deseja substituir?"
        ):
            return

        try:
            options = Options(
                dpi=_number(self.dpi_var.get(), 150),
                quality=_number(self.quality_var.get(), 85),
                theme=_theme_key(self.theme_var.get()),
                keep_color=self.keep_color_var.get(),
                keep_images=self.keep_images_var.get(),
            )
        except ValueError as exc:
            messagebox.showerror("PDF Dark", str(exc))
            return

        self._busy = True
        self._result = None
        self.convert_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.progress.configure(value=0)
        self.status_var.set(f"Convertendo {source.name}…")

        thread = threading.Thread(
            target=self._worker, args=(source, target, options), daemon=True
        )
        thread.start()
        self.after(80, self._poll)

    def _worker(self, source: Path, target: Path, options: Options) -> None:
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
                    self.status_var.set(f"Convertendo… {done}/{total} páginas")
                elif kind == "done":
                    _, result, elapsed = message
                    self._finish(result, elapsed)
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
        self.progress.configure(value=100)
        size_mb = result.stat().st_size / (1024 * 1024)
        self.status_var.set(
            f"Pronto em {elapsed:.1f}s: {result.name} ({size_mb:.1f} MB)"
        )
        self.convert_button.configure(state="normal")
        self.open_button.configure(state="normal")
        if messagebox.askyesno("PDF Dark", f"Conversão concluída!\n\n{result}\n\nAbrir agora?"):
            self.open_result()

    def _fail(self, message: str) -> None:
        self._busy = False
        self.progress.configure(value=0)
        self.status_var.set("Não foi possível converter o arquivo.")
        self.convert_button.configure(state="normal")
        messagebox.showerror("PDF Dark", message)

    def open_result(self) -> None:
        if self._result and self._result.exists():
            try:
                if sys.platform == "win32":
                    os.startfile(self._result)  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(self._result)])
                else:
                    subprocess.Popen(["xdg-open", str(self._result)])
            except Exception as exc:
                messagebox.showerror("PDF Dark", f"Não foi possível abrir o arquivo: {exc}")


def _number(raw: str, fallback: int) -> int:
    try:
        return int(float(raw.replace(",", ".")))
    except (ValueError, AttributeError):
        return fallback


def _theme_key(label: str) -> str:
    for key, theme in THEMES.items():
        if theme.label == label:
            return key
    return DEFAULT_THEME


def main(argv: list[str] | None = None) -> int:
    del argv  # a GUI não recebe argumentos
    try:
        app = App()
    except tk.TclError as exc:  # pragma: no cover - ambiente sem display
        print(f"não foi possível abrir a interface gráfica: {exc}", file=sys.stderr)
        print("use a linha de comando: pdf-dark arquivo.pdf", file=sys.stderr)
        return 1
    app.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
