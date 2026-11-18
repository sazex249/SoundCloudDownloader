import os
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


APP_TITLE = "SoundCloud Profile Downloader"


class SoundCloudDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("720x540")
        self.root.minsize(620, 460)

        self.url_var = tk.StringVar()
        self.folder_var = tk.StringVar(value=str(Path.home() / "Music" / "SoundCloud"))
        self.status_var = tk.StringVar(value="Вставьте ссылку на профиль SoundCloud.")
        self.running = False

        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="SoundCloud Downloader", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Скачивание публичных треков из профиля, если загрузка разрешена и доступна.",
            wraplength=660
        ).pack(anchor="w", pady=(4, 16))

        ttk.Label(outer, text="Ссылка на профиль или плейлист SoundCloud:").pack(anchor="w")
        url_row = ttk.Frame(outer)
        url_row.pack(fill="x", pady=(5, 12))
        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.url_entry.focus_set()
        ttk.Button(url_row, text="Вставить", command=self.paste_url).pack(side="left", padx=(8, 0))

        ttk.Label(outer, text="Папка для сохранения:").pack(anchor="w")
        folder_row = ttk.Frame(outer)
        folder_row.pack(fill="x", pady=(5, 14))
        ttk.Entry(folder_row, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        ttk.Button(folder_row, text="Обзор…", command=self.choose_folder).pack(side="left", padx=(8, 0))

        options = ttk.LabelFrame(outer, text="Настройки", padding=10)
        options.pack(fill="x", pady=(0, 12))
        self.mp3_var = tk.BooleanVar(value=True)
        self.cover_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options, text="Конвертировать в MP3 (требуется FFmpeg)", variable=self.mp3_var).pack(anchor="w")
        ttk.Checkbutton(options, text="Добавлять обложку и метаданные, если доступны", variable=self.cover_var).pack(anchor="w")

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(4, 5))
        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w")

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(12, 8))
        self.start_button = ttk.Button(buttons, text="Начать скачивание", command=self.start_download)
        self.start_button.pack(side="left")
        ttk.Button(buttons, text="Открыть папку", command=self.open_folder).pack(side="left", padx=8)

        ttk.Label(outer, text="Журнал:").pack(anchor="w", pady=(8, 3))
        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=10, wrap="word", state="disabled", font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(
            outer,
            text="Используйте программу только для треков, которые вы вправе сохранять. "
                 "Она не обходит приватность, платный доступ или технические ограничения.",
            wraplength=660,
            foreground="#666666"
        ).pack(anchor="w", pady=(10, 0))

    def log_line(self, message):
        def add():
            self.log.configure(state="normal")
            self.log.insert("end", message + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(0, add)

    def paste_url(self):
        try:
            self.url_var.set(self.root.clipboard_get().strip())
        except tk.TclError:
            pass

    def choose_folder(self):
        selected = filedialog.askdirectory(initialdir=self.folder_var.get() or str(Path.home()))
        if selected:
            self.folder_var.set(selected)

    def open_folder(self):
        folder = Path(self.folder_var.get()).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(folder)
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(folder)])

    def start_download(self):
        if self.running:
            return
        url = self.url_var.get().strip()
        if not re.match(r"^https?://(www\.)?soundcloud\.com/", url, re.I):
            messagebox.showerror("Неверная ссылка", "Вставьте ссылку вида https://soundcloud.com/имя-пользователя")
            return
        if yt_dlp is None:
            messagebox.showerror(
                "Не установлен yt-dlp",
                "Установите зависимости командой:\npy -m pip install -U yt-dlp"
            )
            return

        folder = Path(self.folder_var.get()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Ошибка папки", str(exc))
            return

        self.running = True
        self.start_button.configure(state="disabled")
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)
        self.status_var.set("Подключение к SoundCloud…")
        self.log_line(f"Адрес: {url}")
        threading.Thread(target=self.download_worker, args=(url, folder), daemon=True).start()

    def download_worker(self, url, folder):
        def progress_hook(data):
            status = data.get("status")
            if status == "downloading":
                name = Path(data.get("filename", "")).name
                percent = data.get("_percent_str", "").strip()
                speed = data.get("_speed_str", "").strip()
                self.root.after(0, lambda: self.status_var.set(f"{name}  {percent}  {speed}"))
            elif status == "finished":
                self.log_line("Файл загружен, выполняется обработка…")

        def logger_warning(message):
            self.log_line("Предупреждение: " + str(message))

        opts = {
            "format": "bestaudio/best",
            "outtmpl": str(folder / "%(uploader)s" / "%(title)s [%(id)s].%(ext)s"),
            "noplaylist": False,
            "ignoreerrors": True,
            "continuedl": True,
            "download_archive": str(folder / "downloaded.txt"),
            "windowsfilenames": True,
            "trim_file_name": 180,
            "quiet": True,
            "no_warnings": False,
            "progress_hooks": [progress_hook],
            "logger": type("GuiLogger", (), {
                "debug": lambda _self, msg: None,
                "info": lambda _self, msg: None,
                "warning": lambda _self, msg: logger_warning(msg),
                "error": lambda _self, msg: self.log_line("Ошибка: " + str(msg)),
            })(),
        }

        if self.mp3_var.get():
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }]
        if self.cover_var.get():
            opts["writethumbnail"] = True
            opts["postprocessors"] = opts.get("postprocessors", []) + [
                {"key": "EmbedThumbnail"},
                {"key": "FFmpegMetadata"},
            ]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            if info is None:
                self.log_line("Не удалось получить список треков. Проверьте ссылку и доступность профиля.")
            else:
                self.log_line("Обработка завершена.")
        except Exception as exc:
            self.log_line("Сбой: " + str(exc))
        finally:
            def finish():
                self.progress.stop()
                self.progress.configure(mode="determinate", value=0)
                self.running = False
                self.start_button.configure(state="normal")
                self.status_var.set("Готово. Проверьте папку сохранения.")
            self.root.after(0, finish)


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    SoundCloudDownloader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
