import io
import os
import sys
import tempfile
import unittest
from textwrap import dedent

from backends.NAgame import state
from impbuild import Loader
from impbuild.loader import DEFAULT_ROOT
from src.errors import NativaRuntimeError
from src.main import run_source
from tests.fake_pygame import KEY_CODES, make_fake_pygame


def na(code):
    return dedent(code).lstrip("\n")


class NAgameCase(unittest.TestCase):
    def setUp(self):
        self.previous = sys.modules.get("pygame")
        self.pg = make_fake_pygame()
        sys.modules["pygame"] = self.pg
        state.reset()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.loader = Loader(
            root=DEFAULT_ROOT,
            search_dirs=[os.path.join(DEFAULT_ROOT, "libraries")],
            build_dir=os.path.join(self.tmp.name, "build"),
        )

    def tearDown(self):
        state.reset()
        if self.previous is None:
            sys.modules.pop("pygame", None)
        else:
            sys.modules["pygame"] = self.previous

    def run_na(self, source):
        out = io.StringIO()
        run_source("NA imp NAgame\n" + na(source), out=out, loader=self.loader)
        return out.getvalue()

    def file(self, name, data=b"x"):
        path = os.path.join(self.tmp.name, name)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def calls(self, name):
        return [c for c in self.pg.screen.calls if c[0] == name]


class TestWindowAndLoop(NAgameCase):
    def test_window_title_background(self):
        self.run_na('NAgame.st_title("Meu Jogo")\nNAgame.window(800, 600)\nNAgame.back(10, 20, 30)')
        self.assertEqual(self.pg.screen.size, (800, 600))
        self.assertEqual(self.pg.captions[-1], "Meu Jogo")
        self.assertIn(("fill", (10, 20, 30)), self.pg.screen.calls)

    def test_invalid_window_size(self):
        for bad in ("0, 600", "800, -1", "'a', 5"):
            with self.assertRaises(NativaRuntimeError):
                self.run_na(f"NAgame.window({bad})")

    def test_functions_require_window(self):
        code = na("""
            try: (
                NAgame.updt()
            )
            xcept RuntimeError as e: (
                shw "sem janela"
            )
        """)
        self.assertEqual(self.run_na(code), "sem janela\n")

    def test_updt_flips_and_clears_to_background(self):
        self.run_na("NAgame.window(100, 100)\nNAgame.back(1, 2, 3)\nNAgame.updt()")
        self.assertEqual(self.pg.flips, 1)
        self.assertEqual(self.pg.screen.calls[-1], ("fill", (1, 2, 3)))

    def test_evn_until_quit(self):
        code = na("""
            NAgame.window(100, 100)
            shw NAgame.evn()
            shw NAgame.evn()
        """)
        out = io.StringIO()
        self.pg.post(self.pg.QUIT)
        run_source("NA imp NAgame\n" + na("""
            NAgame.window(100, 100)
            shw NAgame.evn()
        """), out=out, loader=self.loader)
        self.assertEqual(out.getvalue(), "False\n")

    def test_game_loop_runs_frames(self):
        code = na("""
            NAgame.window(200, 100)
            frames = 0
            while NAgame.evn(): (
                NAgame.updt()
                NAgame.tof(60)
                frames = frames + 1
                if frames == 3: (
                    NAgame.close()
                )
            )
            shw frames
        """)
        self.assertEqual(self.run_na(code), "3\n")
        self.assertEqual(self.pg.quit_calls, 1)
        self.assertEqual(self.pg.ticks, [60, 60, 60])

    def test_dt_and_clamp(self):
        self.pg.next_ms = 20
        code = "NAgame.window(10, 10)\nshw NAgame.tof(30), NAgame.dt()"
        self.assertEqual(self.run_na(code), "0.02 0.02\n")
        self.pg.next_ms = 900
        self.assertEqual(self.run_na("NAgame.window(10, 10)\nshw NAgame.tof(30)"), "0.1\n")

    def test_gettime(self):
        code = "NAgame.window(10, 10)\nshw NAgame.gettime() >= 0, NAgame.gettime() < 5"
        self.assertEqual(self.run_na(code), "True True\n")

    def test_missing_pygame_is_catchable(self):
        sys.modules["pygame"] = None
        state.reset()
        code = na("""
            try: (
                NAgame.window(10, 10)
            )
            xcept ImportError as e: (
                shw "sem pygame"
            )
        """)
        self.assertEqual(self.run_na(code), "sem pygame\n")


