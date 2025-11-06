# login_gui.py
import os, json, sys
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from backend.auth import do_login
from backend.license import check_license
from frontend.main_gui import MainAppWindow

ICON_PATH = r"C:\Users\SamuelPCx\Desktop\Husky\icon.ico"

NAVY_BG = "#0b1930"


class LoginWindow:
    def __init__(self, root: tb.Window):
        self.root = root
        self.root.title("Husky - Login")

        # icono
        try:
            self.root.iconbitmap(ICON_PATH)
        except Exception:
            pass

        self.root.geometry("320x240")
        self.root.resizable(False, False)
        self.center_window()

        # ====== estilos ======
        style = self.root.style
        style.configure("Navy.TFrame", background=NAVY_BG)
        style.configure("Navy.TLabel", background=NAVY_BG, foreground="white")

        # resolver base_path
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
        else:
            base_path = "."
        self.config_path = os.path.join(base_path, "login_data.json")

        self.load_saved_data()

        # ----- contenedor principal -----
        container = tb.Frame(self.root, padding=15, style="Navy.TFrame")
        container.pack(fill=BOTH, expand=YES)

        # Email
        tb.Label(container, text="Email:", style="Navy.TLabel", anchor=W).pack(fill=X, pady=(0, 5))
        self.email_entry = tb.Entry(container, width=30)
        self.email_entry.pack(fill=X, pady=(0, 8))
        self.email_entry.focus()
        if self.saved_email:
            self.email_entry.insert(0, self.saved_email)

        # Password
        tb.Label(container, text="Password:", style="Navy.TLabel", anchor=W).pack(fill=X, pady=(0, 5))
        self.pass_entry = tb.Entry(container, show="*", width=30)
        self.pass_entry.pack(fill=X, pady=(0, 8))
        self.pass_entry.bind("<Return>", lambda e: self.login())

        # Remember email
        self.remember_email_var = tb.BooleanVar(value=self.remember_email)
        tb.Checkbutton(
            container,
            text="Remember email",
            variable=self.remember_email_var,
            bootstyle="round-toggle",
        ).pack(anchor=W, pady=(0, 10))

        # Botón
        tb.Button(
            container,
            text="Log in",
            bootstyle=PRIMARY,
            command=self.login,
            width=30,
        ).pack(pady=(0, 5))

        # fondo
        self.root.configure(background=NAVY_BG)

    # ----------------- dialogs -----------------
    def show_error_dialog(self, title: str, message: str):
        dlg = tb.Toplevel(self.root)
        dlg.title(title)
        try:
            dlg.iconbitmap(ICON_PATH)
        except Exception:
            pass

        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        frame = tb.Frame(dlg, padding=15)
        frame.pack(fill=BOTH, expand=YES)

        tb.Label(frame, text=title, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        tb.Label(frame, text=message, wraplength=280, justify="left").pack(anchor="w", pady=(0, 12))

        tb.Button(frame, text="OK", bootstyle=DANGER, command=dlg.destroy).pack(anchor="e")

        # centrar sobre el parent
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 160
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 60
        dlg.geometry(f"320x120+{x}+{y}")

    # ------------- helpers -------------
    def load_saved_data(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    self.saved_email = data.get("email", "")
                    self.remember_email = data.get("remember_email", False)
            else:
                self.saved_email = ""
                self.remember_email = False
        except Exception:
            self.saved_email = ""
            self.remember_email = False

    def save_login_data(self):
        data = {
            "email": self.email_entry.get().strip() if self.remember_email_var.get() else "",
            "remember_email": self.remember_email_var.get(),
        }
        try:
            with open(self.config_path, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def center_window(self):
        self.root.update_idletasks()
        w, h = 320, 240
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def login(self):
        email = self.email_entry.get().strip()
        password = self.pass_entry.get()
        self.save_login_data()

        try:
            user = do_login(email, password)
            user_email = user["email"]
            uid = user["uid"]

            license_info = check_license(user_email, uid)
            if license_info["valid"]:
                self.root.withdraw()
                self.show_main_app(user_email, license_info["exp_date"])
        except ValueError as e:
            self.show_error_dialog("Login Error", str(e))

    def show_main_app(self, user_email, exp_date):
        main_win = tb.Toplevel(self.root)
        main_win.title("Husky Pro")
        MainAppWindow(main_win, user_email, exp_date)


def main():
    root = tb.Window(themename="darkly")
    LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
