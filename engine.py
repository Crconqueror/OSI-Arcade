"""CN Arcade shared toolkit: cartoon-style drawing helpers and a small network simulator.

The simulator (Packet, Link) is what makes the games "real": packets wait in a
queue, are serialised at the link's rate, travel for the propagation delay and
can be lost at random or dropped when the queue is full.
"""
import heapq
import itertools
import math
import random
from collections import deque

import pygame

W, H = 1100, 700

# ---------------------------------------------------------------- palette
INK = (43, 45, 66)
WHITE = (255, 255, 255)
CREAM = (255, 249, 236)
SKY_TOP = (110, 205, 255)
SKY_BOTTOM = (210, 242, 255)
YELLOW = (255, 209, 59)
ORANGE = (255, 150, 40)
PINK = (255, 105, 160)
RED = (238, 66, 92)
GREEN = (52, 199, 120)
TEAL = (20, 190, 170)
BLUE = (45, 150, 255)
PURPLE = (150, 100, 235)
GREY = (205, 210, 222)
MID = (105, 110, 132)
DARK_GREEN = (22, 140, 80)
DARK_RED = (190, 30, 60)

SANS = "arialroundedmtbold,chalkboardse,comicsansms,trebuchetms,verdana,arial"
MONO = "menlo,monaco,consolas,dejavusansmono,couriernew"

_fonts, _cache = {}, {}


def shade(c, k):
    """k > 0 lightens towards white, k < 0 darkens."""
    if k >= 0:
        return tuple(int(v + (255 - v) * k) for v in c)
    return tuple(int(v * (1 + k)) for v in c)


def font(size, bold=False, mono=False):
    key = (size, bold, mono)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont(MONO if mono else SANS, size, bold=bold)
    return _fonts[key]


def render(s, size=20, color=INK, bold=False, mono=False):
    key = (s, size, color, bold, mono)
    img = _cache.get(key)
    if img is None:
        if len(_cache) > 4000:
            _cache.clear()
        img = font(size, bold, mono).render(s, True, color)
        _cache[key] = img
    return img


def text(surf, s, pos, size=20, color=INK, bold=False, mono=False, anchor="topleft"):
    img = render(str(s), size, color, bold, mono)
    r = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    surf.blit(img, r)
    return r


def outlined(surf, s, pos, size, color, outline=INK, width=3, anchor="center"):
    """Chunky cartoon title text with an outline and drop shadow."""
    img, out = render(s, size, color, True), render(s, size, outline, True)
    r = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    surf.blit(out, r.move(0, width + 3))
    for dx in (-width, 0, width):
        for dy in (-width, 0, width):
            if dx or dy:
                surf.blit(out, r.move(dx, dy))
    surf.blit(img, r)
    return r


