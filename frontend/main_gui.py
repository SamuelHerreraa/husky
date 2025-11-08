# frontend/main_gui.py

import os
from datetime import datetime, timezone

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import Toplevel

import pyautogui as pg  # para detectar ventana activa Tibia

from tools import transparency  # helper de transparencia
from frontend import engine     # ← nuestro motor separado

# ============ CONFIG ============

# Mostrar u ocultar HUD flotante
HUD_ENABLED = True

# Prefijos para detectar ventana de Tibia (igual que en engine)
TIBIA_TITLE_PREFIXES = ("Tibia -", "Tibia")


class MainAppWindow:
    def __init__(self, root: tb.Toplevel, user_email: str, exp_date):
        self.root = root
        self.user_email = user_email

        if exp_date.tzinfo is None:
            exp_date = exp_date.replace(tzinfo=timezone.utc)
        self.exp_date = exp_date

        self.root.title("Husky Pro")
        self.root.geometry("1000x600")
        self.root.minsize(900, 520)

        # icono
        try:
            self.root.iconbitmap(r"C:\Users\SamuelPCx\Desktop\Husky\icon.ico")
        except Exception:
            pass

        # estado transparencia (se ajustará luego con _init_transparency_state)
        self.transparency_on = False

        # referencia HUD (si está habilitado)
        self.hud = None
        self.hud_label = None

        # layout base
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        # topbar
        top = tb.Frame(self.root, bootstyle="dark")
        top.grid(row=0, column=0, columnspan=2, sticky="nsew")
        top.columnconfigure(0, weight=1)
        tb.Label(top, text="Husky", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, padx=15, pady=10, sticky="w"
        )
        tb.Label(top, text=f"{user_email}", font=("Segoe UI", 9)).grid(
            row=0, column=1, padx=15, pady=10, sticky="e"
        )

        # sidebar
        sidebar = tb.Frame(self.root, bootstyle="secondary", width=180)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        tb.Label(sidebar, text="Tools", font=("Segoe UI", 11, "bold")).pack(
            fill=X, padx=10, pady=(10, 5)
        )

        tb.Button(
            sidebar,
            text="Dashboard",
            bootstyle=LINK,
            command=lambda: self.show_view("dashboard"),
        ).pack(fill=X, padx=10, pady=2)

        tb.Button(
            sidebar,
            text="Licenses info",
            bootstyle=LINK,
            command=lambda: self.show_view("licenses"),
        ).pack(fill=X, padx=10, pady=2)

        tb.Button(
            sidebar,
            text="Settings",
            bootstyle=LINK,
            command=lambda: self.show_view("settings"),
        ).pack(fill=X, padx=10, pady=2)

        # botón START / STOP / PAUSED
        self.btn_start = tb.Button(
            sidebar,
            text="Start",
            bootstyle=PRIMARY,
            command=self.on_start_clicked,
        )
        self.btn_start.pack(fill=X, padx=10, pady=(18, 2))

        # botón transparencia
        self.btn_transparency = tb.Button(
            sidebar,
            text="Transparency (Tibia): OFF",
            bootstyle=SECONDARY,
            command=self.toggle_transparency,
        )
        self.btn_transparency.pack(fill=X, padx=10, pady=(10, 2))

        # área de contenido
        self.content = tb.Frame(self.root)
        self.content.grid(row=1, column=1, sticky="nsew")
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        # bottom
        bottom = tb.Frame(self.root, bootstyle="light")
        bottom.grid(row=2, column=0, columnspan=2, sticky="nsew")
        bottom.columnconfigure(0, weight=1)
        self.expire_label = tb.Label(bottom, text="", font=("Segoe UI", 9))
        self.expire_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # vistas + timers + estados
        self.show_view("dashboard")
        self.update_timer()
        self._refresh_start_button_ui()

        # sincronizar botón de transparencia con estado real
        self._init_transparency_state()

        # crear HUD flotante (si está habilitado)
        if HUD_ENABLED:
            self._create_hud()
            self._update_hud()  # empieza el ciclo de actualización

    # ============ NAV =============
    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def show_view(self, name: str):
        self.clear_content()
        if name == "dashboard":
            self._view_dashboard()
        elif name == "licenses":
            self._view_licenses()
        elif name == "settings":
            self._view_settings()
        else:
            self._view_dashboard()

    # ============ VISTAS ============
    def _view_dashboard(self):
        dash = tb.Frame(self.content, padding=10)
        dash.pack(fill=BOTH, expand=YES)
        tb.Label(dash, text="Dashboard", font=("Segoe UI", 13, "bold")).pack(
            anchor="w", pady=(0, 10)
        )
        tb.Label(dash, text="Here goes Husky tools...", font=("Segoe UI", 10)).pack(
            anchor="w"
        )

    def _view_licenses(self):
        frame = tb.Frame(self.content, padding=10)
        frame.pack(fill=BOTH, expand=YES)

        tb.Label(frame, text="License information", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(0, 10)
        )
        tb.Label(frame, text=f"User: {self.user_email}", font=("Segoe UI", 10)).pack(anchor="w")
        tb.Label(
            frame,
            text=f"Expiration (UTC): {self.exp_date.strftime('%Y-%m-%d %H:%M:%S')}",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 10))

    def _view_settings(self):
        frame = tb.Frame(self.content, padding=10)
        frame.pack(fill=BOTH, expand=YES)
        tb.Label(frame, text="Settings", font=("Segoe UI", 12, "bold")).pack(anchor="w")

    # ============ transparencia ============
    def _init_transparency_state(self):
        """
        Detecta si Tibia ya está en modo transparente al abrir Husky
        y sincroniza el botón en consecuencia.
        """
        patterns = ("Tibia -", "Tibia")
        detected = False

        try:
            if hasattr(transparency, "is_transparent"):
                detected = bool(transparency.is_transparent(patterns))
        except Exception as e:
            print(f"[gui] Transparency init check error: {e}")

        self.transparency_on = bool(detected)
        if self.transparency_on:
            self.btn_transparency.config(
                text="Transparency (Tibia): ON",
                bootstyle=SUCCESS,
            )
        else:
            self.btn_transparency.config(
                text="Transparency (Tibia): OFF",
                bootstyle=SECONDARY,
            )

    def toggle_transparency(self):
        patterns = ("Tibia -", "Tibia")
        if not self.transparency_on:
            ok = transparency.make_transparent(patterns, alpha=1)
            if ok:
                self.transparency_on = True
                self.btn_transparency.config(text="Transparency (Tibia): ON", bootstyle=SUCCESS)
            else:
                self.transparency_on = False
                self.btn_transparency.config(text="Transparency (Tibia): OFF", bootstyle=SECONDARY)
        else:
            transparency.restore_window(patterns)
            self.transparency_on = False
            self.btn_transparency.config(text="Transparency (Tibia): OFF", bootstyle=SECONDARY)

    # ============ HUD FLOTANTE ============

    def _create_hud(self):
        """Crea la ventana flotante del HUD (pero no fuerza su visibilidad)."""
        self.hud = Toplevel(self.root)
        self.hud.overrideredirect(True)          # sin bordes
        self.hud.attributes("-topmost", True)    # siempre arriba cuando esté visible
        self.hud.attributes("-alpha", 0.9)       # ligera transparencia visual
        self.hud.configure(bg="#101010")

        # posición inicial (puedes ajustar)
        self.hud.geometry("+100+100")

        # contenido
        self.hud_label = tb.Label(
            self.hud,
            text="Husky: STOPPED",
            font=("Segoe UI", 9, "bold"),
            bootstyle="inverse-dark",
        )
        self.hud_label.pack(padx=8, pady=4)

        # empezar oculto; lo mostramos solo si Tibia está en foreground
        self.hud.withdraw()

    def _get_engine_status(self) -> str:
        """Obtiene el estado lógico del engine."""
        status = "stopped"
        if hasattr(engine, "get_status"):
            try:
                status = engine.get_status()
            except Exception:
                # fallback si algo falla
                status = "running" if engine.is_running() else "stopped"
        else:
            status = "running" if engine.is_running() else "stopped"
        return status

    def _get_tibia_active(self) -> bool:
        """True si Tibia es la ventana activa (para mostrar HUD solo en Tibia)."""
        try:
            title = pg.getActiveWindowTitle()
        except Exception:
            return False

        if not isinstance(title, str) or not title:
            return False

        return any(title.startswith(p) for p in TIBIA_TITLE_PREFIXES)

    def _update_hud(self):
        """Actualiza texto/color/visibilidad del HUD periódicamente."""
        if not HUD_ENABLED or self.hud is None or self.hud_label is None:
            return

        # Estado del engine
        status = self._get_engine_status()

        if status == "running":
            text = "Husky: RUNNING"
            fg = "#00ff55"
        elif status == "paused":
            text = "Husky: PAUSED"
            fg = "#ffcc00"
        else:
            text = "Husky: STOPPED"
            fg = "#ff5555"

        # Actualizar label
        try:
            self.hud_label.config(text=text, foreground=fg)
        except Exception:
            pass

        # Mostrar solo cuando Tibia está en primer plano
        tibia_active = self._get_tibia_active()

        if tibia_active:
            # mostrar HUD si está oculto
            if not self.hud.winfo_viewable():
                self.hud.deiconify()
            # asegurar topmost
            try:
                self.hud.attributes("-topmost", True)
            except Exception:
                pass
        else:
            # ocultar si Tibia no está activa
            if self.hud.winfo_viewable():
                self.hud.withdraw()

        # volver a llamarse
        self.root.after(200, self._update_hud)

    # ============ start/stop engine ============

    def on_start_clicked(self):
        if engine.is_running():
            print("[gui] Stop requested.")
            engine.stop_engine()
        else:
            print("[gui] Start requested.")
            engine.start_engine()

        self._refresh_start_button_ui()

    def _refresh_start_button_ui(self):
        # Usamos get_status() del engine si existe
        status = self._get_engine_status()

        if status == "running":
            # Cavebot activo
            self.btn_start.config(text="Stop", bootstyle=DANGER)
        elif status == "paused":
            # Pausa (END)
            self.btn_start.config(text="Paused", bootstyle=WARNING)
        else:
            # Detenido
            self.btn_start.config(text="Start", bootstyle=PRIMARY)

    # ============ timer ============

    def update_timer(self):
        now = datetime.now(timezone.utc)
        delta = self.exp_date - now

        if delta.total_seconds() <= 0:
            self.expire_label.config(text="License expired")
            # Seguimos refrescando el botón y HUD por si el engine cambia.
            self._refresh_start_button_ui()
            if HUD_ENABLED:
                self._update_hud()
            self.root.after(1000, self.update_timer)
            return

        total_seconds = int(delta.total_seconds())
        days = total_seconds // 86400
        remainder = total_seconds % 86400
        hours, rem = divmod(remainder, 3600)
        minutes, seconds = divmod(rem, 60)

        self.expire_label.config(
            text=f"License time left: {days}d {hours}h {minutes}m {seconds}s"
        )

        # Sincronizar botón y HUD con estado real del engine
        self._refresh_start_button_ui()

        # (El HUD ya se actualiza con su propio after cada 200ms)

        self.root.after(1000, self.update_timer)
