"""The seven CN Arcade mini-games.

Every game has the same shape: setup / on_event / step / render, plus bot()
which plays the game automatically for Demo mode.
"""
import heapq
import ipaddress
import itertools
import math
import random
from collections import deque

import pygame

from engine import (BLUE, CREAM, DARK_GREEN, DARK_RED, GREEN, GREY, H, INK, MID, ORANGE, PINK,
                    PURPLE, RED, TEAL, W, WHITE, YELLOW, Button, Link, Packet, PacketLog,
                    dashed_line, envelope, font, icon, jain, outlined, panel, paragraph, pill,
                    shade, star, text, triangle, wrap)

DEMO_SECONDS = 25


class Game:
    key = title = layer = icon = ""
    color = BLUE
    duration = 60
    learn, howto, lessons = [], [], []
    thresholds = (1, 2, 3)          # score needed for 1, 2, 3 stars

    def __init__(self, app=None, auto=False):
        self.app, self.auto = app, auto
        self.total_time = min(self.duration, DEMO_SECONDS) if auto else self.duration
        self.time_left = self.total_time
        self.t = 0.0
        self.score = 0
        self.done = False
        self.banner = None
        self.fx = []
        self.bot_t = 0.0
        self.setup()

    # hooks for each game
    def setup(self): pass
    def on_event(self, e): pass
    def step(self, dt): pass
    def bot(self, dt): pass
    def render(self, s): pass
    def stats(self): return []

    def stars(self):
        return sum(self.score >= t for t in self.thresholds)

    def result(self):
        return {"score": int(self.score), "stars": self.stars(), "stats": self.stats(),
                "lessons": self.lessons}

    # shared machinery
    def handle(self, e):
        if not self.auto and not self.done:
            self.on_event(e)

    def update(self, dt):
        if self.done:
            return
        self.t += dt
        self.time_left -= dt
        self.step(dt)
        if self.auto and not self.done:
            self.bot(dt)
        for f in self.fx:
            f["t"] += dt
        self.fx = [f for f in self.fx if f["t"] < f["life"]]
        if self.time_left <= 0:
            self.finish()

    def finish(self):
        self.done = True

    def say(self, msg, color=INK, secs=3.0):
        self.banner = (msg, color, self.t + secs)

    def float_text(self, msg, pos, color=DARK_GREEN):
        self.fx.append(dict(kind="text", msg=msg, pos=pos, color=color, t=0.0, life=1.0))

    def poof(self, pos, color=GREY):
        self.fx.append(dict(kind="poof", pos=pos, color=color, t=0.0, life=0.5))

    def confetti(self, pos):
        for _ in range(14):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(80, 220)
            self.fx.append(dict(kind="dot", pos=pos, vel=(math.cos(a) * v, math.sin(a) * v - 60),
                                color=random.choice((YELLOW, PINK, BLUE, GREEN, ORANGE)), t=0.0, life=0.8))

    def add_score(self, pts, pos=None):
        self.score += pts
        if pos:
            self.float_text(f"{pts:+d}", pos, DARK_GREEN if pts >= 0 else DARK_RED)

    def draw(self, s):
        self.render(s)
        for f in self.fx:
            k = f["t"] / f["life"]
            x, y = f["pos"]
            if f["kind"] == "text":
                text(s, f["msg"], (x, y - 40 * k), 24, f["color"], bold=True, anchor="center")
            elif f["kind"] == "poof":
                pygame.draw.circle(s, f["color"], (int(x), int(y)), int(8 + 26 * k), 4)
                text(s, "poof", (x, y - 22 - 10 * k), 14, MID, bold=True, anchor="center")
            elif f["kind"] == "dot":
                vx, vy = f["vel"]
                pygame.draw.circle(s, f["color"], (int(x + vx * f["t"]), int(y + vy * f["t"] + 200 * f["t"] ** 2)), 5)
        self.draw_hud(s)

    def draw_banner(self, s, rect, idle=""):
        if self.banner and self.t < self.banner[2]:
            msg, color = self.banner[0], self.banner[1]
        elif idle:
            msg, color = idle, MID
        else:
            return
        r = pygame.Rect(rect)
        panel(s, r, WHITE, radius=14, border=3, shadow=4, border_color=INK)
        pygame.draw.rect(s, color, (r.x + 10, r.y + 10, 8, r.h - 20), border_radius=4)
        paragraph(s, msg, r.x + 28, r.y + 10, r.w - 40, 18, color if color != MID else INK)

    def draw_hud(self, s):
        panel(s, (10, 8, W - 20, 62), WHITE, radius=16, border=3, shadow=4)
        icon(s, self.icon, (46, 39), 0.55, self.color)
        text(s, self.title, (82, 13), 25, INK, bold=True)
        text(s, self.layer, (83, 44), 14, MID)
        text(s, f"Score {int(self.score)}", (560, 39), 26, INK, bold=True, anchor="center")
        frac = max(0.0, self.time_left) / self.total_time
        bar = pygame.Rect(700, 28, 220, 22)
        pygame.draw.rect(s, GREY, bar, border_radius=11)
        fill = bar.copy()
        fill.w = int(bar.w * frac)
        if fill.w > 0:
            pygame.draw.rect(s, GREEN if frac > 0.3 else RED, fill, border_radius=11)
        pygame.draw.rect(s, INK, bar, 3, border_radius=11)
        text(s, f"{max(0, math.ceil(self.time_left))}s", (bar.centerx, bar.centery), 15, INK, bold=True, anchor="center")
        if self.auto:
            pill(s, "DEMO", (1078, 39), PINK, 15, anchor="midright")
        else:
            text(s, "P pause  S slow", (940, 22), 13, MID)
            text(s, "Esc quit", (940, 40), 13, MID)


# =============================================================== 1. Packet Wrapper
WRAP_SCENARIOS = [
    dict(title="Open https://shop.example", data="GET /", steps=[
        ("TCP  dst port 443", ["TCP  dst port 25", "UDP  dst port 53"], "TCP :443",
         "Web pages need every byte, so they use TCP. HTTPS servers listen on port 443."),
        ("IP  dst 203.0.113.10 (the server)", ["IP  dst 192.168.1.1 (gateway)", "IP  dst 192.168.1.50"], "IP to .113.10",
         "The IP header carries the FINAL destination: the web server, end to end."),
        ("ETH  dst ..:01 (gateway MAC)", ["ETH  dst = the web server's MAC", "ETH  dst ff:ff:ff:ff:ff:ff"], "ETH to gw",
         "The server is on another network, so the frame goes to the gateway's MAC. MACs change at every hop; IPs don't.")]),
    dict(title="Look up shop.example (DNS)", data="shop.example?", steps=[
        ("UDP  dst port 53", ["TCP  dst port 443", "UDP  dst port 123"], "UDP :53",
         "A DNS query is one tiny question: UDP port 53, no handshake needed."),
        ("IP  dst 8.8.8.8 (DNS server)", ["IP  dst 203.0.113.10", "IP  dst 192.168.1.20"], "IP to 8.8.8.8",
         "You ask the DNS server. You can't address the website yet: you don't know its IP!"),
        ("ETH  dst ..:01 (gateway MAC)", ["ETH  dst ff:ff:ff:ff:ff:ff", "ETH  dst ..:50 (printer)"], "ETH to gw",
         "8.8.8.8 is outside your LAN, so once again the frame goes to the gateway.")]),
    dict(title="Print a report on the office printer", data="%PDF report", steps=[
        ("TCP  dst port 9100", ["UDP  dst port 53", "TCP  dst port 22"], "TCP :9100",
         "A print job must arrive complete and in order: TCP. Printers listen on port 9100."),
        ("IP  dst 192.168.1.50 (printer)", ["IP  dst 192.168.1.1 (gateway)", "IP  dst 203.0.113.10"], "IP to .1.50",
         "The destination IP is the printer itself."),
        ("ETH  dst ..:50 (printer MAC)", ["ETH  dst ..:01 (gateway MAC)", "ETH  dst ff:ff:ff:ff:ff:ff"], "ETH to printer",
         "Same subnet (192.168.1.0/24): deliver straight to the printer's MAC. No router needed!")]),
    dict(title="Video call with a friend (198.51.100.7)", data="voice frame", steps=[
        ("UDP  dst port 5004 (RTP)", ["TCP  dst port 5004", "TCP  dst port 443"], "UDP :5004",
         "Live audio prefers UDP: a late packet is useless, and waiting for a resend only adds delay."),
        ("IP  dst 198.51.100.7 (friend)", ["IP  dst 192.168.1.1 (gateway)", "IP  dst 8.8.8.8"], "IP to friend",
         "The IP destination is your friend's address, even though the gateway forwards it."),
        ("ETH  dst ..:01 (gateway MAC)", ["ETH  dst = your friend's MAC", "ETH  dst ..:20 (yourself)"], "ETH to gw",
         "Your friend is on another network, so the next hop is the gateway.")]),
    dict(title="Send an email (mail server 203.0.113.25)", data="Hi team!", steps=[
        ("TCP  dst port 587 (SMTP)", ["UDP  dst port 587", "TCP  dst port 80"], "TCP :587",
         "Email must arrive intact: TCP. Mail submission uses SMTP on port 587."),
        ("IP  dst 203.0.113.25 (mail server)", ["IP  dst 8.8.8.8", "IP  dst 192.168.1.60"], "IP to .113.25",
         "The final destination is the mail server."),
        ("ETH  dst ..:01 (gateway MAC)", ["ETH  dst ..:60 (lab server)", "ETH  dst = mail server's MAC"], "ETH to gw",
         "Remote host, so the frame goes to the gateway MAC.")]),
    dict(title="SSH into the lab server", data="ls -la", steps=[
        ("TCP  dst port 22 (SSH)", ["TCP  dst port 23 (Telnet)", "UDP  dst port 22"], "TCP :22",
         "SSH runs on TCP port 22. (Telnet on 23 sends passwords in plain text!)"),
        ("IP  dst 192.168.1.60 (lab server)", ["IP  dst 192.168.1.1 (gateway)", "IP  dst 192.168.1.255"], "IP to .1.60",
         "The lab server's own IP is the destination."),
        ("ETH  dst ..:60 (lab server MAC)", ["ETH  dst ..:01 (gateway MAC)", "ETH  dst ff:ff:ff:ff:ff:ff"], "ETH to lab",
         "Same subnet again: deliver directly to the lab server's MAC.")]),
]
LAYER_NAMES = ["Application", "Transport", "Internet", "Link"]
LAYER_COLORS = [YELLOW, GREEN, BLUE, PINK]


