"""CN Arcade - seven mini-games that demo Computer Networks concepts.

Run:  python3 main.py [--windowed]      (needs: pip install pygame)
Keys: 1-7 pick a game, D demo mode, P pause, S slow mode, F fullscreen, Esc back/quit.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import pygame

from engine import (BLUE, CREAM, GREEN, INK, MID, PINK, PURPLE, W, H, WHITE, YELLOW, Button,
                    Sky, icon, outlined, panel, paragraph, pill, shade, star, text)
from games import GAMES

SCORES = Path(__file__).with_name("scores.json")
SLOW_SPEED = 0.2          # game speed while Slow mode is on (S toggles it)


class App:
    def __init__(self, fullscreen=True):
        pygame.init()
        pygame.display.set_caption("CN Arcade")
        self.fullscreen = fullscreen
        try:
            self.screen = self.set_mode(fullscreen)
        except pygame.error as exc:
            if not fullscreen:
                raise
            print(f"Fullscreen unavailable ({exc}); using a window.", file=sys.stderr)
            self.fullscreen = False
            self.screen = self.set_mode(False)
        self.clock = pygame.time.Clock()
        self.sky = Sky()
        self.scores = self.load()
        self.slow = False
        self.scene = Hub(self)

    @staticmethod
    def set_mode(fullscreen):
        """The game is drawn on a fixed 1100x700 canvas; SCALED fits it to the display."""
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else 0)
        return pygame.display.set_mode((W, H), flags)

    def toggle_fullscreen(self):
        want = not self.fullscreen
        try:
            toggled = pygame.display.toggle_fullscreen() == 0    # 0 = success
        except pygame.error:
            toggled = False
        if toggled:
            self.screen = pygame.display.get_surface()          # smoothest path on macOS
        else:
            try:
                self.screen = self.set_mode(want)               # fallback for other drivers
            except pygame.error as exc:
                print(f"Could not switch display mode ({exc}).", file=sys.stderr)
                return
        self.fullscreen = want

    def load(self):
        try:
            return json.loads(SCORES.read_text())
        except (OSError, ValueError):
            return {}

    def record(self, key, res):
        old = self.scores.get(key, {"best": 0, "stars": 0})
        new = {"best": max(old["best"], res["score"]), "stars": max(old["stars"], res["stars"])}
        self.scores[key] = new
        try:
            SCORES.write_text(json.dumps(self.scores, indent=2))
        except OSError:
            pass
        return res["score"] > old["best"]

    def go(self, scene):
        self.scene = scene

    def frame(self, dt, events):
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_f, pygame.K_F11):
                self.toggle_fullscreen()
                continue
            if e.type == pygame.KEYDOWN and e.key == pygame.K_s:
                self.slow = not self.slow          # works on every screen
                continue
            self.scene.handle(e)
        if self.slow:
            dt *= SLOW_SPEED                       # everything runs on this clock
        self.sky.update(dt)
        self.scene.update(dt)
        self.sky.draw(self.screen)
        self.scene.draw(self.screen)
        if self.slow:
            pill(self.screen, f"SLOW MODE {SLOW_SPEED}x  (S)", (W // 2, 10), YELLOW, 14, anchor="center")

    def run(self):
        while True:
            dt = min(self.clock.tick(60) / 1000, 0.05)
            self.frame(dt, pygame.event.get())
            pygame.display.flip()


# ---------------------------------------------------------------- hub
class Hub:
    def __init__(self, app):
        self.app, self.t = app, 0.0
        self.cards = []
        for i, g in enumerate(GAMES):
            row, col = divmod(i, 4)
            x = 42 + col * 258 + (129 if row == 1 else 0)
            self.cards.append((pygame.Rect(x, 150 + row * 225, 240, 205), g))
        self.full_btn = Button((175, 625, 230, 54), "Fullscreen (F)", BLUE, 20)
        self.demo_btn = Button((435, 625, 230, 54), "Demo mode (D)", PINK, 20, key=pygame.K_d)
        self.quit_btn = Button((695, 625, 230, 54), "Quit (Esc)", WHITE, 20, key=pygame.K_ESCAPE)

    def handle(self, e):
        if self.full_btn.hit(e):
            self.app.toggle_fullscreen()
        elif self.demo_btn.hit(e):
            Demo(self.app).start()
        elif self.quit_btn.hit(e):
            pygame.quit()
            sys.exit()
        elif e.type == pygame.KEYDOWN and pygame.K_1 <= e.key <= pygame.K_7:
            self.app.go(Learn(self.app, GAMES[e.key - pygame.K_1]))
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, g in self.cards:
                if r.collidepoint(e.pos):
                    self.app.go(Learn(self.app, g))

    def update(self, dt):
        self.t += dt

    def draw(self, s):
        outlined(s, "CN ARCADE", (W // 2, 58 + math.sin(self.t * 2) * 4), 64, YELLOW, width=4)
        text(s, "Seven mini-games, one network stack", (W // 2, 108), 20, INK, bold=True, anchor="midtop")
        text(s, "S = slow mode   F = fullscreen", (20, 20), 15, INK, bold=True)
        total = sum(v.get("stars", 0) for v in self.app.scores.values())
        star(s, (985, 52), 18)
        text(s, f"{total} / {3 * len(GAMES)}", (1010, 52), 22, INK, bold=True, anchor="midleft")
        mouse = pygame.mouse.get_pos()
        for i, (r, g) in enumerate(self.cards):
            hover = r.collidepoint(mouse)
            rr = r.move(0, -5 if hover else 0)
            panel(s, rr, shade(g.color, 0.25 if hover else 0.45), radius=22, border=4, shadow=8 if hover else 6)
            pygame.draw.circle(s, WHITE, (rr.x + 26, rr.y + 26), 15)
            pygame.draw.circle(s, INK, (rr.x + 26, rr.y + 26), 15, 2)
            text(s, str(i + 1), (rr.x + 26, rr.y + 26), 16, INK, bold=True, anchor="center")
            icon(s, g.icon, (rr.centerx, rr.y + 62), 1.0, g.color)
            text(s, g.title, (rr.centerx, rr.y + 110), 22, INK, bold=True, anchor="midtop")
            text(s, g.layer.split("·")[-1].strip(), (rr.centerx, rr.y + 138), 14, INK, anchor="midtop")
            sc = self.app.scores.get(g.key, {})
            for k in range(3):
                star(s, (rr.centerx - 34 + k * 34, rr.y + 175), 13, k < sc.get("stars", 0))
        self.full_btn.label = "Windowed (F)" if self.app.fullscreen else "Fullscreen (F)"
        self.full_btn.active = self.app.fullscreen
        self.full_btn.draw(s)
        self.demo_btn.draw(s)
        self.quit_btn.draw(s)


# ---------------------------------------------------------------- learn card
class Learn:
    def __init__(self, app, game_cls, demo=None):
        self.app, self.g, self.demo, self.t = app, game_cls, demo, 0.0
        self.start = Button((W // 2 + 20, 600, 240, 60), "Start! (Enter)", GREEN, 22, key=(pygame.K_RETURN, pygame.K_SPACE))
        self.back = Button((W // 2 - 260, 600, 240, 60), "Back (Esc)", WHITE, 22, key=pygame.K_ESCAPE)

    def handle(self, e):
        if self.demo:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.app.go(Hub(self.app))
            return
        if self.start.hit(e):
            self.app.go(Play(self.app, self.g))
        elif self.back.hit(e):
            self.app.go(Hub(self.app))

    def update(self, dt):
        self.t += dt
        if self.demo and self.t > 5:
            self.app.go(Play(self.app, self.g, demo=self.demo))

    def draw(self, s):
        p = panel(s, (90, 40, W - 180, 535), WHITE, radius=26, border=5, shadow=8)
        pygame.draw.rect(s, shade(self.g.color, 0.45), (p.x + 5, p.y + 5, p.w - 10, 110), border_radius=22)
        icon(s, self.g.icon, (p.x + 80, p.y + 60), 1.1, self.g.color)
        outlined(s, self.g.title, (p.x + 140, p.y + 42), 44, WHITE, anchor="midleft")
        pill(s, self.g.layer, (p.x + 142, p.y + 90), WHITE, 15, anchor="midleft")
        y = p.y + 135
        text(s, "The big idea", (p.x + 40, y), 22, self.g.color if self.g.color != YELLOW else INK, bold=True)
        y += 34
        for para in self.g.learn:
            y = paragraph(s, para, p.x + 40, y, p.w - 80, 19) + 8
        y += 6
        text(s, "How to play", (p.x + 40, y), 22, INK, bold=True)
        y += 34
        for line in self.g.howto:
            pygame.draw.circle(s, self.g.color, (p.x + 50, y + 11), 6)
            y = paragraph(s, line, p.x + 66, y, p.w - 110, 18) + 4
        if self.demo:
            pill(s, f"DEMO  -  starting in {max(0, 5 - int(self.t))}s  (Esc to exit)", (W // 2, 630), PINK, 18, anchor="center")
        else:
            self.start.draw(s)
            self.back.draw(s)


# ---------------------------------------------------------------- play
class Play:
    def __init__(self, app, game_cls, demo=None):
        self.app, self.g, self.demo = app, game_cls, demo
        self.game = game_cls(app, auto=demo is not None)
        self.paused = False

    def handle(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.go(Hub(self.app))
            return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_p and not self.demo:
            self.paused = not self.paused
            return
        if not self.paused:
            self.game.handle(e)

    def update(self, dt):
        if self.paused:
            return
        self.game.update(dt)
        if self.game.done:
            res = self.game.result()
            new_best = False if self.demo else self.app.record(self.g.key, res)
            self.app.go(Result(self.app, self.g, res, new_best, self.demo))

    def draw(self, s):
        self.game.draw(s)
        if self.paused:
            shade_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            shade_surf.fill((43, 45, 66, 150))
            s.blit(shade_surf, (0, 0))
            outlined(s, "PAUSED", (W // 2, H // 2 - 20), 64, YELLOW, width=4)
            text(s, "Press P to continue, Esc for the menu", (W // 2, H // 2 + 40), 20, WHITE, bold=True, anchor="midtop")


# ---------------------------------------------------------------- results
TITLES = ["Keep practising!", "Good start!", "Great job!", "Network master!"]


class Result:
    def __init__(self, app, game_cls, res, new_best, demo=None):
        self.app, self.g, self.res, self.new_best, self.demo, self.t = app, game_cls, res, new_best, demo, 0.0
        idx = GAMES.index(game_cls)
        self.nxt = GAMES[(idx + 1) % len(GAMES)]
        self.retry = Button((185, 600, 230, 60), "Retry (R)", YELLOW, 22, key=pygame.K_r)
        self.next = Button((435, 600, 230, 60), "Next game (N)", GREEN, 22, key=pygame.K_n)
        self.hub = Button((685, 600, 230, 60), "Menu (Esc)", WHITE, 22, key=pygame.K_ESCAPE)

    def handle(self, e):
        if self.demo:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.app.go(Hub(self.app))
            return
        if self.retry.hit(e):
            self.app.go(Play(self.app, self.g))
        elif self.next.hit(e):
            self.app.go(Learn(self.app, self.nxt))
        elif self.hub.hit(e):
            self.app.go(Hub(self.app))

    def update(self, dt):
        self.t += dt
        if self.demo and self.t > 7:
            self.demo.next()

    def draw(self, s):
        p = panel(s, (90, 30, W - 180, 550), WHITE, radius=26, border=5, shadow=8)
        stars = self.res["stars"]
        outlined(s, TITLES[stars], (W // 2, p.y + 48), 44, shade(self.g.color, 0.1), width=3)
        text(s, self.g.title, (W // 2, p.y + 82), 18, MID, bold=True, anchor="midtop")
        for k in range(3):
            shown = self.t > 0.35 * (k + 1)
            size = 34 if not shown else 34 + max(0, 10 - int((self.t - 0.35 * (k + 1)) * 40))
            star(s, (W // 2 - 80 + k * 80, p.y + 150), size, shown and k < stars)
        text(s, f"Score {self.res['score']}", (W // 2, p.y + 195), 34, INK, bold=True, anchor="midtop")
        best = self.app.scores.get(self.g.key, {}).get("best", 0)
        if self.new_best:
            pill(s, "NEW BEST!", (W // 2 + 150, p.y + 213), PINK, 16, anchor="midleft")
        elif not self.demo:
            text(s, f"best {best}", (W // 2 + 150, p.y + 210), 16, MID, bold=True, anchor="midleft")
        box = panel(s, (p.x + 30, p.y + 250, 330, 270), CREAM, radius=16, border=3, shadow=4)
        text(s, "Your stats", (box.x + 16, box.y + 12), 19, INK, bold=True)
        y = box.y + 46
        for line in self.res["stats"]:
            y = paragraph(s, line, box.x + 16, y, box.w - 30, 16) + 6
        box2 = panel(s, (p.x + 380, p.y + 250, p.w - 410, 270), shade(self.g.color, 0.75), radius=16, border=3, shadow=4)
        text(s, "What you just saw", (box2.x + 16, box2.y + 12), 19, INK, bold=True)
        y = box2.y + 46
        for line in self.res["lessons"]:
            pygame.draw.circle(s, INK, (box2.x + 22, y + 10), 5)
            y = paragraph(s, line, box2.x + 36, y, box2.w - 52, 16) + 8
        if self.demo:
            pill(s, "DEMO  -  next game coming up  (Esc to exit)", (W // 2, 630), PINK, 18, anchor="center")
        else:
            for b in (self.retry, self.next, self.hub):
                b.draw(s)


# ---------------------------------------------------------------- demo mode
class Demo:
    """Plays every game automatically: learn card -> 25 s of bot play -> results."""

    def __init__(self, app):
        self.app, self.i = app, 0

    def start(self):
        self.app.go(Learn(self.app, GAMES[0], demo=self))

    def next(self):
        self.i += 1
        if self.i >= len(GAMES):
            self.app.go(Hub(self.app))
        else:
            self.app.go(Learn(self.app, GAMES[self.i], demo=self))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CN Arcade")
    parser.add_argument("--windowed", action="store_true",
                        help="start in a window instead of fullscreen (F toggles)")
    App(fullscreen=not parser.parse_args().windowed).run()
