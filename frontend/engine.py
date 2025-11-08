# frontend/engine.py
#
# Cavebot básico con MOVIMIENTO por ROUTE + ROUTE_ACTIONS.
# - Usa imágenes frontend/marcas/<wp_name>.png
# - Soporta acciones básicas: none, ignore, wait:X, rope, shovel, stairs,
#   arrow_up/down/left/right, lure, zoom.
# - Sin combate, sin loot, sin GOTO/tab avanzado (todavía).
# - HOME: start / stop (hotkey global)
# - END: pause / resume (hotkey global)
# - La GUI llama start_engine/stop_engine y lee get_status().

import threading
import time
from typing import List, Tuple, Optional
from pathlib import Path

import pyautogui as pg
import keyboard

# ==== IMPORTS OPCIONALES DE ACCIONES (functions) ====
try:
    from frontend.functions.function_rope import do_rope
    from frontend.functions.function_shovel import do_shovel
    from frontend.functions.function_stairs import do_stairs
    from frontend.functions.function_move_arrow import do_move_arrow
    from frontend.functions.function_zoom import do_zoom_click
except Exception:
    do_rope = do_shovel = do_stairs = do_move_arrow = do_zoom_click = None
    print("[engine] Advertencia: algunas funciones de ROUTE_ACTIONS no están disponibles (frontend/functions).")

# ==================== CONFIGURACIÓN ====================

# Coordenada donde debe quedar centrado el punto del player en el minimapa
PLAYER_CENTER_MINIMAP: Tuple[int, int] = (1807, 82)

# Centro aproximado del personaje en la pantalla (para rope/shovel/stairs, etc.)
PLAYER_CENTER_SCREEN: Tuple[int, int] = (862, 453)

# Prefijos del título de ventana Tibia
TARGET_WINDOW_PREFIXES = ("Tibia -", "Tibia")

# Ruta base del módulo (frontend/)
BASE_DIR = Path(__file__).resolve().parent
MARCAS_DIR = BASE_DIR / "marcas"

# Ruta de waypoints
# Cada nombre corresponde a frontend/marcas/<nombre>.png
ROUTE: List[str] = [
    "wp11",
    "wp12",
    "wp13",
    "wp14",
]

# Acciones por waypoint (paralelo a ROUTE)
# Acciones soportadas:
#   - "none" / ""       → sin acción extra
#   - "ignore"          → solo log
#   - "wait:X"          → espera X segundos extra al llegar
#   - "rope"            → usa HK_ROPE en PLAYER_CENTER_SCREEN
#   - "shovel"          → usa HK_SHOVEL en PLAYER_CENTER_SCREEN
#   - "stairs"          → right-click stairs (function_stairs)
#   - "arrow_up/down/left/right" → mueve con flechas (function_move_arrow)
#   - "lure"            → patrón especial de movimiento (click → correr → ESC → volver)
#   - "zoom"            → clic de zoom usando do_zoom_click
#   - "click_left_north" → clic de zoom usando do_zoom_click
#   - "click_left_south" → clic de zoom usando do_zoom_click
#   - "click_left_east" → clic de zoom usando do_zoom_click
#   - "click_left_west" → clic de zoom usando do_zoom_click

#   - "click_left_north_west" → clic de zoom usando do_zoom_click
#   - "click_left_north_east" → clic de zoom usando do_zoom_click
#   - "click_left_east" → clic de zoom usando do_zoom_click
#   - "click_left_west" → clic de zoom usando do_zoom_click

ROUTE_ACTIONS: List[str] = [
    "none",
    "none",
    "none",
    "none",
]

# Región de búsqueda alrededor del minimapa (en píxeles)
SEARCH_HALF_SIZE = 60

# Parámetros de búsqueda / movimiento
CONFIDENCE = 0.87              # confianza para locateCenterOnScreen
MAX_TRIES_PER_WP = 50          # intentos máximos cuando el WP SÍ es visible

SLEEP_AFTER_CLICK = 0.5        # espera tras hacer click en el WP
CENTER_TOLERANCE_PX = 5        # tolerancia para considerar "centrado"

# Tiempos de flujo de ruta
# Espera DESPUÉS de llegar correctamente a un WP (quieto en ese WP)
WAIT_AFTER_ARRIVAL_S = 0.5

# Espera ANTES de empezar a buscar / ir al siguiente WP
WAIT_BEFORE_NEXT_WP_S = 0

# Timings globales
LOOP_SLEEP_S = 0.01
NOT_ACTIVE_SLEEP = 0.25

