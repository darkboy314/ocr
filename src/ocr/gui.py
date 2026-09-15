"""Cross-platform Chinese desktop interface for the OCR workflow."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Callable

from ocr import find_files_by_name_keyword, process_files


class OcrGui:
    """Tkinter UI for selecting input files and running the OCR pipeline."""

    def __init__(self, root: tk.Tk | None = None) -> None:
        self.root = root or tk.Tk()
        self.root.title("文档 OCR 工具")
        self.root.minsize(680, 420)
        self.root.geometry("760x480")

        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.keyword = tk.StringVar()
        self.status = tk.StringVar(value="请选择输入目录和输出目录")
        self.file_count = tk.StringVar(value="匹配文件：0")
        self.file_types: dict[str, tk.BooleanVar] = {
            ".pdf": tk.BooleanVar(value=True),
            ".png": tk.BooleanVar(value=True),
            ".jpg": tk.BooleanVar(value=True),
        }
        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._running = False
        self._build_ui()
        self._refresh_count()

    def _build_ui(self) -> None:
        font_family = self._select_font_family()
        self._ui_font = tkfont.Font(
            self.root, family=font_family, size=11, name="OcrUiFont"
        )
        ui_font_spec = (font_family, 11)
        self.root.option_add("*Font", ui_font_spec)
        style = ttk.Style(self.root)
        # Configure each native ttk class explicitly; some Windows themes
        # ignore the "." style when resolving label and button fonts.
        for style_name in ("TLabel", "TButton", "TCheckbutton", "TEntry"):
            style.configure(style_name, font=ui_font_spec)
        style.configure(
            "Title.TLabel",
            font=(font_family, 18, "bold"),
        )
        style.configure("Hint.TLabel", foreground="#666666")

        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill=tk.BOTH, expand=True)
        ttk.Label(outer, text="文档 OCR 工具", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="选择要处理的文件，识别结果和 OCR 原始文件将保存到输出目录。",
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(6, 20))

        form = ttk.Frame(outer)
        form.pack(fill=tk.X)
        self._path_row(form, 0, "输入目录", self.input_dir, self._choose_input)
        self._path_row(form, 1, "输出目录", self.output_dir, self._choose_output)

        ttk.Label(form, text="文件类型").grid(row=2, column=0, sticky=tk.W, pady=10)
        types = ttk.Frame(form)
        types.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=10)
        for label, extension in (("PDF", ".pdf"), ("PNG", ".png"), ("JPG", ".jpg")):
            ttk.Checkbutton(
                types,
                text=label,
                variable=self.file_types[extension],
                command=self._refresh_count,
            ).pack(side=tk.LEFT, padx=(0, 18))

        ttk.Label(form, text="文件关键词").grid(row=3, column=0, sticky=tk.W, pady=10)
        keyword_entry = ttk.Entry(form, textvariable=self.keyword)
        keyword_entry.grid(row=3, column=1, columnspan=2, sticky=tk.EW, pady=10)
        keyword_entry.bind("<KeyRelease>", lambda _event: self._refresh_count())
        ttk.Label(form, text="留空表示不限制关键词", style="Hint.TLabel").grid(
            row=4, column=1, columnspan=2, sticky=tk.W
        )
        form.columnconfigure(1, weight=1)

        ttk.Separator(outer).pack(fill=tk.X, pady=22)
        ttk.Label(outer, textvariable=self.file_count).pack(anchor=tk.W)
        ttk.Label(outer, textvariable=self.status, style="Hint.TLabel").pack(
            anchor=tk.W, pady=(8, 0)
        )
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(12, 18))
        self.start_button = ttk.Button(outer, text="开始处理", command=self._start)
        self.start_button.pack(anchor=tk.E)

    def _select_font_family(self) -> str:
        """Choose an installed family with Chinese glyphs on each platform."""
        available = {
            family.casefold(): family for family in tkfont.families(self.root)
        }
        platform_fonts = {
            "win32": (
                "Microsoft YaHei",
                "Microsoft YaHei UI",
                "DengXian",
                "SimSun",
                "NSimSun",
                "Segoe UI",
            ),
            "darwin": (
                "PingFang SC",
                "Hiragino Sans GB",
                "Songti SC",
                "Arial Unicode MS",
            ),
            "linux": (
                "Noto Sans CJK SC",
                "Source Han Sans CN",
                "WenQuanYi Zen Hei",
                "Microsoft YaHei",
                "SimSun",
                "NSimSun",
                "DejaVu Sans",
            ),
        }
        candidates = platform_fonts.get(sys.platform, platform_fonts["linux"])
        for candidate in candidates:
            if candidate.casefold() in available:
                family = available[candidate.casefold()]
                probe = tkfont.Font(self.root, family=family, size=11)
                if probe.measure("中") > 0 and probe.actual("family") != "fixed":
                    return family
        # Tk may not expose fontconfig families in headless Linux sessions,
        # but the named family can still be resolved when the real UI starts.
        return candidates[0]

    def _path_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        choose: Callable[[], None],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=10)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky=tk.EW, pady=10
        )
        ttk.Button(parent, text="浏览...", command=choose).grid(
            row=row, column=2, padx=(10, 0), pady=10
        )

    def _choose_input(self) -> None:
        selected = filedialog.askdirectory(title="选择输入目录")
        if selected:
            self.input_dir.set(selected)
            if not self.output_dir.get():
                self.output_dir.set(str(Path(selected) / "output"))
            self._refresh_count()

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(title="选择输出目录")
        if selected:
            self.output_dir.set(selected)

    def _selected_extensions(self) -> list[str]:
        return [extension for extension, enabled in self.file_types.items() if enabled.get()]

    def _refresh_count(self) -> None:
        directory = self.input_dir.get()
        extensions = self._selected_extensions()
        if not directory or not extensions:
            self.file_count.set("匹配文件：0")
            return
        try:
            count = len(find_files_by_name_keyword(directory, self.keyword.get().strip(), extensions))
        except OSError:
            count = 0
        self.file_count.set(f"匹配文件：{count}")

    def _start(self) -> None:
        input_dir = self.input_dir.get().strip()
        output_dir = self.output_dir.get().strip()
        extensions = self._selected_extensions()
        if not input_dir or not Path(input_dir).is_dir():
            messagebox.showerror("输入错误", "请选择有效的输入目录。")
            return
        if not output_dir:
            messagebox.showerror("输入错误", "请选择输出目录。")
            return
        if not extensions:
            messagebox.showerror("输入错误", "至少选择一种文件类型。")
            return
        self._running = True
        self.start_button.configure(state=tk.DISABLED)
        self.progress.start(10)
        self.status.set("正在处理，请稍候...")
        threading.Thread(
            target=self._worker,
            args=(input_dir, output_dir, self.keyword.get().strip(), extensions),
            daemon=True,
        ).start()
        self.root.after(100, self._poll_events)

    def _worker(self, input_dir: str, output_dir: str, keyword: str, extensions: list[str]) -> None:
        try:
            count = process_files(input_dir, output_dir, keyword, extensions)
            self._events.put(("success", count))
        except Exception as error:
            self._events.put(("error", error))

    def _poll_events(self) -> None:
        try:
            event, value = self._events.get_nowait()
        except queue.Empty:
            if self._running:
                self.root.after(100, self._poll_events)
            return
        self._running = False
        self.progress.stop()
        self.start_button.configure(state=tk.NORMAL)
        if event == "success":
            self.status.set(f"处理完成，共处理 {value} 个文件。")
            messagebox.showinfo("处理完成", f"已处理 {value} 个文件。")
        else:
            self.status.set("处理失败。")
            messagebox.showerror("处理失败", str(value))

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    OcrGui().run()
