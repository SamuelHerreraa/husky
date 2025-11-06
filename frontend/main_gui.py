import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timezone


class MainAppWindow:
    def __init__(self, root, user_email, exp_date):
        self.root = root
        self.root.title("Husky Pro")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        self.center_window()

        label = tk.Label(root, text="husky", font=("Arial", 24, "bold"), fg="blue")
        label.pack(expand=True, pady=50)

        info_frame = tk.Frame(root, bg="white", height=30)
        info_frame.pack(side=tk.BOTTOM, fill=tk.X)
        info_frame.pack_propagate(False)

        user_label = tk.Label(
            info_frame,
            text=f"User: {user_email}",
            font=("Arial", 9),
            fg="gray",
            bg="white",
        )
        user_label.place(relx=0.0, anchor="w", x=10, y=15)

        self.expire_label = tk.Label(
            info_frame, text="", font=("Arial", 9), fg="red", bg="white"
        )
        self.expire_label.place(relx=1.0, anchor="e", x=-10, y=15)

        # guardamos la fecha ya normalizada
        self.exp_date = self._ensure_utc(exp_date)
        self.update_timer()

    def _ensure_utc(self, dt):
        """Recibe un datetime que viene de Firestore o del backend y lo asegura en UTC."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - 200
        y = (self.root.winfo_screenheight() // 2) - 150
        self.root.geometry(f"400x300+{x}+{y}")

    def update_timer(self):
        # ahora actual es UTC
        now = datetime.now(timezone.utc)
        exp = self._ensure_utc(self.exp_date)

        if exp is None:
            self.expire_label.config(text="Expire time: N/A")
            return

        delta = exp - now
        if delta.total_seconds() <= 0:
            self.expire_label.config(text="Expire time: Expirado")
            messagebox.showerror("Expirado", "Licencia vencida. Cierra y renueva.")
            self.root.quit()
            return

        total_seconds = int(delta.total_seconds())
        days = total_seconds // 86400
        remainder = total_seconds % 86400
        hours, rem = divmod(remainder, 3600)
        minutes, seconds = divmod(rem, 60)
        self.expire_label.config(
            text=f"Expire time: {days}d {hours}h {minutes}m {seconds}s"
        )
        self.root.after(1000, self.update_timer)