class TestDrawing(NAgameCase):
    def test_rec_returns_shape_and_draws(self):
        out = self.run_na("NAgame.window(200, 200)\nNAgame.clr(255, 0, 0)\nr = NAgame.rec(10, 20, 30, 40)\nshw r.x, r.y, r.width, r.height, r.kind")
        self.assertEqual(out, "10 20 30 40 rec\n")
        self.assertIn(("rect", (255, 0, 0), ((10, 20, 30, 40), 0)), self.calls("rect"))

    def test_rec_border(self):
        self.run_na("NAgame.window(200, 200)\nNAgame.rec(0, 0, 10, 10, 3)")
        self.assertEqual(self.calls("rect")[-1][2][1], 3)

    def test_circ_and_line(self):
        self.run_na("NAgame.window(200, 200)\nNAgame.clr(0, 255, 0)\nNAgame.circ(50, 60, 10)\nNAgame.lne(0, 0, 30, 40, 2)")
        self.assertEqual(self.calls("circle")[-1], ("circle", (0, 255, 0), ((50, 60), 10, 0)))
        self.assertEqual(self.calls("line")[-1], ("line", (0, 255, 0), ((0, 0), (30, 40), 2)))

    def test_color_names_and_validation(self):
        self.run_na('NAgame.window(50, 50)\nNAgame.clr("red")\nNAgame.rec(0, 0, 5, 5)')
        self.assertEqual(self.calls("rect")[-1][1], (220, 40, 40))
        for bad in ("300, 0, 0", '"inexistente"', "10"):
            with self.assertRaises(NativaRuntimeError):
                self.run_na(f"NAgame.window(50, 50)\nNAgame.clr({bad})")

    def test_alpha_uses_blended_layer(self):
        self.run_na("NAgame.window(100, 100)\nNAgame.clr(255, 255, 255, 128)\nNAgame.rec(10, 10, 20, 20)")
        blits = self.calls("blit")
        self.assertEqual(len(blits), 1)
        layer = blits[0][4]
        self.assertEqual(layer.flags, self.pg.SRCALPHA)
        self.assertEqual(layer.calls[0][1], (255, 255, 255, 128))
        self.assertEqual(self.calls("rect"), [])

    def test_text_and_font_size(self):
        out = self.run_na('NAgame.window(200, 100)\nNAgame.fntsz(40)\nt = NAgame.txt("Olá", 5, 6)\nshw t.size, t.width, t.height, t.text')
        self.assertEqual(out, "40 60 40 Olá\n")
        blit = self.calls("blit")[-1]
        self.assertEqual(blit[2], (5, 6))
        self.assertEqual(blit[4].text, "Olá")

    def test_invalid_font_size(self):
        with self.assertRaises(NativaRuntimeError):
            self.run_na("NAgame.window(50, 50)\nNAgame.fntsz(0)")

    def test_draw_redraws_existing_object(self):
        self.run_na("NAgame.window(100, 100)\nr = NAgame.rec(1, 2, 3, 4)\nr.x = 50\nNAgame.draw(r)")
        rects = [c[2][0] for c in self.calls("rect")]
        self.assertEqual(rects, [(1, 2, 3, 4), (50, 2, 3, 4)])


class TestCamera(NAgameCase):
    def test_default_camera_is_identity(self):
        self.run_na("NAgame.window(800, 600)\nNAgame.rec(100, 50, 10, 10)")
        self.assertEqual(self.calls("rect")[-1][2][0], (100, 50, 10, 10))

    def test_campos_shifts_world(self):
        self.run_na("NAgame.window(800, 600)\nNAgame.campos(500, 300)\nNAgame.rec(500, 300, 10, 10)")
        self.assertEqual(self.calls("rect")[-1][2][0], (400, 300, 10, 10))

    def test_zoom_scales_around_view_center(self):
        self.run_na("NAgame.window(800, 600)\nNAgame.camzoom(2)\nNAgame.rec(400, 300, 10, 10)")
        self.assertEqual(self.calls("rect")[-1][2][0], (400, 300, 20, 20))
        self.run_na("NAgame.window(800, 600)\nNAgame.camzoom(2)\nNAgame.circ(410, 300, 5)")
        self.assertEqual(self.calls("circle")[-1][2], ((420, 300), 10, 0))

    def test_rotation_uses_polygon(self):
        self.run_na("NAgame.window(800, 600)\nNAgame.camrot(90)\nNAgame.rec(400, 300, 10, 10)")
        points = self.calls("polygon")[-1][2][0]
        xs = sorted(round(p[0]) for p in points)
        self.assertEqual(len(points), 4)
        self.assertEqual(xs, [400, 400, 410, 410])

    def test_getters_and_validation(self):
        out = self.run_na("NAgame.window(800, 600)\nshw NAgame.campos(), NAgame.camzoom(), NAgame.camrot(), NAgame.cam()['zoom']")
        self.assertEqual(out, "[400.0, 300.0] 1.0 0.0 1.0\n")
        for bad in ("NAgame.camzoom(0)", "NAgame.camzoom(-1)", "NAgame.campos(1)", "NAgame.camzoom('a')"):
            with self.assertRaises(NativaRuntimeError):
                self.run_na(f"NAgame.window(800, 600)\n{bad}")

    def test_ui_drawing_ignores_camera(self):
        self.run_na("NAgame.window(800, 600)\nNAgame.camzoom(3)\nNAgame.campos(0, 0)\nNAgame.panel(10, 10, 100, 50)")
        self.assertEqual(self.calls("rect")[0][2][0], (10, 10, 100, 50))

    def test_camfolw_moves_toward_target(self):
        code = na("""
            NAgame.window(800, 600)
            target = NAgame.rec(1000, 600, 0, 0)
            NAgame.camfolw(target, 0.5)
            for i in rang(30): (
                NAgame.tof(60)
                NAgame.updt()
            )
            p = NAgame.campos()
            shw p[0] > 900, p[1] > 550, p[0] <= 1000
        """)
        self.pg.next_ms = 16
        self.assertEqual(self.run_na(code), "True True True\n")

    def test_camfolw_snap_and_disable(self):
        code = na("""
            NAgame.window(800, 600)
            t = NAgame.rec(100, 100, 0, 0)
            NAgame.camfolw(t, 1)
            NAgame.tof(60)
            NAgame.updt()
            shw NAgame.campos()
            NAgame.camfolw(None)
            t.x = 900
            NAgame.updt()
            shw NAgame.campos()
        """)
        self.assertEqual(self.run_na(code), "[100.0, 100.0]\n[100.0, 100.0]\n")

    def test_camfolw_validates_smooth(self):
        with self.assertRaises(NativaRuntimeError):
            self.run_na("NAgame.window(10, 10)\nNAgame.camfolw(None, 0)")

    def test_folw_moves_follower(self):
        code = na("""
            NAgame.window(800, 600)
            a = NAgame.rec(0, 0, 10, 10)
            b = NAgame.rec(100, 0, 10, 10)
            NAgame.tof(60)
            left = NAgame.folw(a, b, 100)
            shw round(a.x, 2), round(left, 2)
        """)
        self.pg.next_ms = 100
        self.assertEqual(self.run_na(code), "10.0 90.0\n")

    def test_folw_does_not_overshoot(self):
        code = "NAgame.window(10, 10)\na = NAgame.rec(0, 0, 0, 0)\nb = NAgame.rec(5, 0, 0, 0)\nNAgame.tof(60)\nshw NAgame.folw(a, b, 1000000), a.x"
        self.pg.next_ms = 100
        self.assertEqual(self.run_na(code), "0.0 5.0\n")


