"""Simple Windows desktop app to organize photos by capture date.

The app lets a user choose a source folder and destination folder.
Each image can be previewed, skipped, copied to the destination
(foldered by capture date), or deleted from the source.
"""
from __future__ import annotations

import shutil
import threading
import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from PIL import Image, ImageTk, ExifTags

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".bmp"}


@dataclass
class PhotoItem:
    path: Path
    date_taken: datetime
    action: str = "Copy"
    item_id: Optional[str] = field(default=None)

    @property
    def date_label(self) -> str:
        return self.date_taken.strftime("%Y-%m-%d")

    @property
    def name(self) -> str:
        return self.path.name


class PhotoOrganizerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Photo Organizer")
        self.root.geometry("1050x700")

        self.source_dir: Optional[Path] = None
        self.destination_dir: Optional[Path] = None
        self.photos: List[PhotoItem] = []
        self.preview_cache: Dict[str, ImageTk.PhotoImage] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Source folder:").grid(row=0, column=0, sticky=tk.W)
        self.source_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.source_var, width=60, state="readonly").grid(
            row=0, column=1, padx=5
        )
        ttk.Button(top_frame, text="Choose", command=self.choose_source).grid(row=0, column=2, padx=5)

        ttk.Label(top_frame, text="Destination folder:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.dest_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.dest_var, width=60, state="readonly").grid(
            row=1, column=1, padx=5, pady=(5, 0)
        )
        ttk.Button(top_frame, text="Choose", command=self.choose_destination).grid(
            row=1, column=2, padx=5, pady=(5, 0)
        )

        middle_frame = ttk.Frame(self.root, padding=10)
        middle_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            middle_frame,
            columns=("name", "action", "date", "filepath"),
            show="headings",
            selectmode="browse",
            height=20,
        )
        self.tree.heading("name", text="File")
        self.tree.heading("action", text="Action")
        self.tree.heading("date", text="Date")
        self.tree.column("filepath", width=0, stretch=False)
        self.tree.column("name", width=280)
        self.tree.column("action", width=80, anchor=tk.CENTER)
        self.tree.column("date", width=100, anchor=tk.CENTER)
        self.tree["displaycolumns"] = ("name", "action", "date")
        self.tree.bind("<<TreeviewSelect>>", self.show_preview)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(middle_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        right_panel = ttk.Frame(middle_frame, padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.preview_label = ttk.Label(right_panel, text="Select a photo to preview", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        action_frame = ttk.Frame(right_panel, padding=(0, 10))
        action_frame.pack(fill=tk.X)
        ttk.Button(action_frame, text="Copy", command=lambda: self.set_action("Copy")).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(action_frame, text="Skip", command=lambda: self.set_action("Skip")).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(action_frame, text="Delete", command=lambda: self.set_action("Delete")).pack(
            side=tk.LEFT, padx=5
        )

        self.status_var = tk.StringVar(value="Choose a source folder to get started")
        ttk.Label(self.root, textvariable=self.status_var, padding=10).pack(fill=tk.X)

        run_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        run_frame.pack(fill=tk.X)
        ttk.Button(run_frame, text="Process files", command=self.process_files).pack(side=tk.RIGHT)

    def _set_status(self, text: str) -> None:
        self.root.after(0, lambda: self.status_var.set(text))

    def _notify_error(self, title: str, message: str) -> None:
        self.root.after(0, lambda: messagebox.showerror(title, message))

    def choose_source(self) -> None:
        selected = filedialog.askdirectory(title="Select source folder")
        if not selected:
            return
        self.source_dir = Path(selected)
        self.source_var.set(str(self.source_dir))
        self.load_photos()

    def choose_destination(self) -> None:
        selected = filedialog.askdirectory(title="Select destination folder")
        if not selected:
            return
        self.destination_dir = Path(selected)
        self.dest_var.set(str(self.destination_dir))

    def load_photos(self) -> None:
        if not self.source_dir:
            return
        self.photos.clear()
        self.tree.delete(*self.tree.get_children())

        for entry in sorted(self.source_dir.iterdir()):
            if not entry.is_file() or entry.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            date = self._get_date_taken(entry)
            photo = PhotoItem(path=entry, date_taken=date)
            item_id = self.tree.insert("", tk.END, values=(photo.name, photo.action, photo.date_label, str(photo.path)))
            photo.item_id = item_id
            self.photos.append(photo)

        count = len(self.photos)
        if count:
            self._set_status(f"Loaded {count} photo(s). Select one to preview and choose an action.")
        else:
            self._set_status("No supported images found in the selected folder.")
            self.preview_label.configure(text="Select a photo to preview", image="")
        self.preview_cache.clear()

    def _get_date_taken(self, path: Path) -> datetime:
        try:
            with Image.open(path) as img:
                exif = img.getexif()
                if exif:
                    # Prefer DateTimeOriginal, fall back to DateTime
                    for tag_name in ("DateTimeOriginal", "DateTime"):
                        tag = next((k for k, v in ExifTags.TAGS.items() if v == tag_name), None)
                        if tag and tag in exif:
                            return datetime.strptime(exif.get(tag), "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
        stat = path.stat()
        return datetime.fromtimestamp(stat.st_mtime)

    def show_preview(self, event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        photo = next((p for p in self.photos if p.item_id == item_id), None)
        if not photo:
            return

        cached = self.preview_cache.get(item_id)
        if cached:
            self.preview_label.configure(image=cached, text="")
            return

        try:
            with Image.open(photo.path) as img:
                img.thumbnail((600, 400))
                photo_img = ImageTk.PhotoImage(img)
                self.preview_cache[item_id] = photo_img
                self.preview_label.configure(image=photo_img, text="")
        except Exception as exc:
            self.preview_label.configure(text=f"Unable to preview image: {exc}", image="")

    def set_action(self, action: str) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Select a photo first.")
            return
        item_id = selection[0]
        for photo in self.photos:
            if photo.item_id == item_id:
                photo.action = action
                self.tree.set(item_id, "action", action)
                break

    def process_files(self) -> None:
        if not self.destination_dir:
            messagebox.showwarning("Destination missing", "Choose a destination folder first.")
            return
        if not self.photos:
            messagebox.showinfo("Nothing to do", "Load photos before processing.")
            return

        if any(p.action == "Delete" for p in self.photos):
            if not messagebox.askyesno(
                "Confirm delete",
                "You chose to delete some files from the source folder. This cannot be undone. Continue?",
            ):
                return

        self._set_status("Processing photos...")
        threading.Thread(target=self._process_worker, daemon=True).start()

    def _process_worker(self) -> None:
        copied = skipped = deleted = 0
        for photo in self.photos:
            if photo.action == "Skip":
                skipped += 1
                continue
            if photo.action == "Delete":
                try:
                    photo.path.unlink()
                    deleted += 1
                except Exception:
                    self._notify_error("Delete failed", f"Could not delete {photo.path}")
                continue

            date_folder = self.destination_dir / photo.date_label  # type: ignore[arg-type]
            date_folder.mkdir(parents=True, exist_ok=True)
            destination_file = date_folder / photo.name

            try:
                shutil.copy2(photo.path, destination_file)
                copied += 1
            except Exception:
                self._notify_error("Copy failed", f"Could not copy {photo.name}")

        self._set_status(f"Done. Copied: {copied}, Skipped: {skipped}, Deleted: {deleted}.")


def main() -> None:
    root = tk.Tk()
    app = PhotoOrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