class PacketWrapper(Game):
    key, title, icon, color, duration = "wrapper", "Packet Wrapper", "wrapper", PINK, 90
    layer = "All layers  ·  encapsulation"
    learn = ["Before data leaves your laptop it travels DOWN the stack. Each layer wraps it in a header: "
             "Transport adds ports, Internet adds IP addresses, Link adds MAC addresses.",
             "IP addresses name the final destination. MAC addresses only name the next hop on your local network."]
    howto = ["Read the mission, then choose the right header for each layer.",
             "Click a card or press 1, 2 or 3. Use the host table on the right!",
             "Fast answers earn bonus points. Wrong picks cost 40."]
    lessons = ["Each layer adds its own header: ports (Transport), IP addresses (Internet), MAC addresses (Link).",
               "The destination IP stays the same end to end, but the destination MAC is only the next hop: "
               "the gateway for remote hosts, the device itself on your own subnet.",
               "TCP when every byte matters (web, email, printing); UDP when speed matters more (DNS, live calls)."]
    thresholds = (500, 1300, 2000)

    def setup(self):
        self.order = WRAP_SCENARIOS[:]
        random.shuffle(self.order)
        self.si = self.first_try_ok = self.answered = self.wrong = 0
        self.state, self.state_t = "choose", 0.0
        self.start_scenario()

    def start_scenario(self):
        sc = self.order[self.si]
        self.segments = [("DATA: " + sc["data"], YELLOW)]
        self.li = 0
        self.anim = 1.0
        self.new_step()

    def new_step(self):
        correct, wrongs, _, _ = self.order[self.si]["steps"][self.li]
        self.options = [correct] + wrongs
        random.shuffle(self.options)
        self.disabled = set()
        self.step_t = 0.0
        self.first = True

    def card_rect(self, i):
        return pygame.Rect(250 + i * 280, 548, 260, 100)

    def choose(self, i):
        if self.state != "choose" or i in self.disabled:
            return
        correct, _, short, why = self.order[self.si]["steps"][self.li]
        pos = self.card_rect(i).center
        if self.options[i] == correct:
            self.add_score(100 + max(0, int(60 - 12 * self.step_t)), pos)
            self.answered += 1
            self.first_try_ok += self.first
            self.segments.insert(0, (short, LAYER_COLORS[self.li + 1]))
            if self.li == 2:
                self.segments.append(("FCS", PINK))
            self.say("Correct! " + why, DARK_GREEN, 5)
            self.anim = 0.0
            self.li += 1
            if self.li == 3:
                self.state, self.state_t = "send", 0.0
            else:
                self.new_step()
        else:
            self.disabled.add(i)
            self.first = False
            self.wrong += 1
            self.add_score(-40, pos)
            self.say("Not quite. " + why, DARK_RED, 5)

    def on_event(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.choose(e.key - pygame.K_1)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i in range(3):
                if self.card_rect(i).collidepoint(e.pos):
                    self.choose(i)

    def step(self, dt):
        self.step_t += dt
        self.anim = min(1.0, self.anim + dt * 4)
        if self.state == "send":
            self.state_t += dt
            if self.state_t > 1.3:
                self.si += 1
                if self.si >= len(self.order):
                    self.add_score(int(self.time_left) * 5)
                    self.finish()
                    return
                self.state = "choose"
                self.start_scenario()

    def bot(self, dt):
        if self.state != "choose":
            return
        self.bot_t += dt
        if self.bot_t > 1.4:
            self.bot_t = 0
            correct = self.order[self.si]["steps"][self.li][0]
            i = self.options.index(correct)
            if random.random() > 0.85:
                i = next(j for j in range(3) if j != i and j not in self.disabled)
            self.choose(i)

    def stats(self):
        return [f"Missions sent: {self.si} of {len(self.order)}",
                f"Right first time: {self.first_try_ok} of {self.answered} headers",
                f"Wrong picks: {self.wrong}"]

    def render(self, s):
        sc = self.order[min(self.si, len(self.order) - 1)]
        panel(s, (30, 85, 670, 95), WHITE)
        text(s, f"Mission {min(self.si + 1, len(self.order))} of {len(self.order)}", (50, 95), 16, MID, bold=True)
        text(s, sc["title"], (50, 116), 27, INK, bold=True)
        text(s, f"Application data:  \"{sc['data']}\"", (50, 152), 16, MID)

        hr = panel(s, (720, 85, 350, 160), CREAM)
        text(s, "Host table  (LAN 192.168.1.0/24)", (hr.x + 14, hr.y + 10), 15, INK, bold=True)
        for i, row in enumerate(["You         192.168.1.20  ..:20", "Gateway     192.168.1.1   ..:01",
                                 "Printer     192.168.1.50  ..:50", "Lab server  192.168.1.60  ..:60"]):
            text(s, row, (hr.x + 14, hr.y + 40 + i * 27), 15, INK, mono=True)

        # layer ladder
        for i, name in enumerate(LAYER_NAMES):
            r = pygame.Rect(30, 200 + i * 80, 190, 66)
            current = self.state == "choose" and i == self.li + 1
            done = i <= self.li
            panel(s, r, LAYER_COLORS[i] if (done or current) else WHITE, radius=14, border=3, shadow=4)
            text(s, name, r.center, 20, INK, bold=True, anchor="center")
            if current:
                triangle(s, (r.right + 16, r.centery), 10, "left", INK)
        text(s, "Data goes DOWN the stack", (32, 525), 14, MID, bold=True)

        # prompt + packet
        if self.state == "choose":
            outlined(s, f"Add the {LAYER_NAMES[self.li + 1].upper()} header", (250, 222), 28, LAYER_COLORS[self.li + 1], anchor="midleft")
        else:
            outlined(s, "Sending bits onto the wire...", (250, 222), 28, YELLOW, anchor="midleft")
        widths = [font(16, True).size(lbl)[0] + 28 for lbl, _ in self.segments]
        x = 660 - sum(widths) // 2
        if self.state == "send":
            x += int(self.state_t ** 2 * 700)
        for k, ((lbl, col), w) in enumerate(zip(self.segments, widths)):
            r = pygame.Rect(x, 262, w, 70)
            if k == 0 and self.anim < 1 and lbl != self.segments[-1][0]:
                r.x -= int((1 - self.anim) * 80)
            pygame.draw.rect(s, col, r, border_radius=10)
            pygame.draw.rect(s, INK, r, 3, border_radius=10)
            text(s, lbl, r.center, 16, INK, bold=True, anchor="center")
            x += w - 3
        if self.state == "send":
            text(s, "0110100101011101 0010110", (660 + int(self.state_t * 300), 350), 18, MID, mono=True, anchor="center")

        self.draw_banner(s, (250, 395, 820, 120), "Pick the correct header below. Think: is the destination on my own subnet?")

        if self.state == "choose":
            for i, opt in enumerate(self.options):
                r = self.card_rect(i)
                dis = i in self.disabled
                panel(s, r, GREY if dis else WHITE, radius=16, border=4, shadow=6)
                pygame.draw.circle(s, LAYER_COLORS[self.li + 1] if not dis else MID, (r.x + 22, r.y + 22), 15)
                pygame.draw.circle(s, INK, (r.x + 22, r.y + 22), 15, 2)
                text(s, str(i + 1), (r.x + 22, r.y + 22), 16, INK, bold=True, anchor="center")
                y = r.y + 40
                for line in wrap(opt, 17, r.w - 30, True):
                    text(s, line, (r.x + 16, y), 17, MID if dis else INK, bold=True)
                    y += 22


# =============================================================== 2. Subnet Sniper
QUESTIONS = {"network": "What is the NETWORK address?", "broadcast": "What is the BROADCAST address?",
             "hosts": "How many USABLE hosts?", "mask": "What is the subnet MASK?",
             "first": "What is the FIRST usable host?", "same": ""}


def make_question():
    prefix = random.choice([20, 22, 23, 24, 24, 25, 25, 26, 26, 27, 27, 28, 28, 29, 30])
    first = random.choice((10, 172, 192))
    if first == 10:
        ip = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    elif first == 172:
        ip = f"172.{random.randint(16, 31)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    else:
        ip = f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"
    addr = ipaddress.IPv4Address(ip)
    net = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)

    def variant(p):
        return ipaddress.ip_network(f"{ip}/{p}", strict=False)

    others = [p for p in (prefix - 1, prefix + 1, prefix - 2, prefix + 2) if 8 <= p <= 30]
    n = net.num_addresses
    kind = random.choice(["network", "broadcast", "hosts", "mask", "first", "same"])
    q = QUESTIONS[kind]
    if kind == "network":
        correct = str(net.network_address)
        cands = [str(variant(p).network_address) for p in others] + [str(net.broadcast_address), str(addr)]
    elif kind == "broadcast":
        correct = str(net.broadcast_address)
        cands = [str(variant(p).broadcast_address) for p in others] + [str(net.network_address), str(net.broadcast_address - 1)]
    elif kind == "hosts":
        correct = str(n - 2)
        cands = [str(n), str(n - 1), str(2 * n - 2), str(max(2, n // 2 - 2)), str(n + 2)]
    elif kind == "mask":
        correct = str(net.netmask)
        cands = [str(variant(p).netmask) for p in others]
    elif kind == "first":
        correct = str(net.network_address + 1)
        cands = [str(net.network_address), str(net.broadcast_address - 1), str(net.network_address + 2), str(net.broadcast_address)]
    else:
        inside = random.random() < 0.5
        if inside:
            other = net.network_address + random.randint(1, n - 2)
        else:
            other = net.broadcast_address + random.randint(1, min(60, n))
        q = f"Is {other} on the SAME subnet?"
        correct = "Yes" if inside else "No"
        cands = ["No" if inside else "Yes"]
    answers = [correct]
    for c in cands:
        if c not in answers and len(answers) < (2 if kind == "same" else 4):
            answers.append(c)
    k = 3
    while len(answers) < (2 if kind == "same" else 4):          # top up if candidates collided
        filler = str(addr + k) if kind != "hosts" else str(n * k - 2)
        if filler not in answers:
            answers.append(filler)
        k += 1
    random.shuffle(answers)
    why = (f"/{prefix} means mask {net.netmask}, so {n} addresses: "
           f"{net.network_address} to {net.broadcast_address} ({n - 2} usable).")
    return dict(ip=f"{ip}/{prefix}", q=q, answers=answers, correct=correct, why=why)


class SubnetSniper(Game):
    key, title, icon, color, duration = "subnet", "Subnet Sniper", "subnet", RED, 60
    layer = "Network layer  ·  IP addressing"
    learn = ["An IP address has a network part and a host part. The prefix (/26) says how many bits belong to the network.",
             "All host bits 0 = the network address. All host bits 1 = the broadcast address. Everything in between can be given to devices."]
    howto = ["Each round shows an IP address with its prefix and a question.",
             "Pop the balloon with the right answer: click it or press 1-4.",
             "Answer before the balloons float away. Streaks multiply your points!"]
    lessons = ["The prefix length says how many bits are network bits; the rest are host bits.",
               "Network address = host bits all 0, broadcast = host bits all 1, usable hosts = 2^(host bits) - 2.",
               "Two IPs can talk directly (no router) only if they share the same network address."]
    thresholds = (300, 900, 1500)
    BAL_W, BAL_H = 180, 100

    def setup(self):
        self.correct_n = self.total = self.streak = self.best_streak = 0
        self.next_q()

    def next_q(self):
        self.q = make_question()
        n = len(self.q["answers"])
        xs = [350, 750] if n == 2 else [160 + i * (780 / (n - 1)) for i in range(n)]
        self.balloons = [dict(text=a, x=xs[i], y=640 + random.uniform(0, 50), phase=random.uniform(0, 6), alive=True,
                              color=(YELLOW, PINK, BLUE, GREEN)[i % 4]) for i, a in enumerate(self.q["answers"])]
        self.q_t = 0.0
        self.state, self.state_t = "play", 0.0

    def bpos(self, b):
        return (b["x"] + math.sin(self.t * 2 + b["phase"]) * 10, b["y"])

    def answer(self, i):
        if self.state != "play" or not self.balloons[i]["alive"]:
            return
        b = self.balloons[i]
        self.total += 1
        if b["text"] == self.q["correct"]:
            mult = 1 + min(self.streak, 4) * 0.25
            self.add_score(int((100 + max(0, 60 - 6 * self.q_t)) * mult), self.bpos(b))
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            self.correct_n += 1
            b["alive"] = False
            self.confetti(self.bpos(b))
            self.say("Correct! " + self.q["why"], DARK_GREEN, 3)
            self.state, self.state_t = "feedback", 0.0
        else:
            self.add_score(-50, self.bpos(b))
            self.streak = 0
            b["alive"] = False
            self.poof(self.bpos(b), RED)
            self.say(f"Nope, it's {self.q['correct']}. " + self.q["why"], DARK_RED, 4)
            self.state, self.state_t = "reveal", 0.0

    def on_event(self, e):
        if e.type == pygame.KEYDOWN and pygame.K_1 <= e.key <= pygame.K_4:
            i = e.key - pygame.K_1
            if i < len(self.balloons):
                self.answer(i)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, b in enumerate(self.balloons):
                cx, cy = self.bpos(b)
                if ((e.pos[0] - cx) / (self.BAL_W / 2)) ** 2 + ((e.pos[1] - cy) / (self.BAL_H / 2)) ** 2 <= 1:
                    self.answer(i)
                    break

    def step(self, dt):
        self.q_t += dt
        if self.state == "play":
            for b in self.balloons:
                b["y"] -= 30 * dt
            if min(b["y"] for b in self.balloons) < 345:
                self.total += 1
                self.streak = 0
                self.say(f"Too slow! It was {self.q['correct']}. " + self.q["why"], DARK_RED, 4)
                self.state, self.state_t = "reveal", 0.0
        else:
            self.state_t += dt
            if self.state_t > (1.3 if self.state == "feedback" else 2.4):
                self.next_q()

    def bot(self, dt):
        if self.state != "play":
            return
        self.bot_t += dt
        if self.bot_t > 1.7:
            self.bot_t = 0
            idx = [b["text"] for b in self.balloons].index(self.q["correct"])
            if random.random() > 0.8:
                idx = (idx + 1) % len(self.balloons)
            self.answer(idx)

    def stats(self):
        return [f"Correct: {self.correct_n} of {self.total}", f"Best streak: {self.best_streak}"]

    def render(self, s):
        panel(s, (30, 85, 1040, 130), WHITE)
        outlined(s, self.q["ip"], (550, 128), 46, YELLOW)
        text(s, self.q["q"], (550, 185), 24, INK, bold=True, anchor="center")
        if self.streak >= 2:
            pill(s, f"Streak x{self.streak}", (1055, 100), ORANGE, 16, anchor="topright")
        self.draw_banner(s, (30, 228, 1040, 90), "Pop the right balloon before it floats away!")
        for i, b in enumerate(self.balloons):
            cx, cy = self.bpos(b)
            show_right = self.state == "reveal" and b["text"] == self.q["correct"]
            if not b["alive"] and not show_right:
                continue
            pygame.draw.line(s, INK, (cx, cy + self.BAL_H / 2), (cx + math.sin(self.t * 3 + b["phase"]) * 8, cy + self.BAL_H / 2 + 60), 2)
            r = pygame.Rect(0, 0, self.BAL_W, self.BAL_H)
            r.center = (int(cx), int(cy))
            pygame.draw.ellipse(s, GREEN if show_right else b["color"], r)
            pygame.draw.ellipse(s, INK, r, 4)
            pygame.draw.ellipse(s, WHITE, (r.x + 28, r.y + 14, 26, 16))
            triangle(s, (cx, r.bottom + 4), 7, "up", INK)
            text(s, b["text"], (cx, cy + 4), 21, INK, bold=True, anchor="center")
            pygame.draw.circle(s, WHITE, (r.x + 14, r.y + 18), 12)
            pygame.draw.circle(s, INK, (r.x + 14, r.y + 18), 12, 2)
            text(s, str(i + 1), (r.x + 14, r.y + 18), 14, INK, bold=True, anchor="center")


# =============================================================== 3. Router Rush
NODES = {"A": (90, 250), "B": (280, 190), "C": (500, 215), "D": (700, 270), "E": (110, 470),
         "F": (330, 400), "G": (540, 450), "H": (705, 582), "I": (330, 588)}
EDGES = [("A", "B", 4), ("A", "E", 3), ("B", "C", 5), ("B", "F", 2), ("C", "D", 3), ("C", "G", 4),
         ("D", "G", 2), ("D", "H", 6), ("E", "F", 3), ("E", "I", 5), ("F", "G", 4), ("F", "I", 3),
         ("G", "H", 2), ("I", "H", 4), ("A", "F", 6)]


def ekey(a, b):
    return tuple(sorted((a, b)))


COST = {ekey(a, b): c for a, b, c in EDGES}


def dijkstra(adj, src):
    dist, prev, heap = {src: 0}, {}, [(0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, 1e9):
            continue
        for v in adj[u]:
            nd = d + COST[ekey(u, v)]
            if nd < dist.get(v, 1e9):
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd, v))
    return dist, prev


def build_path(prev, src, dst):
    if dst != src and dst not in prev:
        return None
    path = [dst]
    while path[-1] != src:
        path.append(prev[path[-1]])
    return path[::-1]


class RouterRush(Game):
    key, title, icon, color, duration = "router", "Router Rush", "router", GREEN, 75
    layer = "Network layer  ·  routing"
    learn = ["Routers forward packets hop by hop. Each link has a cost (here: delay in ms), and the best path is the cheapest one, not always the one with fewest hops.",
             "Link-state routing (OSPF): every router knows the whole map and runs Dijkstra. When a link fails, the news is flooded and routes are recomputed."]
    howto = ["Build a route from the green router to the pink one by clicking routers in order.",
             "Click the last router again (or Backspace) to undo. Links can fail at any time!",
             "Score = how close you are to Dijkstra's best cost. Press T to peek at the routing table (-20)."]
    lessons = ["Routers pick paths by cost (delay, bandwidth), not hop count. Dijkstra finds the cheapest path to every destination.",
               "Link-state routing: a failed link is flooded to all routers and each recomputes its table - this is convergence.",
               "TTL stops packets looping forever: every hop subtracts 1 and the packet is dropped at 0."]
    thresholds = (300, 800, 1300)
    TTL = 6

    def setup(self):
        self.down = {}
        self.log = PacketLog((785, 85, 285, 600), "Router log")
        self.next_fail = 8.0
        self.delivered = self.optimal = self.peeks = self.dropped = 0
        self.new_packet()

    def adj(self):
        a = {n: [] for n in NODES}
        for x, y, _ in EDGES:
            if ekey(x, y) not in self.down:
                a[x].append(y)
                a[y].append(x)
        return a

    def best(self):
        dist, prev = dijkstra(self.adj(), self.src)
        return dist.get(self.dst), build_path(prev, self.src, self.dst)

    def new_packet(self):
        while True:
            self.src, self.dst = random.sample(list(NODES), 2)
            cost, path = self.best()
            if path and len(path) >= 3:
                break
        self.path = [self.src]
        self.state = "plan"
        self.peek = False
        self.bot_plan = None
        self.log.add(f"New packet  {self.src} -> {self.dst}", INK)

    def path_cost(self, path):
        return sum(COST[ekey(a, b)] for a, b in zip(path, path[1:]))

    def click_node(self, n):
        if self.state != "plan":
            return
        last = self.path[-1]
        if n == last and len(self.path) > 1:
            self.path.pop()
            return
        if n in self.path:
            self.say("That would make a loop - packets would circle forever!", DARK_RED)
            return
        if n not in self.adj()[last]:
            self.say(f"No working link from {last} to {n}.", DARK_RED)
            return
        if len(self.path) - 1 >= self.TTL:
            self.say("TTL would reach 0 - the packet would be dropped. Find a shorter route!", DARK_RED)
            return
        self.path.append(n)
        if n == self.dst:
            self.launch()

    def launch(self):
        cost = self.path_cost(self.path)
        best, _ = self.best()
        self.flight_info = (cost, best)
        self.state, self.fly_i, self.fly_p = "fly", 0, 0.0

    def arrive(self):
        cost, best = self.flight_info
        pts = int(100 * best / cost) + (50 if cost == best else 0) - (20 if self.peek else 0)
        self.add_score(pts, NODES[self.dst])
        self.delivered += 1
        self.optimal += cost == best
        verdict = "optimal!" if cost == best else f"best was {best}"
        self.log.add(f"Delivered via {'-'.join(self.path)}", DARK_GREEN)
        self.log.add(f"  cost {cost} ms ({verdict})", DARK_GREEN if cost == best else ORANGE)
        self.say(f"Delivered! Your cost {cost} ms, Dijkstra's best {best} ms.", DARK_GREEN if cost == best else ORANGE)
        self.new_packet()

    def fail_link(self):
        candidates = [ekey(a, b) for a, b, _ in EDGES if ekey(a, b) not in self.down]
        if self.state == "fly":
            used = {ekey(a, b) for a, b in zip(self.path, self.path[1:])}
            candidates = [k for k in candidates if k not in used]
        if not candidates or len(self.down) >= 2:
            return
        k = random.choice(candidates)
        self.down[k] = self.t + 14
        self.log.add(f"LINK {k[0]}-{k[1]} DOWN", DARK_RED)
        self.log.add("  flood LSA, all routers rerun Dijkstra", MID)
        if self.state == "plan":
            for i, (a, b) in enumerate(zip(self.path, self.path[1:])):
                if ekey(a, b) == k:
                    self.path = self.path[: i + 1]
                    self.say(f"Link {k[0]}-{k[1]} failed under your route! Re-plan from {self.path[-1]}.", DARK_RED)
                    break
            if self.best()[1] is None:
                self.dropped += 1
                self.log.add(f"  {self.dst} unreachable: packet dropped", DARK_RED)
                self.new_packet()
        self.bot_plan = None

    def on_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for n, (x, y) in NODES.items():
                if math.hypot(e.pos[0] - x, e.pos[1] - y) < 32:
                    self.click_node(n)
                    break
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE and self.state == "plan" and len(self.path) > 1:
                self.path.pop()
            elif e.key == pygame.K_t and self.state == "plan" and not self.peek:
                self.peek = True
                self.peeks += 1

    def step(self, dt):
        for k, until in list(self.down.items()):
            if until <= self.t:
                del self.down[k]
                self.log.add(f"LINK {k[0]}-{k[1]} back UP", DARK_GREEN)
        if self.t >= self.next_fail:
            self.next_fail = self.t + random.uniform(8, 12)
            self.fail_link()
        if self.state == "fly":
            a, b = self.path[self.fly_i], self.path[self.fly_i + 1]
            self.fly_p += dt / (COST[ekey(a, b)] * 0.08)
            if self.fly_p >= 1:
                self.fly_p = 0
                self.fly_i += 1
                if self.fly_i >= len(self.path) - 1:
                    self.arrive()

    def bot(self, dt):
        if self.state != "plan":
            return
        self.bot_t += dt
        if self.bot_t < 0.45:
            return
        self.bot_t = 0
        if not self.bot_plan or self.bot_plan[: len(self.path)] != self.path:
            _, prev = dijkstra(self.adj(), self.path[-1])
            rest = build_path(prev, self.path[-1], self.dst)
            if rest is None:
                return
            if random.random() < 0.2 and len(rest) > 2:          # sometimes take a detour
                k = ekey(rest[0], rest[1])
                self.down[k] = self.t + 0.001
                _, prev2 = dijkstra(self.adj(), self.path[-1])
                del self.down[k]
                alt = build_path(prev2, self.path[-1], self.dst)
                if alt and not set(alt[1:]) & set(self.path):
                    rest = alt
            self.bot_plan = self.path + rest[1:]
        self.click_node(self.bot_plan[len(self.path)])

    def stats(self):
        return [f"Packets delivered: {self.delivered}", f"Optimal routes: {self.optimal}",
                f"Routing-table peeks: {self.peeks}", f"Dropped (unreachable): {self.dropped}"]

    def render(self, s):
        panel(s, (30, 85, 740, 600), WHITE)
        cost = self.path_cost(self.path)
        text(s, f"Route a packet  {self.src}  to  {self.dst}", (50, 98), 22, INK, bold=True)
        text(s, f"Hops left (TTL): {self.TTL - (len(self.path) - 1)}     Your cost so far: {cost} ms", (50, 128), 16, MID)
        used = {ekey(a, b) for a, b in zip(self.path, self.path[1:])}
        for a, b, c in EDGES:
            k = ekey(a, b)
            pa, pb = NODES[a], NODES[b]
            if k in self.down:
                dashed_line(s, RED, pa, pb, 4)
                mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
                pygame.draw.line(s, RED, (mx - 9, my - 9), (mx + 9, my + 9), 5)
                pygame.draw.line(s, RED, (mx - 9, my + 9), (mx + 9, my - 9), 5)
                continue
            pygame.draw.line(s, INK, pa, pb, 10 if k in used else 6)
            pygame.draw.line(s, YELLOW if k in used else GREY, pa, pb, 6 if k in used else 3)
            mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
            pygame.draw.circle(s, WHITE, (int(mx), int(my)), 14)
            pygame.draw.circle(s, INK, (int(mx), int(my)), 14, 2)
            text(s, str(c), (mx, my), 14, INK, bold=True, anchor="center")
        for n, (x, y) in NODES.items():
            fill = GREEN if n == self.src else PINK if n == self.dst else YELLOW if n in self.path else WHITE
            pygame.draw.circle(s, INK, (x, y + 4), 28)
            pygame.draw.circle(s, fill, (x, y), 28)
            pygame.draw.circle(s, INK, (x, y), 28, 4)
            text(s, n, (x, y), 24, INK, bold=True, anchor="center")
        if self.state == "fly":
            a, b = NODES[self.path[self.fly_i]], NODES[self.path[self.fly_i + 1]]
            x = a[0] + (b[0] - a[0]) * self.fly_p
            y = a[1] + (b[1] - a[1]) * self.fly_p
            envelope(s, (x - 18, y - 13, 36, 26), ORANGE)
        self.draw_banner(s, (380, 620, 380, 58), "")
        if self.peek and self.state == "plan":
            r = panel(s, (785, 85, 285, 600), WHITE)
            text(s, f"Routing table of {self.src}", (r.x + 14, r.y + 10), 18, INK, bold=True)
            text(s, "dest   next hop   cost", (r.x + 14, r.y + 44), 14, MID, mono=True)
            dist, prev = dijkstra(self.adj(), self.src)
            y = r.y + 70
            for n in sorted(NODES):
                if n == self.src:
                    continue
                p = build_path(prev, self.src, n)
                hop = p[1] if p else "-"
                text(s, f" {n}        {hop}        {dist.get(n, '--')}", (r.x + 14, y), 15,
                     DARK_RED if n == self.dst else INK, mono=True)
                y += 26
            text(s, "Follow next hops = routing!", (r.x + 14, y + 10), 14, MID, bold=True)
        else:
            self.log.draw(s)


# =============================================================== 4. Lossy Link
PHASES = [("Clear skies", "short delay, almost no loss", 0.4, 0.02),
          ("Stormy link", "25% of packets get lost!", 0.4, 0.25),
          ("Satellite hop", "1.5 s one-way delay", 1.5, 0.03)]


class LossyLink(Game):
    key, title, icon, color, duration = "lossy", "Lossy Link", "lossy", ORANGE, 60
    layer = "Transport layer  ·  reliable delivery"
    learn = ["The network may lose packets. TCP-style reliability fixes this with sequence numbers, ACKs and a timer: if no ACK arrives in time, the packet is sent again.",
             "Go-Back-N keeps a WINDOW of unacknowledged packets in flight. On a timeout it resends the whole window."]
    howto = ["The sender works automatically. YOU tune it as the link changes in 3 phases.",
             "Up/Down: window size (how many packets in flight).  Left/Right: timeout.",
             "Score = 10 per delivered packet, -2 per retransmission. Watch the measured RTT!"]
    lessons = ["Reliable delivery = sequence numbers + ACKs + a retransmission timer.",
               "Go-Back-N resends the whole window after a loss, so big windows waste bandwidth on lossy links.",
               "Long-delay links need a big window (about rate x RTT) to keep the pipe full, and a timeout longer than the RTT."]
    thresholds = (700, 1200, 1650)
    RATE = 8
    LANE_X0, LANE_X1, DATA_Y, ACK_Y = 190, 910, 225, 290

    def setup(self):
        self.data = Link(self.RATE, 0.4, 0.0, qcap=64)
        self.acks = Link(60, 0.4, 0.0)
        self.window, self.timeout = 4, 2.0
        self.base = self.next = self.expected = 0
        self.timer = None
        self.delivered = self.retrans = self.dups = self.timeouts = 0
        self.sent_at = {}
        self.rtt = None
        self.phase = -1
        self.log = PacketLog((400, 445, 670, 240), "Packet log")
        self.established = False
        hs = 0.4
        self.handshake = [("SYN", 0.0, hs, True), ("SYN-ACK", hs, 2 * hs, False), ("ACK", 2 * hs, 3 * hs, True)]
        self.hs_logged = set()
        bx = 30
        self.btns = {"w-": Button((bx + 150, 505, 44, 40), "-", YELLOW, 24),
                     "w+": Button((bx + 270, 505, 44, 40), "+", YELLOW, 24),
                     "t-": Button((bx + 150, 575, 44, 40), "-", YELLOW, 24),
                     "t+": Button((bx + 270, 575, 44, 40), "+", YELLOW, 24)}

    def set_phase(self, i):
        self.phase = i
        name, desc, delay, loss = PHASES[i]
        self.data.delay, self.data.loss = delay, loss
        self.acks.delay, self.acks.loss = delay, loss / 2
        self.say(f"Phase {i + 1}: {name} - {desc}", ORANGE, 4)
        self.log.add(f"== Phase {i + 1}: {name} ({desc})", PURPLE)

    def change(self, what, d):
        if what == "w":
            self.window = max(1, min(16, self.window + d))
        else:
            self.timeout = round(max(0.5, min(5.0, self.timeout + d * 0.25)), 2)

    def transmit(self, seq, now, retrans):
        p = Packet(seq=seq, kind="DATA", retrans=retrans)
        if not self.data.send(p, now):
            self.log.add(f"seq {seq} dropped: sender queue full", DARK_RED)
        if retrans:
            self.retrans += 1
            self.sent_at.pop(seq, None)               # Karn: no RTT samples from resends
        else:
            self.sent_at[seq] = now

    def on_event(self, e):
        for k, b in self.btns.items():
            if b.hit(e):
                self.change(k[0], 1 if k[1] == "+" else -1)
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_UP:
                self.change("w", 1)
            elif e.key == pygame.K_DOWN:
                self.change("w", -1)
            elif e.key == pygame.K_RIGHT:
                self.change("t", 1)
            elif e.key == pygame.K_LEFT:
                self.change("t", -1)

    def step(self, dt):
        now = self.t
        phase = min(2, int(now / (self.total_time / 3)))
        if phase != self.phase:
            self.set_phase(phase)
        if not self.established:
            for name, t0, t1, fwd in self.handshake:
                if now >= t0 and name not in self.hs_logged:
                    self.hs_logged.add(name)
                    self.log.add(f"{'sender' if fwd else 'receiver'} -> {name}", BLUE)
            if now >= self.handshake[-1][2]:
                self.established = True
                self.log.add("Connection ESTABLISHED (3-way handshake)", DARK_GREEN)
            return
        while self.next < self.base + self.window:
            if self.base == self.next:
                self.timer = now
            self.transmit(self.next, now, False)
            self.next += 1
        if self.timer is not None and now - self.timer > self.timeout:
            self.timeouts += 1
            self.log.add(f"TIMEOUT! resend {self.base}..{self.next - 1} (Go-Back-N)", DARK_RED)
            for sq in range(self.base, self.next):
                self.transmit(sq, now, True)
            self.timer = now
        arrived, lost = self.data.update(now)
        for p in lost:
            self.poof((self.LANE_X0 + (self.LANE_X1 - self.LANE_X0) * p.lost_at, self.DATA_Y))
            self.log.add(f"seq {p.seq} LOST on the link", DARK_RED)
        for p in arrived:
            if p.seq == self.expected:
                self.expected += 1
                self.delivered += 1
            else:
                self.dups += 1
            self.acks.send(Packet(seq=self.expected, kind="ACK"), now)
        acks, _ = self.acks.update(now)
        for a in acks:
            if a.seq > self.base:
                t0 = self.sent_at.get(a.seq - 1)
                if t0 is not None:
                    sample = now - t0
                    self.rtt = sample if self.rtt is None else 0.8 * self.rtt + 0.2 * sample
                for sq in range(self.base, a.seq):
                    self.sent_at.pop(sq, None)
                self.base = a.seq
                self.timer = None if self.base == self.next else now
                if self.base % 10 == 0:
                    self.log.add(f"ACK {self.base}: {self.delivered} delivered in order", DARK_GREEN)
        self.score = self.delivered * 10 - self.retrans * 2

    def bot(self, dt):
        self.bot_t += dt
        if self.bot_t < 0.3:
            return
        self.bot_t = 0
        tw, tt = [(10, 1.0), (4, 1.0), (16, 4.0)][max(0, self.phase)]
        if self.window != tw:
            self.change("w", 1 if tw > self.window else -1)
        elif abs(self.timeout - tt) > 0.01:
            self.change("t", 1 if tt > self.timeout else -1)

    def stats(self):
        sent = self.delivered + self.retrans
        eff = 100 * self.delivered / sent if sent else 0
        return [f"Delivered in order: {self.delivered}", f"Retransmissions: {self.retrans}  (timeouts: {self.timeouts})",
                f"Duplicates discarded at receiver: {self.dups}", f"Efficiency: {eff:.0f}% of transmissions were useful"]

    def render(self, s):
        name, desc, _, _ = PHASES[max(0, self.phase)]
        panel(s, (30, 85, 680, 70), WHITE)
        text(s, f"Phase {self.phase + 1} of 3:  {name}", (48, 94), 22, INK, bold=True)
        text(s, desc, (48, 124), 16, MID)
        for i in range(3):
            pygame.draw.circle(s, ORANGE if i <= self.phase else GREY, (650 + i * 22, 120), 8)
            pygame.draw.circle(s, INK, (650 + i * 22, 120), 8, 2)
        panel(s, (725, 85, 345, 70), WHITE)
        text(s, f"Delivered {self.delivered}", (742, 95), 18, DARK_GREEN, bold=True)
        text(s, f"Resent {self.retrans}", (742, 122), 16, DARK_RED, bold=True)
        text(s, f"Duplicates {self.dups}", (900, 122), 16, MID, bold=True)
        text(s, f"Timeouts {self.timeouts}", (900, 95), 16, MID, bold=True)

        for label, x in (("Sender", 40), ("Receiver", 910)):
            r = panel(s, (x, 175, 150, 160), YELLOW if x == 40 else GREEN)
            text(s, label, (r.centerx, r.y + 14), 20, INK, bold=True, anchor="midtop")
            if x == 40:
                text(s, "Go-Back-N", (r.centerx, r.y + 44), 15, INK, anchor="midtop")
                text(s, f"next seq {self.next}", (r.centerx, r.y + 80), 15, INK, mono=True, anchor="midtop")
                text(s, f"queue {len(self.data.queue)}", (r.centerx, r.y + 104), 15, INK, mono=True, anchor="midtop")
            else:
                text(s, "expects", (r.centerx, r.y + 50), 15, INK, anchor="midtop")
                text(s, f"seq {self.expected}", (r.centerx, r.y + 74), 22, INK, bold=True, anchor="midtop")
        for y, lbl in ((self.DATA_Y, "DATA"), (self.ACK_Y, "ACK")):
            pygame.draw.line(s, INK, (self.LANE_X0, y), (self.LANE_X1, y), 4)
            text(s, lbl, (550, y - 30 if lbl == "DATA" else y + 12), 14, MID, bold=True, anchor="midtop")
        triangle(s, (self.LANE_X1 - 6, self.DATA_Y), 8, "right")
        triangle(s, (self.LANE_X0 + 6, self.ACK_Y), 8, "left")
        span = self.LANE_X1 - self.LANE_X0
        now = self.t
        if not self.established:
            for name, t0, t1, fwd in self.handshake:
                if t0 <= now < t1:
                    k = (now - t0) / (t1 - t0)
                    x = self.LANE_X0 + span * (k if fwd else 1 - k)
                    y = self.DATA_Y if fwd else self.ACK_Y
                    pill(s, name, (x, y), PURPLE, 15, WHITE, anchor="center")
        for p in self.data.in_flight():
            x = self.LANE_X0 + span * Link.progress(p, now)
            envelope(s, (x - 17, self.DATA_Y - 13, 34, 26), YELLOW if p.retrans else ORANGE, str(p.seq), 12)
        for a in self.acks.in_flight():
            x = self.LANE_X1 - span * Link.progress(a, now)
            pygame.draw.circle(s, GREEN, (int(x), self.ACK_Y), 13)
            pygame.draw.circle(s, INK, (int(x), self.ACK_Y), 13, 2)
            text(s, str(a.seq), (x, self.ACK_Y), 11, INK, bold=True, anchor="center")

        # sliding window strip
        start = max(0, self.base - 6)
        text(s, "Sequence numbers:", (40, 352), 14, MID, bold=True)
        for i in range(24):
            sq = start + i
            r = pygame.Rect(40 + i * 42, 372, 38, 38)
            col = GREEN if sq < self.base else YELLOW if sq < self.next else WHITE
            pygame.draw.rect(s, col, r, border_radius=6)
            pygame.draw.rect(s, INK, r, 2, border_radius=6)
            text(s, str(sq), r.center, 14, INK, bold=True, anchor="center")
            if sq == self.expected:
                triangle(s, (r.centerx, r.bottom + 9), 6, "up", DARK_GREEN)
        wx0 = 40 + (self.base - start) * 42 - 4
        ww = min(self.window, 24 - (self.base - start)) * 42 + 4
        pygame.draw.rect(s, BLUE, (wx0, 366, ww, 50), 4, border_radius=8)
        text(s, f"window = {self.window}", (wx0 + ww, 420), 13, BLUE, bold=True, anchor="topright")
        text(s, "green = ACKed   yellow = in flight   white = not sent", (650, 352), 13, MID)

        r = panel(s, (30, 445, 355, 240), WHITE)
        text(s, "Your controls", (r.x + 14, r.y + 10), 18, INK, bold=True)
        text(s, "Window", (r.x + 14, r.y + 70), 18, INK, bold=True)
        text(s, str(self.window), (r.x + 232, r.y + 80), 26, INK, bold=True, anchor="center")
        text(s, "Up / Down", (r.x + 14, r.y + 94), 12, MID)
        text(s, "Timeout", (r.x + 14, r.y + 140), 18, INK, bold=True)
        text(s, f"{self.timeout:.2f}s", (r.x + 232, r.y + 150), 20, INK, bold=True, anchor="center")
        text(s, "Left / Right", (r.x + 14, r.y + 164), 12, MID)
        rtt = f"{self.rtt:.2f} s" if self.rtt else "measuring..."
        text(s, f"Measured RTT: {rtt}", (r.x + 14, r.y + 190), 15, PURPLE, bold=True)
        text(s, f"Link rate {self.RATE} pkt/s  -> window ~ rate x RTT", (r.x + 14, r.y + 212), 12, MID)
        for b in self.btns.values():
            b.draw(s)
        if self.banner and self.t < self.banner[2]:
            self.draw_banner(s, (400, 445, 670, 60))
            self.log.rect = pygame.Rect(400, 515, 670, 170)
        else:
            self.log.rect = pygame.Rect(400, 445, 670, 240)
        self.log.draw(s)


# =============================================================== 5. Congestion Arena
class CongestionArena(Game):
    key, title, icon, color, duration = "congestion", "Congestion Arena", "congestion", PURPLE, 60
    layer = "Transport layer  ·  congestion control"
    learn = ["Three senders share one bottleneck link. Each one's congestion window (cwnd) = how many packets it may have in flight.",
             "Send too much and the router's queue overflows: packets are dropped. TCP grows cwnd slowly while things go well and HALVES it on a loss: AIMD."]
    howto = ["You are the BLUE flow. The two bots run TCP Reno.",
             "Hold UP to grow your cwnd. When you see DROP!, press DOWN to halve it.",
             "Score = packets delivered - 4 per drop. Aim for your fair share (a third of the link)."]
    lessons = ["AIMD: add a little per round trip while ACKs arrive, halve on loss - the famous sawtooth.",
               "Drops happen when the router queue overflows, and a full queue adds delay for everyone.",
               "Because every flow backs off the same way, competing flows converge to a fair share (Jain's index near 1)."]
    thresholds = (60, 120, 170)
    RATE, QCAP, DELAY = 12, 16, 0.35
    FLOWS = [("You", BLUE, 0.0), ("Reno bot", ORANGE, 0.0), ("Reno bot 2", PINK, 4.0)]

    def setup(self):
        self.link = Link(self.RATE, self.DELAY, loss=0.003, qcap=self.QCAP)
        self.flows = [dict(name=n, color=c, start=st, cwnd=1.0, ssth=64.0, inflight=0, delivered=0,
                           drops=0, last_cut=-9.0, recent=deque()) for n, c, st in self.FLOWS]
        self.events, self.ev_id = [], itertools.count()
        self.hist = deque(maxlen=300)
        self.sample_t = 0.0
        self.last_drop = -9.0
        self.btn_up = Button((300, 625, 220, 50), "Grow cwnd (Up)", GREEN, 18)
        self.btn_down = Button((540, 625, 220, 50), "Halve (Down)", RED, 18, text_color=WHITE)
        self.up_clicks = 0.0

    def is_bot(self, i):
        return i > 0 or self.auto

    def halve(self, i):
        f = self.flows[i]
        f["ssth"] = max(2.0, f["cwnd"] / 2)
        f["cwnd"] = f["ssth"]
        f["last_cut"] = self.t

    def on_event(self, e):
        if self.btn_down.hit(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_DOWN):
            self.halve(0)
        if self.btn_up.hit(e):
            self.up_clicks += 2

    def step(self, dt):
        now = self.t
        me = self.flows[0]
        if not self.auto:
            if pygame.key.get_pressed()[pygame.K_UP]:
                me["cwnd"] = min(60.0, me["cwnd"] + 5 * dt)
            if self.up_clicks > 0:
                me["cwnd"] = min(60.0, me["cwnd"] + self.up_clicks)
                self.up_clicks = 0
        for i, f in enumerate(self.flows):
            if now < f["start"]:
                continue
            while f["inflight"] < int(f["cwnd"]):
                f["inflight"] += 1
                if not self.link.send(Packet(flow=i), now):
                    heapq.heappush(self.events, (now + 2 * self.DELAY, next(self.ev_id), "loss", i))
        arrived, lost = self.link.update(now)
        for p in arrived:
            heapq.heappush(self.events, (now + self.DELAY, next(self.ev_id), "ack", p.flow))
        for p in lost:
            heapq.heappush(self.events, (now + 2 * self.DELAY, next(self.ev_id), "loss", p.flow))
        while self.events and self.events[0][0] <= now:
            _, _, kind, i = heapq.heappop(self.events)
            f = self.flows[i]
            f["inflight"] -= 1
            if kind == "ack":
                f["delivered"] += 1
                f["recent"].append(now)
                if self.is_bot(i):
                    f["cwnd"] += 1.0 if f["cwnd"] < f["ssth"] else 1.0 / f["cwnd"]
            else:
                f["drops"] += 1
                if i == 0:
                    self.last_drop = now
                    if not self.auto:
                        self.say("DROP! Your packet was lost - press DOWN to halve your cwnd.", DARK_RED, 1.5)
                if self.is_bot(i) and now - f["last_cut"] > 2 * self.DELAY + 0.4:
                    self.halve(i)
        for f in self.flows:
            while f["recent"] and now - f["recent"][0] > 5:
                f["recent"].popleft()
        self.sample_t += dt
        if self.sample_t >= 0.1:
            self.sample_t = 0
            self.hist.append([f["cwnd"] if now >= f["start"] else None for f in self.flows])
        self.score = me["delivered"] - 4 * me["drops"]

    def throughputs(self):
        return [len(f["recent"]) / min(5.0, max(0.5, self.t - f["start"])) for f in self.flows if self.t >= f["start"]]

    def stats(self):
        me = self.flows[0]
        bots = self.flows[1:]
        return [f"You delivered {me['delivered']} packets, lost {me['drops']}",
                f"Reno bots delivered {bots[0]['delivered']} and {bots[1]['delivered']}",
                f"Fairness (Jain's index): {jain(self.throughputs()):.2f}"]

    def render(self, s):
        now = self.t
        r = panel(s, (30, 85, 1040, 165), WHITE)
        for i, f in enumerate(self.flows):
            y = r.y + 35 + i * 48
            active = now >= f["start"]
            pygame.draw.line(s, INK if active else GREY, (110, y), (300, r.y + 82), 4)
            pygame.draw.circle(s, f["color"] if active else GREY, (85, y), 20)
            pygame.draw.circle(s, INK, (85, y), 20, 3)
            pill(s, f["name"] if active else "joins soon", (112, y - 24), WHITE, 12)
        q = pygame.Rect(300, r.y + 55, self.QCAP * 14 + 12, 54)
        pygame.draw.rect(s, CREAM, q, border_radius=8)
        pygame.draw.rect(s, INK, q, 3, border_radius=8)
        for k, p in enumerate(list(self.link.queue)[: self.QCAP]):
            pygame.draw.rect(s, self.flows[p.flow]["color"], (q.right - 18 - k * 14, q.y + 10, 11, 34), border_radius=3)
        text(s, f"Router queue {len(self.link.queue)}/{self.QCAP}", (q.x, q.y - 24), 14, INK, bold=True)
        x0, x1, py = q.right + 10, 940, r.y + 82
        pygame.draw.line(s, INK, (x0, py), (x1, py), 14)
        pygame.draw.line(s, GREY, (x0, py), (x1, py), 8)
        text(s, f"Bottleneck: {self.RATE} packets/s", (x0 + 20, py + 16), 14, INK, bold=True)
        for p in self.link.in_flight():
            x = x0 + (x1 - x0) * Link.progress(p, now)
            pygame.draw.rect(s, self.flows[p.flow]["color"], (x - 7, py - 7, 14, 14), border_radius=3)
            pygame.draw.rect(s, INK, (x - 7, py - 7, 14, 14), 2, border_radius=3)
        pygame.draw.circle(s, GREEN, (975, py), 26)
        pygame.draw.circle(s, INK, (975, py), 26, 3)
        text(s, "Server", (975, py + 30), 13, INK, bold=True, anchor="midtop")

        g = panel(s, (30, 265, 680, 345), WHITE)
        text(s, "Congestion window (cwnd) over time - look for the sawtooth!", (g.x + 14, g.y + 10), 16, INK, bold=True)
        plot = pygame.Rect(g.x + 50, g.y + 42, g.w - 70, g.h - 70)
        pygame.draw.rect(s, CREAM, plot)
        top = max(20, max((c for row in self.hist for c in row if c is not None), default=20) * 1.15)
        for v in range(0, int(top) + 1, 10):
            y = plot.bottom - plot.h * v / top
            pygame.draw.line(s, GREY, (plot.x, y), (plot.right, y), 1)
            text(s, str(v), (plot.x - 8, y), 12, MID, anchor="midright")
        for i, f in enumerate(self.flows):
            pts = [(plot.x + plot.w * k / 299, plot.bottom - plot.h * row[i] / top)
                   for k, row in enumerate(self.hist) if row[i] is not None]
            if len(pts) > 1:
                pygame.draw.lines(s, f["color"], False, pts, 4 if i == 0 else 3)
        pygame.draw.rect(s, INK, plot, 2)
        text(s, "last 30 seconds", (plot.right, plot.bottom + 6), 12, MID, anchor="topright")
        if now - self.last_drop < 0.7:
            outlined(s, "DROP!", (plot.centerx, plot.centery), 56, RED)

        st = panel(s, (725, 265, 345, 345), WHITE)
        me = self.flows[0]
        text(s, "Your cwnd", (st.x + 16, st.y + 10), 16, MID, bold=True)
        text(s, f"{me['cwnd']:.1f}", (st.x + 16, st.y + 30), 40, BLUE, bold=True)
        text(s, f"drops: {me['drops']}", (st.right - 16, st.y + 44), 18, DARK_RED, bold=True, anchor="topright")
        text(s, "Throughput (packets/s)", (st.x + 16, st.y + 92), 15, INK, bold=True)
        thr = {i: len(f["recent"]) / min(5.0, max(0.5, now - f["start"])) for i, f in enumerate(self.flows) if now >= f["start"]}
        for i, f in enumerate(self.flows):
            y = st.y + 122 + i * 52
            text(s, f["name"], (st.x + 16, y), 14, INK, bold=True)
            bar = pygame.Rect(st.x + 16, y + 20, 300, 20)
            pygame.draw.rect(s, GREY, bar, border_radius=6)
            v = thr.get(i, 0)
            if v > 0:
                pygame.draw.rect(s, f["color"], (bar.x, bar.y, int(bar.w * min(1, v / self.RATE)), bar.h), border_radius=6)
            pygame.draw.rect(s, INK, bar, 2, border_radius=6)
            fx = bar.x + bar.w * (1 / 3)
            pygame.draw.line(s, INK, (fx, bar.y - 4), (fx, bar.bottom + 4), 3)
            text(s, f"{v:.1f}", (bar.right - 6, y), 13, INK, bold=True, anchor="topright")
        text(s, "| = fair share (1/3 of the link)", (st.x + 16, st.y + 278), 12, MID)
        text(s, f"Fairness (Jain): {jain(list(thr.values())):.2f}", (st.x + 16, st.y + 300), 18, PURPLE, bold=True)
        self.btn_up.draw(s)
        self.btn_down.draw(s)
        self.draw_banner(s, (780, 620, 290, 64), "Hold UP to grow, DOWN on DROP!")


# =============================================================== 6. Firewall Defender
TOGGLES = [("telnet", "No Telnet (23)", "DENY tcp dport 23"), ("ssh", "No outside SSH", "DENY tcp dport 22 if src not 10.x"),
           ("synlimit", "SYN limit 3/s", "DENY SYN above 3 per second"), ("alltcp", "Block ALL TCP", "DENY all tcp")]
TOGGLE_ACL = {k: acl for k, _, acl in TOGGLES}
SCAN_PORTS = [21, 22, 23, 25, 80, 110, 135, 139, 143, 443, 445, 3306, 3389, 8080]


def rand_public_ip():
    return f"{random.choice([31, 49, 77, 88, 101, 117, 134, 152, 176, 185, 201, 212])}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"


class FirewallDefender(Game):
    key, title, icon, color, duration = "firewall", "Firewall Defender", "firewall", TEAL, 75
    layer = "Network security  ·  packet filtering"
    learn = ["A firewall inspects each packet's header - source IP, protocol, destination port, TCP flags - and checks it against an ordered list of rules. The first matching rule decides: allow or deny.",
             "Attacks come in waves: a port scan, password guessing on SSH and Telnet, then a SYN flood from thousands of fake addresses."]
    howto = ["Packets fly from the Internet towards your server. Real users and attackers look alike!",
             "Click a packet to block its source IP. Toggle rules with the buttons below.",
             "+10 per attack blocked, -25 per real user blocked. Keep the server alive!"]
    lessons = ["Firewalls match header fields (IP, protocol, port, flags) against ordered rules: the first match wins.",
               "Blocking one IP stops a single scanner, but a SYN flood uses spoofed IPs - rate limiting works where IP blocks can't.",
               "Over-broad rules (block all TCP) stop the attack AND your real users."]
    thresholds = (200, 550, 850)
    WALL_X, CARD_W, LANES = 690, 170, (142, 198, 254, 310, 366)

    def setup(self):
        self.rules_on = set()
        self.ip_blocks = deque(maxlen=4)
        self.packets = []
        self.health = 100
        self.syn_times = deque()
        self.spawn_acc = {}
        self.wave = -1
        self.counts = dict(att=0, att_blocked=0, legit=0, legit_ok=0)
        self.log = PacketLog((760, 450, 310, 235), "Firewall log")
        self.btns = {k: Button((45 + (i % 2) * 172, 495 + (i // 2) * 58, 162, 48), lbl, YELLOW if k != "alltcp" else PINK, 15)
                     for i, (k, lbl, _) in enumerate(TOGGLES)}
        self.bot_done = set()

    def frac(self):
        return self.t / self.total_time

    def spawn(self, kind):
        free = [l for l in self.LANES
                if all(p["x"] > 40 + self.CARD_W + 14 for p in self.packets if p["y"] == l and p["state"] == "in")]
        if not free:
            return False                              # all lanes busy: wait (keeps cards readable)
        p = dict(x=40.0, y=random.choice(free), state="in", t=0.0)
        if kind == "https":
            p.update(proto="TCP", flags=random.choice(["SYN", "ACK", "ACK", "ACK"]), dport=443, src=rand_public_ip(), attack=False)
        elif kind == "dns":
            p.update(proto="UDP", flags="", dport=53, src="8.8.8.8", attack=False, label="UDP reply from :53")
        elif kind == "admin":
            p.update(proto="TCP", flags="ACK", dport=22, src="10.0.0.5", attack=False)
        elif kind == "scan":
            self.scan_i = getattr(self, "scan_i", -1) + 1
            p.update(proto="TCP", flags="SYN", dport=SCAN_PORTS[self.scan_i % len(SCAN_PORTS)], src="203.0.113.66", attack=True, dmg=1)
        elif kind == "brute":
            if random.random() < 0.65:
                p.update(proto="TCP", flags="ACK", dport=22, src=random.choice(["198.51.100.23", "198.51.100.24", "198.51.100.31", rand_public_ip()]), attack=True, dmg=2)
            else:
                p.update(proto="TCP", flags="SYN", dport=23, src=rand_public_ip(), attack=True, dmg=2)
        elif kind == "flood":
            p.update(proto="TCP", flags="SYN", dport=443, src=rand_public_ip(), attack=True, dmg=0.5)
        p.setdefault("label", f"{p['proto']} {p['flags']} to :{p['dport']}".replace("  ", " "))
        self.packets.append(p)
        return True

    def evaluate(self, p):
        for ip in self.ip_blocks:
            if p["src"] == ip:
                return f"DENY src {ip}"
        if "telnet" in self.rules_on and p["proto"] == "TCP" and p["dport"] == 23:
            return "DENY tcp/23"
        if "ssh" in self.rules_on and p["dport"] == 22 and not p["src"].startswith("10."):
            return "DENY external ssh"
        if "alltcp" in self.rules_on and p["proto"] == "TCP":
            return "DENY all tcp"
        if "synlimit" in self.rules_on and p["flags"] == "SYN":
            while self.syn_times and self.t - self.syn_times[0] > 1:
                self.syn_times.popleft()
            if len(self.syn_times) >= 3:
                return "DENY syn rate>3/s"
            self.syn_times.append(self.t)
        return None

    def block_ip(self, ip):
        if ip not in self.ip_blocks and not ip.startswith("10."):
            self.ip_blocks.append(ip)
            self.log.add(f"+ rule: DENY src {ip}", PURPLE)
        elif ip.startswith("10."):
            self.say("That's your own admin (10.x is internal) - not blocking.", ORANGE)

    def toggle(self, k):
        if k in self.rules_on:
            self.rules_on.discard(k)
            self.log.add(f"- rule off: {TOGGLE_ACL[k]}", MID)
        else:
            self.rules_on.add(k)
            self.log.add(f"+ rule on: {TOGGLE_ACL[k]}", PURPLE)
        self.btns[k].active = k in self.rules_on

    def on_event(self, e):
        for k, b in self.btns.items():
            if b.hit(e):
                self.toggle(k)
                return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for p in reversed(self.packets):
                if p["state"] == "in" and pygame.Rect(p["x"], p["y"], self.CARD_W, 50).collidepoint(e.pos):
                    self.block_ip(p["src"])
                    break

    def step(self, dt):
        f = self.frac()
        wave = 0 if f < 0.2 else 1 if f < 0.47 else 2 if f < 0.73 else 3
        if wave != self.wave:
            self.wave = wave
            msg = ["Calm traffic: real users browsing.", "Wave 1: PORT SCAN! One host is probing every port.",
                   "Wave 2: PASSWORD GUESSING on SSH (22) and Telnet (23) from many hosts!",
                   "Wave 3: SYN FLOOD on port 443 from thousands of spoofed IPs!"][wave]
            self.say(msg, DARK_RED if wave else DARK_GREEN, 5)
            self.log.add("== " + msg, DARK_RED if wave else DARK_GREEN)
        rates = {"https": 1.3, "dns": 0.35, "admin": 0.2}
        rates.update({1: {"scan": 2.6}, 2: {"brute": 2.4}, 3: {"flood": 8.0}}.get(wave, {}))
        for kind, rate in rates.items():
            self.spawn_acc[kind] = min(3.0, self.spawn_acc.get(kind, random.random()) + rate * dt)
            while self.spawn_acc[kind] >= 1 and self.spawn(kind):
                self.spawn_acc[kind] -= 1
        for p in self.packets:
            p["t"] += dt
            if p["state"] == "in":
                p["x"] += 210 * dt
                if p["x"] + self.CARD_W >= self.WALL_X:
                    reason = self.evaluate(p)
                    if p["attack"]:
                        self.counts["att"] += 1
                    else:
                        self.counts["legit"] += 1
                    if reason:
                        p["state"], p["t"] = "blocked", 0.0
                        pos = (self.WALL_X - 40, p["y"] + 25)
                        if p["attack"]:
                            self.counts["att_blocked"] += 1
                            self.add_score(10, pos)
                        else:
                            self.add_score(-25, pos)
                            self.log.add(f"oops: real user {p['src']} blocked", DARK_RED)
                    else:
                        p["state"] = "pass"
                        if not p["attack"]:
                            self.counts["legit_ok"] += 1
                            self.score += 2
            elif p["state"] == "pass":
                p["x"] += 230 * dt
                if p["x"] >= 900:
                    p["state"] = "gone"
                    if p["attack"]:
                        self.health -= p.get("dmg", 3)
                        self.add_score(-5, (1000, 180))
        self.packets = [p for p in self.packets if p["state"] != "gone" and not (p["state"] == "blocked" and p["t"] > 0.5)]
        if self.health <= 0:
            self.health = 0
            self.say("The server went down!", DARK_RED)
            self.finish()

    def bot(self, dt):
        f = self.frac()
        if f > 0.27 and "scan" not in self.bot_done:
            self.bot_done.add("scan")
            self.block_ip("203.0.113.66")
        if f > 0.52 and "brute" not in self.bot_done:
            self.bot_done.add("brute")
            self.toggle("telnet")
            self.toggle("ssh")
        if f > 0.77 and "flood" not in self.bot_done:
            self.bot_done.add("flood")
            self.toggle("synlimit")

    def stats(self):
        c = self.counts
        return [f"Attack packets blocked: {c['att_blocked']} of {c['att']}",
                f"Real users let through: {c['legit_ok']} of {c['legit']}",
                f"Server health left: {int(self.health)}%"]

    def render(self, s):
        cl = panel(s, (30, 90, 120, 330), WHITE)
        text(s, "Internet", (cl.centerx, cl.y + 12), 18, INK, bold=True, anchor="midtop")
        for i in range(3):
            pygame.draw.circle(s, BLUE, (cl.centerx, cl.y + 90 + i * 80), 26)
            pygame.draw.circle(s, INK, (cl.centerx, cl.y + 90 + i * 80), 26, 3)
        sv = panel(s, (900, 120, 170, 280), WHITE)
        text(s, "Your server", (sv.centerx, sv.y + 12), 18, INK, bold=True, anchor="midtop")
        for i in range(3):
            r = pygame.Rect(sv.x + 30, sv.y + 50 + i * 52, 110, 40)
            pygame.draw.rect(s, GREY, r, border_radius=6)
            pygame.draw.rect(s, INK, r, 3, border_radius=6)
            pygame.draw.circle(s, GREEN if self.health > 30 else RED, (r.right - 16, r.centery), 6)
        hb = pygame.Rect(sv.x + 20, sv.bottom - 50, 130, 22)
        pygame.draw.rect(s, GREY, hb, border_radius=8)
        pygame.draw.rect(s, GREEN if self.health > 40 else RED, (hb.x, hb.y, int(hb.w * self.health / 100), hb.h), border_radius=8)
        pygame.draw.rect(s, INK, hb, 2, border_radius=8)
        text(s, f"health {int(self.health)}%", (hb.centerx, hb.bottom + 4), 13, INK, bold=True, anchor="midtop")
        for row in range(9):
            for col in range(2):
                off = 10 if row % 2 else 0
                r = pygame.Rect(self.WALL_X + col * 22 - off + 10, 90 + row * 37, 22, 37)
                pygame.draw.rect(s, ORANGE if (row + col) % 2 else RED, r)
                pygame.draw.rect(s, INK, r, 2)
        text(s, "FIREWALL", (self.WALL_X + 32, 432), 14, INK, bold=True, anchor="midtop")
        for p in self.packets:
            r = pygame.Rect(int(p["x"]), p["y"], self.CARD_W, 50)
            if p["state"] == "blocked":
                k = p["t"] / 0.5
                r = r.inflate(-int(60 * k), -int(20 * k))
                fill = shade(RED, 0.4)
            else:
                fill = WHITE if p["state"] == "in" else shade(GREEN, 0.5)
            pygame.draw.rect(s, INK, r.move(0, 3), border_radius=10)
            pygame.draw.rect(s, fill, r, border_radius=10)
            pygame.draw.rect(s, INK, r, 3, border_radius=10)
            if p["state"] != "blocked":
                text(s, p["label"], (r.x + 10, r.y + 5), 15, INK, bold=True)
                text(s, p["src"], (r.x + 10, r.y + 27), 14, MID, mono=True)
        self.draw_banner(s, (160, 90, 520, 52), "")
        rp = panel(s, (30, 450, 355, 235), WHITE)
        text(s, "Rule switches", (rp.x + 14, rp.y + 10), 17, INK, bold=True)
        for b in self.btns.values():
            b.draw(s)
        text(s, "Tip: click a packet to block its IP", (rp.x + 14, rp.bottom - 28), 13, MID, bold=True)
        ac = panel(s, (400, 450, 345, 235), CREAM)
        text(s, "ACL  (first match wins)", (ac.x + 14, ac.y + 10), 17, INK, bold=True)
        rules = [f"DENY src {ip}" for ip in self.ip_blocks] + [TOGGLE_ACL[k] for k, _, _ in TOGGLES if k in self.rules_on]
        y = ac.y + 40
        for i, rule in enumerate(rules[:7]):
            text(s, f"{i + 1}. {rule}", (ac.x + 14, y), 14, INK, mono=True)
            y += 22
        text(s, f"{len(rules) + 1}. ALLOW everything else", (ac.x + 14, y), 14, MID, mono=True)
        self.log.draw(s)


# =============================================================== 7. DNS Detective
DNS_POS = {".": (700, 175), "com": (467, 315), "org": (650, 315), "in": (810, 315), "edu": (965, 315),
           "example.com": (400, 455), "cdn.com": (535, 455), "wiki.org": (670, 455), "shop.in": (810, 455),
           "univ.edu": (965, 455)}
RECORDS = {"www.example.com": ("A", "203.0.113.80"), "mail.example.com": ("A", "203.0.113.25"),
           "en.wiki.org": ("A", "198.51.100.40"), "www.shop.in": ("CNAME", "edge.cdn.com"),
           "edge.cdn.com": ("A", "203.0.113.200"), "www.univ.edu": ("A", "198.51.100.90"),
           "lib.univ.edu": ("A", "198.51.100.91")}
DNS_ROUNDS = ["www.example.com", "en.wiki.org", "mail.example.com", "www.shop.in",
              "www.example.com", "www.univ.edu", "lib.univ.edu", "en.wiki.org"]


def zone_of(name):
    return ".".join(name.split(".")[-2:])


class DNSDetective(Game):
    key, title, icon, color, duration = "dns", "DNS Detective", "dns", BLUE, 90
    layer = "Application layer  ·  DNS"
    learn = ["Computers need IP addresses, people use names. DNS turns names into addresses using a HIERARCHY of servers.",
             "The root server points to the TLD server (.com), the TLD points to the domain's authoritative server, which finally gives the answer. Every answer is CACHED for its TTL."]
    howto = ["You are the resolver. Click servers to ask them about the name.",
             "Start at the root, follow the referrals down. Check your cache first (C) - it's instant!",
             "Faster answers score more. Asking the wrong server gets REFUSED (-20)."]
    lessons = ["DNS is a hierarchy: root -> TLD (.com) -> authoritative server, which holds the real record.",
               "Answers and referrals are cached for their TTL, so repeat lookups skip most of the tree.",
               "A CNAME is an alias: the resolver must start again with the new name."]
    thresholds = (350, 700, 900)
    RES = (130, 300)

    def setup(self):
        self.cache = {}
        self.ri = 0
        self.solved = self.cache_hits = self.refused = self.queries = 0
        self.log = PacketLog((330, 525, 740, 160), "Resolver log")
        self.cache_btn = Button((40, 345, 180, 46), "Check cache (C)", YELLOW, 16, key=pygame.K_c)
        self.busy = None
        self.state = "play"
        self.start_round()

    def start_round(self):
        self.name = DNS_ROUNDS[self.ri]
        self.round_t = 0.0
        self.round_q = 0
        self.state = "play"
        self.log.add(f"-- Resolve {self.name}", PURPLE)

    def cached(self, key):
        v = self.cache.get(key)
        return v if v and v[2] > self.t else None

    def put(self, key, value, ttl):
        self.cache[key] = (key, value, self.t + ttl)

    def responsible(self, server):
        return server == "." or self.name.endswith("." + server) or self.name == server

    def use_cache(self):
        if self.busy or self.state != "play":
            return
        rec = self.cached(("REC", self.name))
        if rec:
            self.cache_hits += 1
            self.log.add(f"cache HIT {self.name}", DARK_GREEN)
            self.got_record(rec[1])
        else:
            self.round_t += 0.3
            self.log.add(f"cache miss for {self.name}", MID)
            self.say("Cache miss - nothing stored for this name yet. Ask a server.", ORANGE, 2)

    def query(self, server):
        if self.busy or self.state != "play":
            return
        self.queries += 1
        self.round_q += 1
        if not self.responsible(server):
            resp = ("REFUSED", None)
        elif server == ".":
            resp = ("REF", self.name.split(".")[-1])
        elif "." not in server:
            resp = ("REF", zone_of(self.name))
        else:
            resp = ("ANS", RECORDS[self.name])
        self.busy = dict(server=server, t=0.0, resp=resp)
        self.log.add(f"query {self.name} ? -> {'root' if server == '.' else server}", INK)

    def got_record(self, rec):
        rtype, value = rec
        if rtype == "CNAME":
            self.log.add(f"CNAME: {self.name} is an alias of {value}", ORANGE)
            self.say(f"CNAME! {self.name} is an alias for {value}. Resolve the new name.", ORANGE, 4)
            self.name = value
            return
        pts = max(30, int(170 - 25 * self.round_t))
        self.add_score(pts, (self.RES[0], self.RES[1] - 50))
        self.solved += 1
        self.say(f"Solved! {DNS_ROUNDS[self.ri]} = {value}  ({self.round_t:.1f}s, {self.round_q} queries)", DARK_GREEN, 3)
        self.log.add(f"ANSWER {value}", DARK_GREEN)
        self.state, self.state_t = "solved", 0.0

    def finish_query(self):
        server, (kind, val) = self.busy["server"], self.busy["resp"]
        self.busy = None
        if kind == "REFUSED":
            self.refused += 1
            self.add_score(-20, DNS_POS[server])
            self.log.add(f"REFUSED by {server}: not its zone", DARK_RED)
            self.say(f"{server} doesn't know about {self.name}. Follow the hierarchy!", DARK_RED, 3)
        elif kind == "REF":
            self.put(("NS", val), val, 60)
            self.log.add(f"referral: ask the {val} server (cached 60s)", BLUE)
        else:
            self.put(("REC", self.name), val, 30)
            self.log.add(f"{val[0]} record: {self.name} -> {val[1]} (TTL 30s)", DARK_GREEN)
            self.got_record(val)

    def best_action(self):
        if self.cached(("REC", self.name)):
            return "cache"
        z, tld = zone_of(self.name), self.name.split(".")[-1]
        if self.cached(("NS", z)):
            return z
        if self.cached(("NS", tld)):
            return tld
        return "."

    def on_event(self, e):
        if self.cache_btn.hit(e):
            self.use_cache()
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for srv, (x, y) in DNS_POS.items():
                if pygame.Rect(x - 62, y - 24, 124, 48).collidepoint(e.pos):
                    self.query(srv)
                    break

    def step(self, dt):
        if self.state == "play":
            self.round_t += dt
        if self.busy:
            self.busy["t"] += dt
            if self.busy["t"] >= 0.8:
                self.finish_query()
        if self.state == "solved":
            self.state_t += dt
            if self.state_t > 1.4:
                self.ri += 1
                if self.ri >= len(DNS_ROUNDS):
                    self.add_score(int(self.time_left) * 3)
                    self.finish()
                else:
                    self.start_round()

    def bot(self, dt):
        if self.busy or self.state != "play":
            return
        self.bot_t += dt
        if self.bot_t > 0.6:
            self.bot_t = 0
            a = self.best_action()
            self.use_cache() if a == "cache" else self.query(a)

    def stats(self):
        return [f"Names resolved: {self.solved} of {len(DNS_ROUNDS)}", f"Queries sent: {self.queries}",
                f"Cache hits: {self.cache_hits}", f"Refused queries: {self.refused}"]

    def render(self, s):
        panel(s, (330, 85, 740, 55), WHITE)
        text(s, "Resolve:", (348, 99), 18, MID, bold=True)
        text(s, self.name, (430, 95), 24, INK, bold=True)
        text(s, f"{self.round_t:.1f}s   queries {self.round_q}", (1055, 101), 16, MID, anchor="topright")
        for t in ("com", "org", "in", "edu"):
            pygame.draw.line(s, GREY, DNS_POS["."], DNS_POS[t], 3)
        for z in ("example.com", "cdn.com", "wiki.org", "shop.in", "univ.edu"):
            pygame.draw.line(s, GREY, DNS_POS[z.split(".")[-1]], DNS_POS[z], 3)
        if self.busy:
            sx, sy = DNS_POS[self.busy["server"]]
            k = self.busy["t"] / 0.8
            go = k < 0.5
            f = k * 2 if go else (1 - k) * 2
            x = self.RES[0] + (sx - self.RES[0]) * f
            y = self.RES[1] + (sy - self.RES[1]) * f
            pygame.draw.line(s, shade(PURPLE, 0.5), self.RES, (sx, sy), 2)
            pill(s, "?" if go else ("no!" if self.busy["resp"][0] == "REFUSED" else "!"), (x, y),
                 YELLOW if go else (RED if self.busy["resp"][0] == "REFUSED" else GREEN), 16, anchor="center")
        for srv, (x, y) in DNS_POS.items():
            tier = PURPLE if srv == "." else BLUE if "." not in srv else GREEN
            r = pygame.Rect(x - 62, y - 24, 124, 48)
            hover = r.collidepoint(pygame.mouse.get_pos()) and not self.auto
            panel(s, r.move(0, -3 if hover else 0), shade(tier, 0.55 if hover else 0.3), radius=12, border=3, shadow=4)
            label = "root  ." if srv == "." else ("." + srv if "." not in srv else srv)
            text(s, label, r.move(0, -3 if hover else 0).center, 16, INK, bold=True, anchor="center")
        text(s, "ROOT", (DNS_POS["."][0] + 75, DNS_POS["."][1] - 8), 13, MID, bold=True)
        text(s, "TLD servers", (1065, 350), 13, MID, bold=True, anchor="topright")
        text(s, "Authoritative servers", (1065, 490), 13, MID, bold=True, anchor="topright")
        pygame.draw.circle(s, INK, (self.RES[0], self.RES[1] + 4), 46)
        pygame.draw.circle(s, YELLOW, self.RES, 46)
        pygame.draw.circle(s, INK, self.RES, 46, 4)
        text(s, "You", self.RES, 20, INK, bold=True, anchor="center")
        text(s, "Resolver", (self.RES[0], self.RES[1] - 75), 18, INK, bold=True, anchor="midtop")
        self.cache_btn.draw(s)
        c = panel(s, (30, 405, 285, 280), CREAM)
        text(s, "Cache", (c.x + 14, c.y + 10), 17, INK, bold=True)
        y = c.y + 40
        for key, (_, value, exp) in sorted(self.cache.items(), key=lambda kv: kv[0][0]):
            left = exp - self.t
            if left <= 0:
                continue
            if key[0] == "NS":
                line = f"NS    {key[1]:<18} {int(left):>2}s"
            else:
                line = f"{value[0]:<5} {key[1][:18]:<18} {int(left):>2}s"
            text(s, line, (c.x + 14, y), 13, INK, mono=True)
            y += 21
            if y > c.bottom - 24:
                break
        self.draw_banner(s, (330, 150, 740, 48), "")
        self.log.draw(s)


GAMES = [PacketWrapper, SubnetSniper, RouterRush, LossyLink, CongestionArena, FirewallDefender, DNSDetective]