class TestImages(NAgameCase):
    def test_loadimg_and_shwimg(self):
        path = self.file("a.png")
        out = self.run_na(f'NAgame.window(200, 200)\nimg = NAgame.loadimg("{path}")\nshw img.width, img.height\nNAgame.shwimg(img, 10, 20)')
        self.assertEqual(out, "64 32\n")
        blit = self.calls("blit")[-1]
        self.assertEqual(blit[2], (10, 20))

    def test_missing_image_is_catchable(self):
        code = na("""
            NAgame.window(10, 10)
            try: (
                NAgame.loadimg("nao_existe.png")
            )
            xcept RuntimeError as e: (
                shw "sem imagem"
            )
        """)
        self.assertEqual(self.run_na(code), "sem imagem\n")

    def test_sprite_draw_with_transforms(self):
        path = self.file("a.png")
        code = f"""
            NAgame.window(400, 400)
            s = NAgame.sprt(NAgame.loadimg("{path}"), 100, 100)
            NAgame.rsze(s, 128, 64)
            NAgame.rttae(s, 90)
            NAgame.alp(s, 100)
            NAgame.flp(s)
            NAgame.draw(s)
            shw s.width, s.height, s.angle, s.alpha, s.flipx
        """
        self.assertEqual(self.run_na(code), "128 64 90 100 True\n")
        blit = self.calls("blit")[-1]
        surface = blit[4]
        self.assertEqual(surface.size, (64, 128))
        self.assertEqual(surface.alpha, 100)
        self.assertEqual(blit[2], (132, 68))

    def test_image_transforms_return_new_images(self):
        path = self.file("a.png")
        code = f"""
            NAgame.window(100, 100)
            img = NAgame.loadimg("{path}")
            big = NAgame.rsze(img, 128, 64)
            rot = NAgame.rttae(img, 90)
            faded = NAgame.alp(img, 50)
            flipped = NAgame.flp(img, True, True)
            shw img.width, big.width, big.height, rot.width, rot.height, faded.width, flipped.width
        """
        self.assertEqual(self.run_na(code), "64 128 64 32 64 64 64\n")

    def test_alp_validation(self):
        path = self.file("a.png")
        with self.assertRaises(NativaRuntimeError):
            self.run_na(f'NAgame.window(10, 10)\nNAgame.alp(NAgame.loadimg("{path}"), 300)')

    def test_camera_scales_sprites(self):
        path = self.file("a.png")
        self.run_na(f'NAgame.window(800, 600)\nNAgame.camzoom(2)\nNAgame.sprt(NAgame.loadimg("{path}"), 400, 300)\nNAgame.draw(NAgame.sprt(NAgame.loadimg("{path}"), 400, 300))')
        blit = self.calls("blit")[-1]
        self.assertEqual(blit[4].size, (128, 64))


