from src.runtime import NativaBuiltinError

from . import graphics


def draw_particles(particles, color, ui=False):
    if not isinstance(particles, list):
        raise NativaBuiltinError("lista de partículas inválida", "TypeError")
    r, g, b, a = graphics.color_tuple(color)
    for particle in particles:
        x, y, _vx, _vy, age, life, size = particle
        fade = max(0.0, 1.0 - age / life) if life > 0 else 0.0
        alpha = int(a * fade)
        if alpha > 0:
            graphics.draw_circ(x, y, size, 0, [r, g, b, alpha], ui)


def exports(interp):
    return {"draw_particles": draw_particles}