# ==== Hotkeys / config para acciones específicas ====

# Rope
HK_ROPE = "f10"
ROPE_ATTEMPTS = 1
ROPE_CAST_DELAY = 1.0
ROPE_CLICK_DELAY = 1.0

# Shovel
HK_SHOVEL = "f11"
SHOVEL_ATTEMPTS = 1
SHOVEL_CAST_DELAY = 1.0
SHOVEL_CLICK_DELAY = 1.0

# Stairs
STAIRS_POST_RIGHT_CLICK_SLEEP = 1.0

# Flechas
MOVE_ARROW_DELAY = 0.25  # delay tras mover con flecha

# Lure
LURE_PAUSE_KEY = "esc"
LURE_PAUSE_SEC = 0.6
LURE_RESUME_SEC = 0.5
LURE_CENTER_TOLERANCE_PX = 4  # suele ser un poco más estricto

# Zoom
ZOOM_RECT_X1Y1X2Y2 = (1863, 72, 1891, 119)  # CONFIGURA esto en tu perfil
ZOOM_CONFIDENCE = 0.99
ZOOM_CLICK_DELAY = 0.5

# pyautogui settings
pg.FAILSAFE = False
pg.PAUSE = 0.0

# ==================== ESTADO ENGINE ====================

_engine_running_event = threading.Event()
_engine_thread: Optional[threading.Thread] = None
_engine_lock = threading.Lock()

# pausa (END)
_pause_event = threading.Event()

# stop_event para funciones externas (rope/shovel/etc.)
_action_stop_event = threading.Event()

# estado legible para GUI/HUD
_status_lock = threading.Lock()
_engine_status: str = "stopped"   # "stopped" | "running" | "paused"


# ==================== HELPERS ESTADO ====================

def _set_status(new_status: str):
    global _engine_status
    with _status_lock:
        _engine_status = new_status


def get_status() -> str:
    """Devuelve 'running', 'paused' o 'stopped' para la GUI/HUD."""
    with _status_lock:
        return _engine_status


def is_running() -> bool:
    """True si el engine está activo."""
    return _engine_running_event.is_set()


def is_paused() -> bool:
    return _pause_event.is_set()


# ==================== HELPERS TIBIA / IMÁGENES ====================

def _is_tibia_active() -> bool:
    """True si la ventana activa parece ser Tibia."""
    try:
        title = pg.getActiveWindowTitle()
    except Exception:
        return False

    if not isinstance(title, str) or not title:
        return False

    return any(title.startswith(pref) for pref in TARGET_WINDOW_PREFIXES)


def _region_from_center(cx: int, cy: int, half: int) -> Tuple[int, int, int, int]:
    """Devuelve región (x, y, w, h) centrada en (cx, cy)."""
    return (cx - half, cy - half, half * 2, half * 2)


def _find_center(img_path: str,
                 region: Tuple[int, int, int, int],
                 confidence: float):
    """locateCenterOnScreen con manejo silencioso de errores."""
    try:
        return pg.locateCenterOnScreen(img_path,
                                       region=region,
                                       confidence=confidence)
    except Exception:
        return None


def _is_centered(pt,
                 center: Tuple[int, int],
                 tol_px: int) -> bool:
    """True si el punto detectado está dentro de la tolerancia del centro esperado."""
    return (
        abs(pt.x - center[0]) <= tol_px and
        abs(pt.y - center[1]) <= tol_px
    )


def _click_point(pt) -> None:
    """Click suave en el punto indicado."""
    try:
        pg.moveTo(pt.x, pt.y, duration=0.05)
        pg.click()
    except Exception as e:
        print(f"[Cavebot] Error al clickear WP: {e}")


# ==================== HELPERS ROUTE_ACTIONS ====================

def _get_action_for_index(index: int) -> str:
    """Devuelve la acción para el WP dado, o 'none' si no hay."""
    if 0 <= index < len(ROUTE_ACTIONS):
        return (ROUTE_ACTIONS[index] or "").strip()
    return "none"