class TestAnimationAndTimers(NAgameCase):
    def frames(self, count=3):
        path = self.file("f.png")
        return path, f'[{", ".join(f"NAgame.loadimg({chr(34)}{path}{chr(34)})" for _ in range(count))}]'

    def test_animation_advances_and_loops(self):
        _, frames = self.frames(3)
        code = f"""
            NAgame.window(100, 100)
            frames = {frames}
            a = NAgame.anm(frames, 10)
            shw a.index()
            a.update(0.1)
            shw a.index()
            a.update(0.25)
            shw a.index()
            a.update(0.1)
            shw a.index()
        """
        self.assertEqual(self.run_na(code), "0\n1\n0\n1\n")

    def test_animation_without_loop_stops(self):
        _, frames = self.frames(3)
        code = f"NAgame.window(10, 10)\na = NAgame.anm({frames}, 10, False)\na.update(5)\nshw a.index(), a.done"
        self.assertEqual(self.run_na(code), "2 True\n")

    def test_animation_is_updated_by_updt(self):
        _, frames = self.frames(4)
        code = f"""
            NAgame.window(100, 100)
            a = NAgame.anm({frames}, 10)
            for i in rang(7): (
                NAgame.tof(60)
                NAgame.updt()
            )
            shw a.index() >= 1
        """
        self.pg.next_ms = 100
        self.assertEqual(self.run_na(code), "True\n")

    def test_sprite_plays_animation(self):
        path = self.file("f.png")
        code = f"""
            NAgame.window(100, 100)
            frames = [NAgame.loadimg("{path}"), NAgame.rsze(NAgame.loadimg("{path}"), 10, 10)]
            a = NAgame.anm(frames, 1)
            s = NAgame.sprt(frames[0], 0, 0)
            s.play(a)
            a.update(1.0)
            NAgame.draw(s)
            shw s.image.width
        """
        self.assertEqual(self.run_na(code), "10\n")

    def test_spritesheet_slicing(self):
        path = self.file("sheet.png")
        code = f"""
            NAgame.window(100, 100)
            sheet = NAgame.loadimg("{path}")
            a = NAgame.anm(sheet, 10, True, 16, 16)
            shw len(a.frames), a.frames[0].width
        """
        self.assertEqual(self.run_na(code), "8 16\n")

    def test_anm_validation(self):
        path = self.file("f.png")
        for bad in ("[]", "5", f'NAgame.loadimg("{path}")'):
            with self.assertRaises(NativaRuntimeError):
                self.run_na(f"NAgame.window(10, 10)\nNAgame.anm({bad})")

    def test_timer_fires_once(self):
        code = na("""
            NAgame.window(10, 10)
            fired = []
            t = NAgame.tmr(0.05, afction: fired.append(1))
            for i in rang(6): (
                NAgame.tof(60)
                NAgame.updt()
            )
            shw len(fired), t.done
        """)
        self.pg.next_ms = 20
        self.assertEqual(self.run_na(code), "1 True\n")

    def test_timer_repeat_and_cancel(self):
        code = na("""
            NAgame.window(10, 10)
            fired = []
            t = NAgame.tmr(0.05, afction: fired.append(1), True)
            for i in rang(10): (
                NAgame.tof(60)
                NAgame.updt()
            )
            shw len(fired)
            t.cancel()
            for i in rang(10): (
                NAgame.tof(60)
                NAgame.updt()
            )
            shw len(fired)
        """)
        self.pg.next_ms = 50
        self.assertEqual(self.run_na(code), "10\n10\n")

    def test_timer_validation(self):
        with self.assertRaises(NativaRuntimeError):
            self.run_na("NAgame.tmr(0)")


class TestParticles(NAgameCase):
    def test_particles_spawn_move_and_die(self):
        code = na("""
            NA imp random
            random.seed(3)
            NAgame.window(200, 200)
            p = NAgame.prt(100, 100, 10, [255, 100, 0, 255], 100, 0.5, 4, 0)
            shw len(p.particles), p.finished()
            for i in rang(9): (
                NAgame.tof(60)
                NAgame.updt()
            )
            shw len(p.particles) < 10
            for i in rang(30): (
                NAgame.tof(60)
                NAgame.updt()
            )
            shw len(p.particles), p.finished()
        """)
        self.pg.next_ms = 50
        self.assertEqual(self.run_na(code), "10 False\nTrue\n0 True\n")

    def test_particles_draw_with_fade(self):
        code = na("""
            NAgame.window(200, 200)
            p = NAgame.prt(100, 100, 5, [255, 100, 0, 255], 50, 1.0, 3, 0)
            NAgame.tof(60)
            NAgame.updt()
        """)
        self.pg.next_ms = 100
        self.run_na(code)
        layers = [c[4] for c in self.pg.screen.calls if c[0] == "blit"]
        self.assertGreater(len(layers), 0)
        alphas = {layer.calls[0][1][3] for layer in layers}
        self.assertTrue(all(0 < a < 255 for a in alphas))

    def test_prt_default_color_is_current_color(self):
        out = self.run_na("NAgame.window(10, 10)\nNAgame.clr(1, 2, 3)\np = NAgame.prt(0, 0, 1)\nshw p.color")
        self.assertEqual(out, "[1, 2, 3, 255]\n")

    def test_prt_validation(self):
        for bad in ("0, 0, -1", "0, 0, 5, None, 10, 0"):
            with self.assertRaises(NativaRuntimeError):
                self.run_na(f"NAgame.window(10, 10)\nNAgame.prt({bad})")


