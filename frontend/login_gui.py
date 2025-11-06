# login_gui.py
import os, json, sys
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox
from backend.auth import do_login
from backend.license import check_license
from frontend.main_gui import MainAppWindow

NAVY_BG = "#0b1930"

class LoginWindow:
    def __init__(self, root: tb.Window):
        self.root = root
        self.root.title("Husky - Login")

        # icono
        try:
            self.root.iconbitmap(r"C:\Users\SamuelPCx\Desktop\Husky\icon.ico")
        except Exception:
            pass

        self.root.geometry("320x240")
        self.root.resizable(False, False)
        self.center_window()

        # ====== estilos ======
        # le decimos al style del root que cree un frame oscuro azul
        style = self.root.style
        style.configure("Navy.TFrame", background=NAVY_BG)
        style.configure("Navy.TLabel", background=NAVY_BG, foreground="white")
        # (los Entry siguen con el estilo del tema, está bien)

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

        # Email label
        email_label = tb.Label(container, text="Email:", style="Navy.TLabel", anchor=W)
        email_label.pack(fill=X, pady=(0, 5))

        self.email_entry = tb.Entry(container, width=30)
        self.email_entry.pack(fill=X, pady=(0, 8))
        self.email_entry.focus()
        if self.saved_email:
            self.email_entry.insert(0, self.saved_email)

        # Password
        pass_label = tb.Label(container, text="Password:", style="Navy.TLabel", anchor=W)
        pass_label.pack(fill=X, pady=(0, 5))

        self.pass_entry = tb.Entry(container, show="*", width=30)
        self.pass_entry.pack(fill=X, pady=(0, 8))
        self.pass_entry.bind("<Return>", lambda e: self.login())

        # Remember email
        self.remember_email_var = tb.BooleanVar(value=self.remember_email)
        tb.Checkbutton(
            container,
            text="Recordar email",
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

        # también podemos poner el bg del root para que no se vea blanco fuera del frame
        self.root.configure(background=NAVY_BG)

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
        w = 320
        h = 240
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
                # en vez de destroy → ocultamos
                self.root.withdraw()
                self.show_main_app(user_email, license_info["exp_date"])
        except ValueError as e:
            messagebox.showerror("Error de Login", str(e))

    def show_main_app(self, user_email, exp_date):
        # usamos la MISMA app, solo abrimos una ventana hija
        main_win = tb.Toplevel(self.root)   # <-- NO crees otro Window/Tk
        main_win.title("Husky Pro")
        MainAppWindow(main_win, user_email, exp_date)
        # NO mainloop aquí, ya hay uno corriendo en el root


def main():
    # usamos un tema real (darkly) y encima pintamos el fondo azul marino
    root = tb.Window(themename="darkly")
    LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