def _perform_action(action: str, wp_name: str):
    """
    Ejecuta la acción declarada en ROUTE_ACTIONS para un WP.
    Se llama SOLO cuando se llegó correctamente al WP.
    'lure' se maneja en el movimiento, aquí solo se loguea.
    """
    a = (action or "").strip().lower()
    if not a or a == "none":
        return

    # ignore → solo log
    if a == "ignore":
        print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION=ignore (sin acción).")
        return

    # lure → ya se aplicó el patrón especial en el movimiento
    if a == "lure":
        print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION=lure (movimiento ya ejecutado).")
        return

    # wait:X → espera adicional
    if a.startswith("wait:"):
        try:
            secs_str = a.split(":", 1)[1].strip()
            secs = float(secs_str)
            if secs > 0:
                print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION=wait → esperando {secs:.2f}s extra.")
                t_end = time.time() + secs
                while time.time() < t_end and _engine_running_event.is_set() and not is_paused():
                    time.sleep(0.05)
            else:
                print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION=wait con valor <=0, ignorado.")
        except Exception:
            print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION=wait malformado ('{a}').")
        return

    # rope
    if a == "rope":
        if do_rope is None:
            print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION=rope pero function_rope no está disponible.")
            return
        try:
            print(f"[Cavebot]  '{wp_name}': Ejecutando rope.")
            do_rope(
                HK_ROPE,
                ROPE_ATTEMPTS,
                ROPE_CAST_DELAY,
                ROPE_CLICK_DELAY,
                PLAYER_CENTER_SCREEN,
                _is_tibia_active,
                is_paused,
                _action_stop_event,
            )
        except Exception as e:
            print(f"[Cavebot]  '{wp_name}': Error en rope: {e}")
        return

    # shovel
    if a == "shovel":
        if do_shovel is None:
            print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION=shovel pero function_shovel no está disponible.")
            return
        try:
            print(f"[Cavebot]  '{wp_name}': Ejecutando shovel.")
            do_shovel(
                HK_SHOVEL,
                SHOVEL_ATTEMPTS,
                SHOVEL_CAST_DELAY,
                SHOVEL_CLICK_DELAY,
                PLAYER_CENTER_SCREEN,
                _is_tibia_active,
                is_paused,
                _action_stop_event,
            )
        except Exception as e:
            print(f"[Cavebot]  '{wp_name}': Error en shovel: {e}")
        return

    # stairs
    if a == "stairs":
        if do_stairs is None:
            print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION=stairs pero function_stairs no está disponible.")
            return
        try:
            print(f"[Cavebot]  '{wp_name}': Ejecutando stairs.")
            do_stairs(
                PLAYER_CENTER_SCREEN,
                STAIRS_POST_RIGHT_CLICK_SLEEP,
                _is_tibia_active,
                is_paused,
                _action_stop_event,
            )
        except Exception as e:
            print(f"[Cavebot]  '{wp_name}': Error en stairs: {e}")
        return

    # arrow_* (mover con flechas)
    if a in ("arrow_up", "arrow_down", "arrow_left", "arrow_right"):
        if do_move_arrow is None:
            print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION={a} pero function_move_arrow no está disponible.")
            return
        try:
            print(f"[Cavebot]  '{wp_name}': Ejecutando {a}.")
            do_move_arrow(
                a,
                MOVE_ARROW_DELAY,
                _is_tibia_active,
                is_paused,
                _action_stop_event,
            )
        except Exception as e:
            print(f"[Cavebot]  '{wp_name}': Error en {a}: {e}")
        return

    # zoom
    if a == "zoom":
        if do_zoom_click is None:
            print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION=zoom pero function_zoom no está disponible.")
            return
        try:
            target_img_path = str(MARCAS_DIR / f"{wp_name}.png")
            print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION=zoom → buscando en región ZOOM_RECT.")
            ok = do_zoom_click(
                target_img_path=target_img_path,
                region_rect_x1y1x2y2=ZOOM_RECT_X1Y1X2Y2,
                confidence=ZOOM_CONFIDENCE,
                click_delay_s=ZOOM_CLICK_DELAY,
            )
            if ok:
                print(f"[Cavebot]  '{wp_name}': Zoom OK.")
            else:
                print(f"[Cavebot]  '{wp_name}': Zoom no encontrado/ejecutado.")
        except Exception as e:
            print(f"[Cavebot]  '{wp_name}': Error en zoom: {e}")
        return

    print(f"[Cavebot]  '{wp_name}': ROUTE_ACTION='{a}' definido pero no implementado en esta versión básica.")


# ==================== LOOP PRINCIPAL ====================