def wrap(s, size, width, bold=False, mono=False):
    f, lines, cur = font(size, bold, mono), [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if not cur or f.size(trial)[0] <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def paragraph(surf, s, x, y, width, size=18, color=INK, bold=False, gap=3):
    lh = font(size, bold).get_linesize() + gap
    for line in wrap(s, size, width, bold):
        text(surf, line, (x, y), size, color, bold)
        y += lh
    return y


def panel(surf, rect, fill=WHITE, radius=18, border=4, shadow=6, border_color=INK):
    r = pygame.Rect(rect)
    if shadow:
        pygame.draw.rect(surf, border_color, r.move(0, shadow), border_radius=radius)
    pygame.draw.rect(surf, fill, r, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border_color, r, border, border_radius=radius)
    return r


def pill(surf, s, pos, fill, size=14, color=INK, anchor="topleft"):
    img = render(s, size, color, True)
    r = img.get_rect()
    r.inflate_ip(18, 6)
    setattr(r, anchor, (int(pos[0]), int(pos[1])))
    pygame.draw.rect(surf, fill, r, border_radius=r.h // 2)
    pygame.draw.rect(surf, INK, r, 2, border_radius=r.h // 2)
    surf.blit(img, img.get_rect(center=r.center))
    return r


class Button:
    def __init__(self, rect, label, color=YELLOW, size=22, key=None, text_color=INK):
        self.rect = pygame.Rect(rect)
        self.label, self.color, self.size, self.text_color = label, color, size, text_color
        self.keys = key if isinstance(key, tuple) else ((key,) if key else ())
        self.enabled = True
        self.active = False            # for toggle buttons

    def hovered(self):
        return self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())

    def draw(self, surf):
        lift = 3 if self.hovered() else 0
        r = self.rect.move(0, -lift)
        if not self.enabled:
            fill = GREY
        elif self.active:
            fill = shade(self.color, -0.1)
        else:
            fill = shade(self.color, 0.15) if lift else self.color
        panel(surf, r, fill, radius=14, border=3, shadow=5 + lift)
        col = self.text_color if self.enabled else MID
        text(surf, self.label, r.center, self.size, col, bold=True, anchor="center")
        if self.active:
            pygame.draw.circle(surf, WHITE, (r.right - 16, r.y + 16), 8)
            pygame.draw.circle(surf, INK, (r.right - 16, r.y + 16), 8, 2)
            pygame.draw.circle(surf, GREEN, (r.right - 16, r.y + 16), 4)

    def hit(self, e):
        if not self.enabled:
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            return True
        return e.type == pygame.KEYDOWN and e.key in self.keys


# ---------------------------------------------------------------- scenery
def cloud(surf, x, y, s):
    for dx, dy, r in ((0, 0, 30), (34, -16, 36), (70, 0, 28), (36, 8, 30)):
        pygame.draw.circle(surf, WHITE, (int(x + dx * s), int(y + dy * s)), int(r * s))


class Sky:
    def __init__(self):
        self.base = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            c = tuple(int(a + (b - a) * t) for a, b in zip(SKY_TOP, SKY_BOTTOM))
            pygame.draw.line(self.base, c, (0, y), (W, y))
        self.clouds = [[random.uniform(-100, W), random.uniform(20, H - 100),
                        random.uniform(0.6, 1.3), random.uniform(6, 18)] for _ in range(8)]

    def update(self, dt):
        for c in self.clouds:
            c[0] += c[3] * dt
            if c[0] > W + 150:
                c[0], c[1] = -180, random.uniform(20, H - 100)

    def draw(self, surf):
        surf.blit(self.base, (0, 0))
        for x, y, s, _ in self.clouds:
            cloud(surf, x, y, s)


def star(surf, c, r, filled=True, color=YELLOW):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a)))
    pygame.draw.polygon(surf, color if filled else GREY, pts)
    pygame.draw.polygon(surf, INK, pts, max(2, int(r) // 8))


def triangle(surf, c, size, direction, color=INK):
    x, y = c
    pts = {"right": [(x - size, y - size), (x + size, y), (x - size, y + size)],
           "left": [(x + size, y - size), (x - size, y), (x + size, y + size)],
           "up": [(x - size, y + size), (x, y - size), (x + size, y + size)],
           "down": [(x - size, y - size), (x, y + size), (x + size, y - size)]}[direction]
    pygame.draw.polygon(surf, color, pts)


def icon(surf, kind, c, s=1.0, color=WHITE):
    """Tiny vector icons for the game cards (no image files needed)."""
    x, y = c
    lw = max(2, int(3 * s))

    def R(dx, dy, w, h):
        return pygame.Rect(int(x + dx * s), int(y + dy * s), int(w * s), int(h * s))

    def P(dx, dy):
        return (int(x + dx * s), int(y + dy * s))

    if kind == "wrapper":
        for (dx, dy, w, h), col in (((-38, -26, 76, 52), PINK), ((-27, -18, 54, 36), BLUE), ((-16, -10, 32, 20), YELLOW)):
            pygame.draw.rect(surf, col, R(dx, dy, w, h), border_radius=int(6 * s))
            pygame.draw.rect(surf, INK, R(dx, dy, w, h), lw, border_radius=int(6 * s))
    elif kind == "subnet":
        for r, col in ((36, RED), (25, WHITE), (14, RED), (5, WHITE)):
            pygame.draw.circle(surf, col, P(0, 0), int(r * s))
            pygame.draw.circle(surf, INK, P(0, 0), int(r * s), lw)
    elif kind == "router":
        pts = [P(-30, -20), P(28, -24), P(-22, 24), P(30, 20), P(2, 0)]
        for a, b in ((0, 4), (1, 4), (2, 4), (3, 4), (0, 2), (1, 3)):
            pygame.draw.line(surf, INK, pts[a], pts[b], lw + 1)
        for i, p in enumerate(pts):
            pygame.draw.circle(surf, YELLOW if i == 4 else WHITE, p, int(10 * s))
            pygame.draw.circle(surf, INK, p, int(10 * s), lw)
    elif kind == "lossy":
        r = R(-34, -22, 68, 44)
        pygame.draw.rect(surf, WHITE, r, border_radius=int(5 * s))
        pygame.draw.rect(surf, INK, r, lw, border_radius=int(5 * s))
        pygame.draw.lines(surf, INK, False, [r.topleft, P(0, 4), r.topright], lw)
        pygame.draw.circle(surf, RED, P(30, 20), int(13 * s))
        pygame.draw.circle(surf, INK, P(30, 20), int(13 * s), lw)
        pygame.draw.line(surf, WHITE, P(24, 14), P(36, 26), lw)
        pygame.draw.line(surf, WHITE, P(36, 14), P(24, 26), lw)
    elif kind == "congestion":
        for i, h in enumerate((18, 32, 46, 26)):
            r = R(-36 + i * 19, 26 - h, 15, h)
            pygame.draw.rect(surf, (YELLOW, ORANGE, RED, GREEN)[i], r, border_radius=int(3 * s))
            pygame.draw.rect(surf, INK, r, lw, border_radius=int(3 * s))
    elif kind == "firewall":
        pts = [P(0, -34), P(30, -22), P(26, 12), P(0, 34), P(-26, 12), P(-30, -22)]
        pygame.draw.polygon(surf, ORANGE, pts)
        pygame.draw.polygon(surf, INK, pts, lw)
        pygame.draw.line(surf, INK, P(-28, -4), P(28, -4), lw)
        pygame.draw.line(surf, INK, P(-20, 14), P(20, 14), lw)
        pygame.draw.line(surf, INK, P(0, -4), P(0, 14), lw)
    elif kind == "dns":
        pygame.draw.line(surf, INK, P(12, 12), P(34, 34), int(9 * s))
        pygame.draw.circle(surf, WHITE, P(-6, -6), int(26 * s))
        pygame.draw.circle(surf, INK, P(-6, -6), int(26 * s), lw + 1)
        text(surf, "?", P(-6, -6), int(30 * s), INK, bold=True, anchor="center")


def envelope(surf, rect, fill, label="", size=13):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, fill, r, border_radius=4)
    pygame.draw.rect(surf, INK, r, 2, border_radius=4)
    pygame.draw.lines(surf, INK, False, [(r.x + 2, r.y + 2), r.center, (r.right - 3, r.y + 2)], 2)
    if label:
        text(surf, label, (r.centerx, r.bottom - 1), size, INK, bold=True, anchor="midbottom")


def dashed_line(surf, color, a, b, width=3, dash=10):
    (x1, y1), (x2, y2) = a, b
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    n = int(length // dash)
    for i in range(0, n, 2):
        t1, t2 = i / n, min(1, (i + 1) / n)
        pygame.draw.line(surf, color, (x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1),
                         (x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2), width)


class PacketLog:
    """A scrolling log of what is happening 'on the wire'."""

    def __init__(self, rect, title="Packet log", size=13):
        self.rect, self.title, self.size = pygame.Rect(rect), title, size
        self.items = deque(maxlen=80)

    def add(self, msg, color=INK):
        f = font(self.size, mono=True)
        maxw = self.rect.w - 24
        if f.size(msg)[0] > maxw:
            cw = max(1, f.size("M")[0])
            msg = msg[: max(4, maxw // cw - 2)] + ".."
        self.items.append((msg, color))

    def draw(self, surf):
        panel(surf, self.rect, CREAM, radius=14, border=3, shadow=4)
        text(surf, self.title, (self.rect.x + 12, self.rect.y + 8), 16, INK, bold=True)
        lh = font(self.size, mono=True).get_linesize() + 1
        n = max(1, (self.rect.h - 40) // lh)
        y = self.rect.y + 34
        for msg, color in list(self.items)[-n:]:
            text(surf, msg, (self.rect.x + 12, y), self.size, color, mono=True)
            y += lh


# ---------------------------------------------------------------- network simulator
class Packet:
    _ids = itertools.count()

    def __init__(self, seq=0, kind="DATA", flow=0, **extra):
        self.id = next(Packet._ids)
        self.seq, self.kind, self.flow = seq, kind, flow
        self.enq = self.depart = self.arrive = 0.0
        self.__dict__.update(extra)


class Link:
    """A one-way link: FIFO queue -> serialisation at `rate` pkt/s -> propagation `delay`.

    send() returns False when the queue is full (tail drop, like a congested router).
    update(now) returns (arrived, lost): lost packets were hit by random `loss`.
    """

    def __init__(self, rate, delay, loss=0.0, qcap=1000, jitter=0.0):
        self.rate, self.delay, self.loss, self.qcap, self.jitter = rate, delay, loss, qcap, jitter
        self.queue = deque()
        self.flight = []
        self.busy_until = 0.0
        self.dropped = self.lost = 0

    def send(self, pkt, now):
        if len(self.queue) >= self.qcap:
            self.dropped += 1
            return False
        pkt.enq = now
        self.queue.append(pkt)
        return True

    def update(self, now):
        lost = []
        while self.queue:
            start = max(self.busy_until, self.queue[0].enq)
            finish = start + 1.0 / self.rate
            if finish > now:
                break
            pkt = self.queue.popleft()
            self.busy_until = finish
            pkt.depart = finish
            pkt.arrive = finish + self.delay + random.uniform(0, self.jitter)
            if random.random() < self.loss:
                self.lost += 1
                pkt.lost_at = random.uniform(0.25, 0.75)
                lost.append(pkt)
                continue
            heapq.heappush(self.flight, (pkt.arrive, pkt.id, pkt))
        arrived = []
        while self.flight and self.flight[0][0] <= now:
            arrived.append(heapq.heappop(self.flight)[2])
        return arrived, lost

    def in_flight(self):
        return [p for _, _, p in self.flight]

    @staticmethod
    def progress(pkt, now):
        span = max(1e-6, pkt.arrive - pkt.depart)
        return min(1.0, max(0.0, (now - pkt.depart) / span))


def jain(values):
    """Jain's fairness index: 1.0 = perfectly fair, 1/n = one flow takes everything."""
    values = [v for v in values]
    if not values or sum(values) == 0:
        return 1.0
    return sum(values) ** 2 / (len(values) * sum(v * v for v in values))
