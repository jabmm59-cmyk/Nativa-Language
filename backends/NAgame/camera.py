import math

from . import check_number, state


def to_screen(x, y):
    cam = state.camera
    dx = x - cam["x"]
    dy = y - cam["y"]
    angle = math.radians(-cam["rot"])
    cos, sin = math.cos(angle), math.sin(angle)
    rx = dx * cos - dy * sin
    ry = dx * sin + dy * cos
    zoom = cam["zoom"]
    return state.width / 2 + rx * zoom, state.height / 2 + ry * zoom


def zoom_factor():
    return state.camera["zoom"]


def rotation():
    return state.camera["rot"]


def reset_camera():
    state.camera.update(
        {"x": state.width / 2, "y": state.height / 2, "zoom": 1.0, "rot": 0.0}
    )


def exports(interp):
    def get_state():
        return dict(state.camera)

    def set_pos(x, y):
        check_number("x", x)
        check_number("y", y)
        state.camera["x"] = float(x)
        state.camera["y"] = float(y)

    def set_zoom(value):
        check_number("zoom", value)
        if value <= 0:
            from src.runtime import NativaBuiltinError

            raise NativaBuiltinError("zoom deve ser maior que zero", "ValueError")
        state.camera["zoom"] = float(value)

    def set_rot(value):
        check_number("rotação", value)
        state.camera["rot"] = float(value)

    def world_to_screen(x, y):
        check_number("x", x)
        check_number("y", y)
        sx, sy = to_screen(x, y)
        return [sx, sy]

    return {
        "get_state": get_state, "set_pos": set_pos, "set_zoom": set_zoom,
        "set_rot": set_rot, "world_to_screen": world_to_screen, "reset": reset_camera,
    }