def _engine_loop():
    print("[engine] Cavebot movement started.")
    _set_status("running")

    if not ROUTE:
        print("[engine] ROUTE vacío. Configura tus wp en frontend/engine.py.")
        _engine_running_event.clear()
        _set_status("stopped")
        return

    # Normalizar ROUTE_ACTIONS al largo de ROUTE
    global ROUTE_ACTIONS
    if len(ROUTE_ACTIONS) < len(ROUTE):
        ROUTE_ACTIONS = list(ROUTE_ACTIONS) + ["none"] * (len(ROUTE) - len(ROUTE_ACTIONS))

    search_region = _region_from_center(
        PLAYER_CENTER_MINIMAP[0],
        PLAYER_CENTER_MINIMAP[1],
        SEARCH_HALF_SIZE
    )
    region_center = PLAYER_CENTER_MINIMAP

    wp_index = 0

    while _engine_running_event.is_set():
        # Pausa (END)
        if _pause_event.is_set():
            _set_status("paused")
            time.sleep(0.05)
            continue
        else:
            _set_status("running")

        # Verificar ventana activa Tibia
        if not _is_tibia_active():
            time.sleep(NOT_ACTIVE_SLEEP)
            continue

        # Por si modifican ROUTE en runtime
        if not ROUTE:
            print("[Cavebot] ROUTE quedó vacío en runtime. Deteniendo.")
            break

        if wp_index >= len(ROUTE):
            wp_index = 0

        wp_name = str(ROUTE[wp_index]).strip()
        if not wp_name:
            print(f"[Cavebot] WP vacío en índice {wp_index}, saltando.")
            wp_index = (wp_index + 1) % len(ROUTE)
            time.sleep(LOOP_SLEEP_S)
            continue

        action = _get_action_for_index(wp_index)
        img_path = str(MARCAS_DIR / f"{wp_name}.png")
        print(f"[Cavebot] → WP {wp_index+1}/{len(ROUTE)}: '{wp_name}' (accion='{action or 'none'}') ({img_path})")

        arrived = False
        saw_any = False  # True si al menos una vez vimos la marca para este WP

        for attempt in range(1, MAX_TRIES_PER_WP + 1):
            if not _engine_running_event.is_set():
                break

            # Respeto a la pausa en medio del intento
            if _pause_event.is_set():
                while _engine_running_event.is_set() and _pause_event.is_set():
                    _set_status("paused")
                    time.sleep(0.05)
                if not _engine_running_event.is_set():
                    break

            if not _is_tibia_active():
                time.sleep(NOT_ACTIVE_SLEEP)
                continue

            pt = _find_center(img_path, search_region, CONFIDENCE)

            # Caso: no se ve la marca
            if pt is None:
                if not saw_any:
                    # Nunca se vio: skip inmediato
                    print(f"[Cavebot]  '{wp_name}': intento {attempt} → no visible, SKIP inmediato al siguiente WP.")
                    break
                else:
                    # Ya la habíamos visto y ahora la perdimos:
                    # regla simple: no seguimos spameando, skip rápido.
                    print(f"[Cavebot]  '{wp_name}': perdió visión tras haberla detectado → SKIP al siguiente WP.")
                    break

            # Marca visible por primera vez
            if not saw_any:
                saw_any = True
                print(f"[Cavebot]  '{wp_name}': marca detectada, iniciando ajuste de centrado.")

            # ---- Movimiento según acción ----
            if (action or "").strip().lower() == "lure":
                # Patrón lure
                print(
                    f"[Cavebot]  '{wp_name}': (lure) intento {attempt}/{MAX_TRIES_PER_WP} → "
                    f"click, esperar {LURE_PAUSE_SEC:.2f}s, ESC, esperar {LURE_RESUME_SEC:.2f}s."
                )
                _click_point(pt)
                time.sleep(LURE_PAUSE_SEC)
                try:
                    keyboard.press_and_release(LURE_PAUSE_KEY)
                except Exception:
                    pass
                time.sleep(LURE_RESUME_SEC)

                check = _find_center(img_path, search_region, CONFIDENCE)
                tol = LURE_CENTER_TOLERANCE_PX
                if check and _is_centered(check, region_center, tol):
                    print(
                        f"[Cavebot]  '{wp_name}': centrado OK (lure) en intento "
                        f"{attempt}/{MAX_TRIES_PER_WP} (±{tol}px)."
                    )
                    arrived = True
                    break
                else:
                    print(
                        f"[Cavebot]  '{wp_name}': aún no centrado (lure) en intento "
                        f"{attempt}/{MAX_TRIES_PER_WP}, reintentando..."
                    )
                    time.sleep(LOOP_SLEEP_S)
                    continue

            # ---- Movimiento normal ----
            print(f"[Cavebot]  '{wp_name}': intento {attempt}/{MAX_TRIES_PER_WP} → probando movimiento.")
            _click_point(pt)
            time.sleep(SLEEP_AFTER_CLICK)

            # Verificar centrado
            check = _find_center(img_path, search_region, CONFIDENCE)
            if check and _is_centered(check, region_center, CENTER_TOLERANCE_PX):
                print(
                    f"[Cavebot]  '{wp_name}': centrado OK en intento "
                    f"{attempt}/{MAX_TRIES_PER_WP} (±{CENTER_TOLERANCE_PX}px)."
                )
                arrived = True
                break
            else:
                print(
                    f"[Cavebot]  '{wp_name}': aún no centrado en intento "
                    f"{attempt}/{MAX_TRIES_PER_WP}, reintentando..."
                )
                time.sleep(LOOP_SLEEP_S)

        if not _engine_running_event.is_set():
            break

        # Resultado final para este WP
        if arrived:
            if WAIT_AFTER_ARRIVAL_S > 0:
                print(
                    f"[Cavebot]  '{wp_name}': llegada confirmada, "
                    f"esperando {WAIT_AFTER_ARRIVAL_S:.2f}s después de llegar."
                )
                t_end = time.time() + WAIT_AFTER_ARRIVAL_S
                while time.time() < t_end and _engine_running_event.is_set() and not is_paused():
                    time.sleep(0.05)

            # Ejecutar ROUTE_ACTION solo si se llegó correctamente
            _perform_action(action, wp_name)

        else:
            if not saw_any:
                print(f"[Cavebot]  '{wp_name}': confirmado SKIP por no encontrar marca.")
            else:
                print(
                    f"[Cavebot]  '{wp_name}': sin centrado o visión perdida "
                    f"→ SKIP al siguiente WP."
                )

        # Avanzar al siguiente WP (cíclico)
        wp_index = (wp_index + 1) % len(ROUTE)

        # Pausa antes del siguiente WP
        if WAIT_BEFORE_NEXT_WP_S > 0:
            print(
                f"[Cavebot] Esperando {WAIT_BEFORE_NEXT_WP_S:.2f}s "
                f"antes de procesar el siguiente WP."
            )
            t_end = time.time() + WAIT_BEFORE_NEXT_WP_S
            while time.time() < t_end and _engine_running_event.is_set() and not is_paused():
                time.sleep(0.05)
        else:
            time.sleep(LOOP_SLEEP_S)

    print("[engine] Cavebot movement stopped.")
    _engine_running_event.clear()
    _pause_event.clear()
    _action_stop_event.set()
    _set_status("stopped")