class TestPhysics(NAgameCase):
    def run_na(self, source):
        return super().run_na("NAgame.window(400, 400)\n" + na(source))

    def test_gravity_and_ground(self):
        code = na("""
            NAgame.window(400, 400)
            NAgame.grnd(300)
            b = NAgame.rec(10, 0, 20, 20)
            for i in rang(200): (
                NAgame.phys(b, 0.016)
            )
            shw round(b.y, 1), b.on_ground, b.vy
        """)
        self.assertEqual(self.run_na(code), "280.0 True 0.0\n")

    def test_grnd_get_and_disable(self):
        out = self.run_na("shw NAgame.grnd()\nNAgame.grnd(50)\nshw NAgame.grnd()\nNAgame.grnd(False)\nshw NAgame.grnd()")
        self.assertEqual(out, "None\n50\nNone\n")

    def test_free_fall_without_ground(self):
        out = self.run_na("b = NAgame.rec(0, 0, 1, 1)\nNAgame.phys(b, 1.0)\nshw b.vy, b.y, NAgame.grv")
        self.assertEqual(out, "980.0 980.0 980.0\n")

    def test_phys_uses_frame_dt_by_default(self):
        self.pg.next_ms = 100
        out = self.run_na("NAgame.window(10, 10)\nb = NAgame.rec(0, 0, 1, 1)\nNAgame.tof(60)\nNAgame.phys(b)\nshw round(b.vy, 1)")
        self.assertEqual(out, "98.0\n")

    def test_bounce(self):
        code = na("""
            b = NAgame.circ(0, 0, 10)
            NAgame.grnd(100)
            NAgame.bounc(b, 0.5)
            NAgame.spd(b, 0, 400)
            b.y = 89
            NAgame.phys(b, 0.01)
            shw b.vy < 0, b.on_ground
        """)
        self.assertEqual(self.run_na(code), "True False\n")

    def test_jump_and_mass(self):
        code = na("""
            NAgame.grnd(100)
            a = NAgame.rec(0, 80, 20, 20)
            b = NAgame.rec(0, 80, 20, 20)
            NAgame.mass(b, 2)
            NAgame.phys(a, 0.01)
            NAgame.phys(b, 0.01)
            shw NAgame.jmp(a, 500), NAgame.jmp(b, 500), a.vy, b.vy
            shw NAgame.jmp(a, 500)
        """)
        self.assertEqual(self.run_na(code), "True True -500.0 -250.0\nFalse\n")

    def test_friction_slows_on_ground(self):
        code = na("""
            NAgame.grnd(100)
            a = NAgame.rec(0, 80, 20, 20)
            NAgame.fric(a, 5)
            NAgame.spd(a, 100, 0)
            NAgame.phys(a, 0.01)
            first = a.vx
            for i in rang(100): (
                NAgame.phys(a, 0.01)
            )
            shw first, a.vx < 1
        """)
        out = self.run_na(code)
        self.assertEqual(out.split()[1], "True")

    def test_acceleration(self):
        out = self.run_na("a = NAgame.rec(0, 0, 1, 1)\na.gravity = 0\nNAgame.acc(a, 10, 0)\nNAgame.phys(a, 2.0)\nshw a.vx, a.x")
        self.assertEqual(out, "20.0 40.0\n")

    def test_accessors(self):
        code = na("""
            a = NAgame.rec(1, 2, 3, 4)
            NAgame.pos(a, 10, 20)
            NAgame.spd(a, 1, 2)
            NAgame.acc(a, 3, 4)
            NAgame.mass(a, 5)
            NAgame.fric(a, 0.5)
            NAgame.bounc(a, 0.25)
            shw NAgame.getpos(a), NAgame.spd(a), NAgame.acc(a), NAgame.mass(a), NAgame.fric(a), NAgame.bounc(a)
        """)
        self.assertEqual(self.run_na(code), "[10, 20] [1, 2] [3, 4] 5 0.5 0.25\n")

    def test_validation(self):
        for bad in ("NAgame.mass(a, 0)", "NAgame.fric(a, -1)", "NAgame.bounc(a, 2)"):
            with self.assertRaises(NativaRuntimeError):
                self.run_na(f"a = NAgame.rec(0, 0, 1, 1)\n{bad}")

    def test_materials(self):
        code = na("""
            a = NAgame.rec(0, 0, 1, 1)
            NAgame.mate(a, "rubber")
            shw a.bounce, a.friction, a.mass
            m = NAgame.mate("ice")
            shw m["friction"]
        """)
        self.assertEqual(self.run_na(code), "0.85 2.0 1.1\n0.1\n")
        with self.assertRaises(NativaRuntimeError):
            self.run_na('NAgame.mate("plasma")')

    def test_collisions_rec_rec(self):
        code = na("""
            a = NAgame.rec(0, 0, 10, 10)
            b = NAgame.rec(5, 5, 10, 10)
            c = NAgame.rec(10, 0, 10, 10)
            d = NAgame.rec(50, 50, 10, 10)
            shw NAgame.colde(a, b), NAgame.colde(a, c), NAgame.tch(a, c), NAgame.tch(a, d)
        """)
        self.assertEqual(self.run_na(code), "True False True False\n")

    def test_collisions_circles_and_mixed(self):
        code = na("""
            c1 = NAgame.circ(0, 0, 5)
            c2 = NAgame.circ(8, 0, 5)
            c3 = NAgame.circ(10, 0, 5)
            r = NAgame.rec(4, -2, 4, 4)
            far = NAgame.rec(100, 100, 5, 5)
            shw NAgame.colde(c1, c2), NAgame.colde(c1, c3), NAgame.tch(c1, c3)
            shw NAgame.colde(c1, r), NAgame.colde(r, c1), NAgame.colde(c1, far)
        """)
        self.assertEqual(self.run_na(code), "True False True\nTrue True False\n")

    def test_collision_works_with_sprites(self):
        path = self.file("a.png")
        code = f"""
            NAgame.window(100, 100)
            s = NAgame.sprt(NAgame.loadimg("{path}"), 0, 0)
            r = NAgame.rec(60, 10, 10, 10)
            shw NAgame.colde(s, r)
        """
        self.assertEqual(self.run_na(code), "True\n")

    def test_ray_hits_nearest(self):
        code = na("""
            near = NAgame.rec(20, -5, 10, 10)
            far = NAgame.rec(60, -5, 10, 10)
            hit = NAgame.ray(0, 0, 100, 0, [far, near])
            shw hit["obj"] is near, hit["x"], hit["y"], hit["distance"]
            shw NAgame.ray(0, 50, 100, 50, [near, far])
        """)
        self.assertEqual(self.run_na(code), "True 20.0 0.0 20.0\nNone\n")

    def test_ray_circle_and_origin_inside(self):
        code = na("""
            c = NAgame.circ(50, 0, 10)
            hit = NAgame.ray(0, 0, 100, 0, [c])
            shw round(hit["x"], 1)
            inside = NAgame.rec(-5, -5, 10, 10)
            shw NAgame.ray(0, 0, 10, 0, [inside])["distance"]
            shw NAgame.ray(0, 0, 10, 0, [NAgame.circ(500, 500, 3)])
        """)
        self.assertEqual(self.run_na(code), "40.0\n0.0\nNone\n")

    def test_ray_diagonal(self):
        code = "r = NAgame.rec(10, 10, 10, 10)\nhit = NAgame.ray(0, 0, 30, 30, [r])\nshw hit['x'], hit['y']"
        self.assertEqual(self.run_na(code), "10.0 10.0\n")


