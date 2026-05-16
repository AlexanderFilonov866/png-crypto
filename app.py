from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from png_crypto import embed_message, extract_message

ROOT = Path(__file__).resolve().parent
DEFAULT_NOISE_DIR = ROOT / "карты шумов"
DEFAULT_IMAGES_DIR = ROOT / "png 1024x1024"


def _list_noise_maps() -> list[Path]:
    if not DEFAULT_NOISE_DIR.is_dir():
        return []
    return sorted(DEFAULT_NOISE_DIR.glob("*.png"))


class PngCryptoApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PNG Crypto — стеганография по карте шума")
        self.minsize(640, 520)
        self.geometry("720x580")

        self.cover_path = tk.StringVar()
        self.stego_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.noise_path = tk.StringVar()
        self.password = tk.StringVar()
        self.status = tk.StringVar(value="Готово")

        self._build_ui()
        self._init_defaults()

    def _init_defaults(self) -> None:
        maps = _list_noise_maps()
        if maps:
            self.noise_path.set(str(maps[0]))
        images = sorted(DEFAULT_IMAGES_DIR.glob("*.png")) if DEFAULT_IMAGES_DIR.is_dir() else []
        if images:
            self.cover_path.set(str(images[0]))

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 4}
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            outer,
            text="Сообщение прячется в младших битах RGB. Порядок пикселей задаёт карта шума.",
            wraplength=680,
        ).pack(anchor=tk.W, pady=(0, 8))

        nb = ttk.Notebook(outer)
        nb.pack(fill=tk.BOTH, expand=True)
        enc = ttk.Frame(nb, padding=8)
        dec = ttk.Frame(nb, padding=8)
        nb.add(enc, text="Зашифровать")
        nb.add(dec, text="Расшифровать")

        self._build_encrypt_tab(enc, pad)
        self._build_decrypt_tab(dec, pad)

        status_frame = ttk.Frame(outer)
        status_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(status_frame, textvariable=self.status, foreground="#444").pack(anchor=tk.W)

    def _noise_row(self, parent: ttk.Frame, pad: dict) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, **pad)
        ttk.Label(row, text="Карта шума", width=14).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.noise_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(row, text="…", width=3, command=self._pick_noise).pack(side=tk.LEFT)

        maps = _list_noise_maps()
        if len(maps) >= 2:
            quick = ttk.Frame(parent)
            quick.pack(fill=tk.X, padx=10, pady=(0, 4))
            ttk.Label(quick, text="", width=14).pack(side=tk.LEFT)
            for p in maps:
                ttk.Button(
                    quick,
                    text=p.name,
                    command=lambda path=p: self.noise_path.set(str(path)),
                ).pack(side=tk.LEFT, padx=2)

    def _file_row(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        command,
        pad: dict,
    ) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, **pad)
        ttk.Label(row, text=label, width=14).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=variable).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(row, text="…", width=3, command=command).pack(side=tk.LEFT)

    def _password_row(self, parent: ttk.Frame, pad: dict) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, **pad)
        ttk.Label(row, text="Пароль", width=14).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.password, show="•").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=4
        )
        ttk.Label(row, text="(необязательно)", foreground="#666").pack(side=tk.LEFT)

    def _build_encrypt_tab(self, parent: ttk.Frame, pad: dict) -> None:
        self._file_row(parent, "Картинка", self.cover_path, self._pick_cover, pad)
        self._noise_row(parent, pad)
        self._file_row(parent, "Сохранить как", self.output_path, self._pick_output, pad)
        self._password_row(parent, pad)

        ttk.Label(parent, text="Сообщение").pack(anchor=tk.W, padx=10, pady=(8, 0))
        self.message_in = tk.Text(parent, height=10, wrap=tk.WORD, font=("Segoe UI", 10))
        self.message_in.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        ttk.Button(parent, text="Встроить сообщение", command=self._do_encrypt).pack(
            anchor=tk.E, padx=10, pady=8
        )

    def _build_decrypt_tab(self, parent: ttk.Frame, pad: dict) -> None:
        self._file_row(parent, "PNG с данными", self.stego_path, self._pick_stego, pad)
        self._noise_row(parent, pad)
        self._password_row(parent, pad)

        ttk.Label(parent, text="Расшифрованное сообщение").pack(anchor=tk.W, padx=10, pady=(8, 0))
        self.message_out = tk.Text(parent, height=12, wrap=tk.WORD, font=("Segoe UI", 10))
        self.message_out.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        ttk.Button(parent, text="Извлечь сообщение", command=self._do_decrypt).pack(
            anchor=tk.E, padx=10, pady=8
        )

    def _pick_cover(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите картинку",
            initialdir=DEFAULT_IMAGES_DIR if DEFAULT_IMAGES_DIR.is_dir() else ROOT,
            filetypes=[("PNG", "*.png"), ("Все файлы", "*.*")],
        )
        if path:
            self.cover_path.set(path)
            if not self.output_path.get():
                p = Path(path)
                self.output_path.set(str(p.with_name(p.stem + "_secret.png")))

    def _pick_stego(self) -> None:
        path = filedialog.askopenfilename(
            title="PNG со скрытым сообщением",
            initialdir=ROOT,
            filetypes=[("PNG", "*.png"), ("Все файлы", "*.*")],
        )
        if path:
            self.stego_path.set(path)

    def _pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Сохранить результат",
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
        )
        if path:
            self.output_path.set(path)

    def _pick_noise(self) -> None:
        path = filedialog.askopenfilename(
            title="Карта шума",
            initialdir=DEFAULT_NOISE_DIR if DEFAULT_NOISE_DIR.is_dir() else ROOT,
            filetypes=[("PNG", "*.png")],
        )
        if path:
            self.noise_path.set(path)

    def _password_value(self) -> str | None:
        p = self.password.get().strip()
        return p if p else None

    def _do_encrypt(self) -> None:
        cover = self.cover_path.get().strip()
        noise = self.noise_path.get().strip()
        out = self.output_path.get().strip()
        text = self.message_in.get("1.0", tk.END).strip()

        if not all([cover, noise, out, text]):
            messagebox.showwarning("Не хватает данных", "Заполните картинку, шум, путь и текст.")
            return
        try:
            info = embed_message(cover, noise, text, out, self._password_value())
            self.status.set(
                f"Готово: {info['bytes_embedded']} байт, "
                f"занято {info['bits_used']}/{info['capacity_bits']} бит LSB"
            )
            messagebox.showinfo("Успех", f"Сохранено:\n{out}")
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))
            self.status.set("Ошибка при шифровании")

    def _do_decrypt(self) -> None:
        stego = self.stego_path.get().strip()
        noise = self.noise_path.get().strip()
        if not stego or not noise:
            messagebox.showwarning("Не хватает данных", "Укажите PNG и карту шума.")
            return
        try:
            text = extract_message(stego, noise, self._password_value())
            self.message_out.delete("1.0", tk.END)
            self.message_out.insert("1.0", text)
            self.status.set(f"Извлечено {len(text)} символов")
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))
            self.status.set("Ошибка при расшифровке")


def main() -> None:
    app = PngCryptoApp()
    app.mainloop()


if __name__ == "__main__":
    main()