# ==================== API PÚBLICA ====================

def start_engine():
    """Inicia el engine de cavebot si no está corriendo."""
    global _engine_thread
    with _engine_lock:
        if _engine_running_event.is_set():
            return
        _engine_running_event.set()
        _pause_event.clear()
        _action_stop_event.clear()
        _set_status("running")
        _engine_thread = threading.Thread(
            target=_engine_loop,
            name="HuskyCavebotEngine",
            daemon=True,
        )
        _engine_thread.start()


def stop_engine():
    """Detiene el engine si está corriendo."""
    with _engine_lock:
        if not _engine_running_event.is_set():
            return
        _engine_running_event.clear()
        _pause_event.clear()
        _action_stop_event.set()
    # _engine_loop pondrá status="stopped" al salir.


def pause_engine():
    """Pone el engine en pausa (si está corriendo)."""
    if _engine_running_event.is_set():
        _pause_event.set()
        _set_status("paused")
        print("[engine] Paused.")


def resume_engine():
    """Quita la pausa (si estaba en pausa)."""
    if _engine_running_event.is_set() and _pause_event.is_set():
        _pause_event.clear()
        _set_status("running")
        print("[engine] Resumed.")


# ==================== HOTKEYS GLOBALES ====================

def _hotkey_home():
    if is_running():
        print("[hotkey] HOME → stop_engine()")
        stop_engine()
    else:
        print("[hotkey] HOME → start_engine()")
        start_engine()


def _hotkey_end():
    if not is_running():
        return
    if is_paused():
        print("[hotkey] END → resume_engine()")
        resume_engine()
    else:
        print("[hotkey] END → pause_engine()")
        pause_engine()


try:
    keyboard.add_hotkey("home", _hotkey_home, suppress=False)
    keyboard.add_hotkey("end", _hotkey_end, suppress=False)
    print("[engine] Hotkeys: HOME=start/stop, END=pause/resume registrados.")
except Exception as e:
    print(f"[engine] Advertencia: no se pudieron registrar hotkeys globales: {e}")