class TestInputAndAudio(NAgameCase):
    def test_keyboard_state(self):
        self.pg.post(self.pg.KEYDOWN, key=KEY_CODES["a"])
        self.pg.post(self.pg.KEYDOWN, key=KEY_CODES["left"])
        code = na("""
            NAgame.window(10, 10)
            NAgame.evn()
            shw NAgame.key("a"), NAgame.key("left"), NAgame.key("d"), NAgame.key("a", True)
            NAgame.evn()
            shw NAgame.key("a"), NAgame.key("a", True)
        """)
        self.assertEqual(self.run_na(code), "True True False True\nTrue False\n")

    def test_key_release_and_aliases(self):
        self.pg.post(self.pg.KEYDOWN, key=KEY_CODES["return"])
        code = na("""
            NAgame.window(10, 10)
            NAgame.evn()
            shw NAgame.key("enter"), NAgame.key("ENTER")
        """)
        self.assertEqual(self.run_na(code), "True True\n")
        self.pg.post(self.pg.KEYUP, key=KEY_CODES["return"])
        out = io.StringIO()
        run_source("NA imp NAgame\nNAgame.evn()\nshw NAgame.key('enter'), NAgame.keyout('enter')", out=out, loader=self.loader)
        self.assertEqual(out.getvalue(), "False True\n")

    def test_key_validation(self):
        for bad in ("5", '""'):
            with self.assertRaises(NativaRuntimeError):
                self.run_na(f"NAgame.window(10, 10)\nNAgame.key({bad})")

    def test_mouse(self):
        self.pg.mouse_pos = (33, 44)
        self.pg.post(self.pg.MOUSEBUTTONDOWN, button=1)
        self.pg.post(self.pg.MOUSEBUTTONUP, button=3)
        code = na("""
            NAgame.window(100, 100)
            NAgame.evn()
            shw NAgame.mse(), NAgame.mseclk(), NAgame.mseclk(3), NAgame.mseout(3), NAgame.mseout()
            NAgame.evn()
            shw NAgame.mseclk()
        """)
        self.assertEqual(self.run_na(code), "[33, 44] True False True False\nFalse\n")

    def test_mouse_button_validation(self):
        with self.assertRaises(NativaRuntimeError):
            self.run_na("NAgame.window(10, 10)\nNAgame.mseclk(9)")

    def test_controller(self):
        out = self.run_na("NAgame.window(10, 10)\nshw NAgame.controllr()")
        self.assertEqual(out, "None\n")
        self.pg.joystick_count = 1
        out = self.run_na("NAgame.window(10, 10)\nc = NAgame.controllr()\nshw c['axes'], c['buttons'], c['index']")
        self.assertEqual(out, "[0.5, -1.0] [False, True, False] 0\n")

    def test_music(self):
        path = self.file("m.ogg")
        code = f"""
            NAgame.loadmsc("{path}")
            NAgame.volmsc(0.5)
            NAgame.playmsc()
            NAgame.pausemsc()
            NAgame.playmsc()
            NAgame.loopmsc()
            NAgame.stopmsc()
        """
        self.run_na(code)
        self.assertEqual(
            self.pg.audio_log,
            [("music_load", path), ("music_volume", 0.5), ("music_play", 0), ("music_pause",),
             ("music_unpause",), ("music_play", -1), ("music_stop",)],
        )

    def test_playmsc_with_file_and_errors(self):
        path = self.file("m.ogg")
        self.run_na(f'NAgame.playmsc("{path}")')
        self.assertEqual(self.pg.audio_log[-2:], [("music_load", path), ("music_play", 0)])
        state.reset()
        with self.assertRaises(NativaRuntimeError):
            self.run_na("NAgame.playmsc()")
        with self.assertRaises(NativaRuntimeError):
            self.run_na('NAgame.loadmsc("nao_existe.ogg")')
        for bad in ("2", "-0.1"):
            with self.assertRaises(NativaRuntimeError):
                self.run_na(f"NAgame.volmsc({bad})")

    def test_sounds_and_sfx_volume(self):
        path = self.file("s.wav")
        code = f"""
            snd = NAgame.loadsnd("{path}")
            NAgame.vlint(50)
            NAgame.playsnd(snd)
            NAgame.playsnd("{path}")
            NAgame.vlint(100)
            NAgame.playsnd(snd)
        """
        self.run_na(code)
        self.assertEqual(
            self.pg.audio_log,
            [("sound", path, 0.5), ("sound", path, 0.5), ("sound", path, 1.0)],
        )
        with self.assertRaises(NativaRuntimeError):
            self.run_na("NAgame.vlint(101)")
        with self.assertRaises(NativaRuntimeError):
            self.run_na('NAgame.loadsnd("nao_existe.wav")')


