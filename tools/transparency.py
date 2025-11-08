# tools/transparency.py
#
# Utilidades para hacer transparente la ventana de Tibia en Windows
# y detectar si ya está en modo transparente.
#
# Requiere Windows. Usa ctypes (no depende de pywin32).

import ctypes
from ctypes import wintypes

USER32 = ctypes.windll.user32
GDI32 = ctypes.windll.gdi32

# Constantes de Win32
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
LWA_ALPHA         = 0x00000002

# Tipos
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

# -------- helpers internos --------

def _get_window_text(hwnd) -> str:
    length = USER32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    USER32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value or ""


def _matches_patterns(title: str, patterns) -> bool:
    if not title:
        return False
    for p in patterns:
        if title.startswith(p):
            return True
    return False


def _enum_windows():
    hwnds = []

    @EnumWindowsProc
    def _callback(hwnd, lParam):
        # Filtrar ventanas invisibles?
        # if not USER32.IsWindowVisible(hwnd):
        #     return True
        hwnds.append(hwnd)
        return True

    USER32.EnumWindows(_callback, 0)
    return hwnds


def _find_tibia_windows(patterns):
    result = []
    for hwnd in _enum_windows():
        title = _get_window_text(hwnd)
        if _matches_patterns(title, patterns):
            result.append(hwnd)
    return result


def _get_exstyle(hwnd):
    return USER32.GetWindowLongW(hwnd, GWL_EXSTYLE)


def _set_exstyle(hwnd, exstyle):
    USER32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)


def _set_layered_alpha(hwnd, alpha_byte: int):
    # alpha_byte: 0-255
    USER32.SetLayeredWindowAttributes(hwnd, 0, alpha_byte, LWA_ALPHA)


# -------- API pública --------

def make_transparent(patterns=("Tibia -", "Tibia"), alpha=1.0) -> bool:
    """
    Activa WS_EX_LAYERED y ajusta alpha en ventanas Tibia que coincidan con patterns.
    alpha:
      - Si 0.0 < alpha <= 1.0 → se usa como factor (alpha*255).
      - Si >1 → se asume valor directo 0-255.
    Devuelve True si al menos una ventana fue modificada con éxito.
    """
    try:
        hwnds = _find_tibia_windows(patterns)
        if not hwnds:
            print("[transparency] No se encontró ventana Tibia para aplicar transparencia.")
            return False

        if alpha <= 0:
            alpha_byte = 0
        elif alpha <= 1.0:
            alpha_byte = int(alpha * 255)
        else:
            alpha_byte = int(alpha)
        alpha_byte = max(0, min(1, alpha_byte))

        any_ok = False
        for hwnd in hwnds:
            exs = _get_exstyle(hwnd)
            if not (exs & WS_EX_LAYERED):
                _set_exstyle(hwnd, exs | WS_EX_LAYERED)
            _set_layered_alpha(hwnd, alpha_byte)
            any_ok = True

        if any_ok:
            print(f"[transparency] Aplicada transparencia a Tibia (alpha={alpha_byte}).")
        return any_ok
    except Exception as e:
        print(f"[transparency] Error en make_transparent: {e}")
        return False


def restore_window(patterns=("Tibia -", "Tibia")):
    """
    Quita WS_EX_LAYERED de las ventanas Tibia coincidentes.
    """
    try:
        hwnds = _find_tibia_windows(patterns)
        if not hwnds:
            print("[transparency] No se encontró ventana Tibia para restaurar.")
            return

        for hwnd in hwnds:
            exs = _get_exstyle(hwnd)
            if exs & WS_EX_LAYERED:
                _set_exstyle(hwnd, exs & ~WS_EX_LAYERED)

        print("[transparency] Restaurado estilo normal de Tibia.")
    except Exception as e:
        print(f"[transparency] Error en restore_window: {e}")


def is_transparent(patterns=("Tibia -", "Tibia")) -> bool:
    """
    Devuelve True si AL MENOS UNA ventana Tibia tiene WS_EX_LAYERED activo,
    independientemente de si está en primer plano o no.
    """
    try:
        hwnds = _find_tibia_windows(patterns)
        if not hwnds:
            return False

        for hwnd in hwnds:
            exs = _get_exstyle(hwnd)
            if exs & WS_EX_LAYERED:
                return True

        return False
    except Exception as e:
        print(f"[transparency] Error en is_transparent: {e}")
        return False
