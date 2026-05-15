import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from processor import MdImageProcessor


class MdImageApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Markdown 图片处理工具")
        self.root.geometry("720x560")
        self.root.minsize(600, 480)

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="keep_structure")
        self.processing = False

        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.LabelFrame(main_frame, text="输入设置", padding="8")
        input_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(input_frame, text="输入文件夹:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 4))
        ttk.Entry(input_frame, textvariable=self.input_var).grid(
            row=0, column=1, sticky=tk.EW, padx=(0, 4))
        ttk.Button(input_frame, text="浏览...",
                   command=self._browse_input).grid(row=0, column=2)

        ttk.Label(input_frame, text="输出文件夹:").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 4), pady=(6, 0))
        ttk.Entry(input_frame, textvariable=self.output_var).grid(
            row=1, column=1, sticky=tk.EW, padx=(0, 4), pady=(6, 0))
        ttk.Button(input_frame, text="浏览...",
                   command=self._browse_output).grid(row=1, column=2, pady=(6, 0))

        input_frame.columnconfigure(1, weight=1)

        mode_frame = ttk.LabelFrame(main_frame, text="输出模式", padding="8")
        mode_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Radiobutton(
            mode_frame, text="保持原目录结构（推荐）",
            variable=self.mode_var, value="keep_structure"
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            mode_frame, text="拍扁到平级文件夹（所有 md 直接放在输出目录下）",
            variable=self.mode_var, value="flatten"
        ).pack(anchor=tk.W)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        self.process_btn = ttk.Button(
            btn_frame, text="开始处理", command=self._start_processing)
        self.process_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.cancel_btn = ttk.Button(
            btn_frame, text="取消", command=self._cancel_processing,
            state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(
            main_frame, mode='determinate', maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 6))

        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="4")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 9), height=14)
        log_scroll = ttk.Scrollbar(
            log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text.tag_config("info", foreground="#333333")
        self.log_text.tag_config("warn", foreground="#cc8800")
        self.log_text.tag_config("error", foreground="#cc0000")
        self.log_text.tag_config("progress", foreground="#0066cc")

    def _browse_input(self):
        path = filedialog.askdirectory(title="选择输入文件夹（包含 md 文件）")
        if path:
            self.input_var.set(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="选择输出文件夹")
        if path:
            self.output_var.set(path)

    def _log(self, level: str, message: str):
        self.log_text.configure(state=tk.NORMAL)
        tags = (level,)
        self.log_text.insert(tk.END, message + "\n", tags)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_progress(self, value):
        def _update():
            self.progress['value'] = value
        self.root.after(0, _update)

    def _on_callback(self, level, message):
        if level == "progress":
            self._set_progress(message)
        else:
            self.root.after(0, lambda: self._log(level, message))

    def _start_processing(self):
        input_path = self.input_var.get().strip()
        output_path = self.output_var.get().strip()

        if not input_path:
            messagebox.showwarning("提示", "请先选择输入文件夹")
            return
        if not os.path.isdir(input_path):
            messagebox.showerror("错误", "输入文件夹不存在")
            return
        if not output_path:
            messagebox.showwarning("提示", "请先选择输出文件夹")
            return
        if not os.path.isdir(output_path):
            messagebox.showerror("错误", "输出文件夹不存在")
            return

        input_abs = os.path.abspath(input_path)
        output_abs = os.path.abspath(output_path)
        if os.path.commonpath([input_abs, output_abs]) == output_abs:
            messagebox.showerror(
                "错误", "输出文件夹不能是输入文件夹的子目录，"
                        "这会导致递归处理")
            return

        keep_structure = self.mode_var.get() == "keep_structure"

        self._clear_log()
        self._log("info", f"输入文件夹: {input_path}")
        self._log("info",
                  f"输出模式: {'保持目录结构' if keep_structure else '拍扁到平级'}")
        self._log("info", f"输出文件夹: {output_path}")
        self._log("info", "=" * 50)

        self._set_processing_state(True)

        self.processor = MdImageProcessor(input_path, output_path,
                                          keep_structure)

        thread = threading.Thread(
            target=self._run_processor, daemon=True)
        thread.start()

    def _run_processor(self):
        try:
            stats = self.processor.run(callback=self._on_callback)
            self.root.after(0, lambda: self._on_done(stats))
        except Exception as e:
            self.root.after(0, lambda: self._on_error(str(e)))

    def _on_done(self, stats):
        self._set_processing_state(False)
        self._log("info", "=" * 50)
        self._log("info",
                  f"处理完毕: 共 {stats['total']} 个文件, "
                  f"成功 {stats['success']}, 失败 {stats['failed']}")
        self._set_progress(100)

    def _on_error(self, error_msg):
        self._set_processing_state(False)
        self._log("error", f"发生错误: {error_msg}")
        messagebox.showerror("错误", f"处理过程发生异常:\n{error_msg}")

    def _cancel_processing(self):
        if self.processing and hasattr(self, 'processor'):
            self.processor.cancel()
            self._log("warn", "正在取消...")

    def _set_processing_state(self, processing: bool):
        self.processing = processing
        if processing:
            self.process_btn.configure(state=tk.DISABLED)
            self.cancel_btn.configure(state=tk.NORMAL)
            self.progress['value'] = 0
        else:
            self.process_btn.configure(state=tk.NORMAL)
            self.cancel_btn.configure(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self.progress['value'] = 0


def launch():
    root = tk.Tk()
    MdImageApp(root)
    root.mainloop()