class TestInterfaceAndScenes(NAgameCase):
    def test_button_click(self):
        self.pg.mouse_pos = (50, 30)
        self.pg.post(self.pg.MOUSEBUTTONDOWN, button=1)
        code = na("""
            NAgame.window(400, 300)
            NAgame.evn()
            shw NAgame.btn("Jogar", 40, 20, 100, 30)
            shw NAgame.btn("Sair", 200, 200, 100, 30)
        """)
        self.assertEqual(self.run_na(code), "True\nFalse\n")
        texts = [c[4].text for c in self.calls("blit") if hasattr(c[4], "text")]
        self.assertEqual(texts, ["Jogar", "Sair"])

    def test_button_callback_and_hover_color(self):
        self.pg.mouse_pos = (50, 30)
        code = na("""
            NAgame.window(400, 300)
            hits = []
            NAgame.evn()
            NAgame.btn("A", 40, 20, 100, 30, afction: hits.append(1))
            shw len(hits)
        """)
        self.assertEqual(self.run_na(code), "0\n")
        self.assertEqual(self.calls("rect")[0][1], (85, 100, 160))
        self.pg.post(self.pg.MOUSEBUTTONDOWN, button=1)
        out = io.StringIO()
        run_source("NA imp NAgame\nNAgame.evn()\nhits = []\nNAgame.btn('A', 40, 20, 100, 30, afction: hits.append(1))\nshw len(hits)", out=out, loader=self.loader)
        self.assertEqual(out.getvalue(), "1\n")

    def test_menu_returns_clicked_index(self):
        self.pg.mouse_pos = (30, 20 + 54 + 5)
        self.pg.post(self.pg.MOUSEBUTTONDOWN, button=1)
        code = na("""
            NAgame.window(400, 400)
            NAgame.evn()
            shw NAgame.menu(["Novo", "Carregar", "Sair"], 10, 20, 200, 44, 10)
        """)
        self.assertEqual(self.run_na(code), "1\n")

    def test_menu_without_click(self):
        out = self.run_na('NAgame.window(400, 400)\nshw NAgame.menu(["a", "b"], 10, 10)')
        self.assertEqual(out, "-1\n")

    def test_panel(self):
        out = self.run_na('NAgame.window(400, 400)\np = NAgame.panel(10, 20, 200, 100, "Status")\nshw p.x, p.width')
        self.assertEqual(out, "10 200\n")
        texts = [c[4].text for c in self.calls("blit") if hasattr(c[4], "text")]
        self.assertEqual(texts, ["Status"])

    def test_scene_switch(self):
        code = na("""
            shw NAgame.scn()
            a = NAgame.scn("menu")
            a.data["x"] = 1
            NAgame.scn("jogo")
            shw NAgame.scn().name
            shw NAgame.scn("menu").data
        """)
        self.assertEqual(self.run_na(code), "None\njogo\n{'x': 1}\n")

    def test_save_and_load_scene(self):
        path = os.path.join(self.tmp.name, "save.json")
        code = f"""
            s = NAgame.scn("fase1")
            s.data["pontos"] = 42
            s.data["itens"] = ["a", "b"]
            NAgame.savscn("{path}")
            s.data = {{}}
            NAgame.scn("outra")
            loaded = NAgame.loadscn("{path}")
            shw loaded.name, loaded.data["pontos"], loaded.data["itens"], NAgame.scn().name
        """
        self.assertEqual(self.run_na(code), "fase1 42 ['a', 'b'] fase1\n")
        self.assertTrue(os.path.isfile(path))

    def test_scene_errors(self):
        with self.assertRaises(NativaRuntimeError):
            self.run_na('NAgame.savscn("x.json")')
        with self.assertRaises(NativaRuntimeError):
            self.run_na('NAgame.loadscn("nao_existe.json")')

    def test_gameover_state_and_overlay(self):
        code = na("""
            NAgame.window(400, 300)
            shw NAgame.gameover(None)
            NAgame.gameover("Perdeu!")
            shw NAgame.gameover(None)
            NAgame.updt()
        """)
        self.assertEqual(self.run_na(code), "False\nTrue\n")
        texts = [c[4].text for c in self.pg.screen.calls if c[0] == "blit" and hasattr(c[4], "text")]
        self.assertEqual(texts, ["Perdeu!"])
        self.assertEqual(self.pg.flips, 1)

    def test_gameover_overlay_is_drawn_before_flip(self):
        seen = []
        original = self.pg.display.flip

        def flip():
            seen.extend(c[4].text for c in self.pg.screen.calls if c[0] == "blit" and hasattr(c[4], "text"))
            original()

        self.pg.display.flip = flip
        self.run_na('NAgame.window(400, 300)\nNAgame.gameover("Fim")\nNAgame.updt()')
        self.assertEqual(seen, ["Fim"])

    def test_restart_resets_runtime_state(self):
        code = na("""
            NAgame.window(400, 300)
            NAgame.gameover()
            fired = []
            NAgame.tmr(0.01, afction: fired.append(1))
            NAgame.camfolw(NAgame.rec(900, 900, 1, 1), 1)
            NAgame.campos(10, 10)
            s = NAgame.scn("x")
            s.data["a"] = 1
            NAgame.restart()
            shw NAgame.gameover(None), NAgame.scn().data, NAgame.campos()
            NAgame.tof(60)
            NAgame.updt()
            shw len(fired), NAgame.campos()
        """)
        self.pg.next_ms = 50
        self.assertEqual(self.run_na(code), "False {} [200.0, 150.0]\n0 [200.0, 150.0]\n")


