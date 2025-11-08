"""
function_move_arrow.py — Acción de mover con flechas
La idea es igual a function_stairs.py pero en vez de click derecho,
mandamos la tecla de flecha que nos pidan.
"""
from typing import Callable
import time
import keyboard


def do_move_arrow(
    arrow_key: str,
    press_sleep_s: float,
    is_active: Callable[[], bool],
    is_paused: Callable[[], bool],
    stop_event,
) -> None:
    """
    arrow_key: "up", "down", "left", "right"
    press_sleep_s: cuánto esperar después de mandarla
    """
    # normalizamos por si vienen "arrow_down"
    arrow_key = arrow_key.strip().lower()
    if arrow_key.startswith("arrow_"):
        arrow_key = arrow_key.replace("arrow_", "", 1)

    while True:
        if stop_event.is_set():
            break
        if is_paused():
            time.sleep(0.05)
            continue
        if not is_active():
            time.sleep(0.25)
            continue

        # enviamos la flecha
        keyboard.press_and_release(arrow_key)
        time.sleep(max(0.0, float(press_sleep_s)))
        print(f"[move_arrow] flecha '{arrow_key}' enviada + espera")
        break