class TestUtilities(NAgameCase):
    def test_rnd_variants(self):
        code = na("""
            a = NAgame.rnd()
            b = NAgame.rnd(5)
            c = NAgame.rnd(10, 12)
            d = NAgame.rnd(0.5, 1.5)
            e = NAgame.rnd(["x", "y"])
            shw a >= 0 and a < 1, b >= 0 and b < 5, c >= 10 and c <= 12, d >= 0.5 and d <= 1.5, e in ["x", "y"]
        """)
        self.assertEqual(self.run_na(code), "True True True True True\n")

    def test_rnd_invalid(self):
        with self.assertRaises(NativaRuntimeError):
            self.run_na("NAgame.rnd(5, 1)")

    def test_debug_prints_and_returns(self):
        out = self.run_na('v = NAgame.debug("x", 5, [1])\nshw v')
        self.assertEqual(out, "[debug] x 5 [1]\nx\n")
        self.assertEqual(self.run_na("shw NAgame.debug()"), "[debug] \nNone\n")


class TestSpecNames(NAgameCase):
    SPEC = """
        window st_title close back updt evn tof dt gettime rec circ lne txt fntsz clr draw
        loadimg shwimg sprt rsze rttae alp flp playmsc playsnd pausemsc stopmsc loopmsc volmsc
        vlint loadmsc loadsnd key mse mseclk keyout mseout controllr colde tch mate grv mass
        fric bounc ray grnd phys pos getpos spd acc jmp anm prt tmr cam campos camfolw camzoom
        camrot folw btn panel menu scn loadscn savscn gameover restart rnd debug
    """.split()

    def test_every_name_from_the_spec_is_exported(self):
        missing = []
        for name in self.SPEC:
            out = self.run_na(f"shw hasattr(NAgame, '{name}')")
            if out != "True\n":
                missing.append(name)
        self.assertEqual(missing, [])

    def test_internals_are_not_exported(self):
        self.assertEqual(self.run_na("shw hasattr(NAgame, '_updaters')"), "False\n")
        self.assertEqual(self.run_na("shw hasattr(NAgame, 'native')"), "False\n")


@unittest.skipUnless(
    os.environ.get("NA_REAL_PYGAME") == "1",
    "defina NA_REAL_PYGAME=1 com pygame instalado para executar este teste",
)
class TestRealPygame(unittest.TestCase):
    def test_headless_smoke(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        sys.modules.pop("pygame", None)
        state.reset()
        out = io.StringIO()
        code = na("""
            NA imp NAgame
            NAgame.window(320, 240)
            NAgame.back(0, 0, 40)
            NAgame.clr(255, 255, 255)
            NAgame.rec(10, 10, 50, 50)
            NAgame.circ(100, 100, 20)
            NAgame.txt("ok", 5, 5)
            NAgame.updt()
            NAgame.tof(60)
            NAgame.close()
            shw "ok"
        """)
        run_source(code, out=out)
        self.assertEqual(out.getvalue(), "ok\n")


if __name__ == "__main__":
    unittest.main()
