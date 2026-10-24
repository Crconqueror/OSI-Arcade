# CN Arcade

Seven single-player mini-games that each turn one Computer Networks concept into something you can play.
Everything runs on one machine with a built-in network simulator, so no Wi-Fi or second computer is needed.

| # | Game | Layer | Concepts |
|---|---|---|---|
| 1 | **Packet Wrapper** | All layers | Encapsulation, TCP vs UDP, ports, IP vs MAC addressing, default gateway |
| 2 | **Subnet Sniper** | Network | IP addressing, CIDR prefixes, masks, network/broadcast address, usable hosts |
| 3 | **Router Rush** | Network | Routing, link costs, Dijkstra / link-state, link failure & convergence, TTL |
| 4 | **Lossy Link** | Transport | 3-way handshake, sequence numbers, ACKs, timeouts, Go-Back-N sliding window, RTT |
| 5 | **Congestion Arena** | Transport | Congestion window, slow start, AIMD, router queues, packet loss, fairness (Jain's index) |
| 6 | **Firewall Defender** | Security | Packet filtering, ACLs (first match wins), port scan, brute force, SYN flood, rate limiting |
| 7 | **DNS Detective** | Application | DNS hierarchy (root, TLD, authoritative), iterative resolution, caching & TTL, CNAME |

Every game starts with a **"big idea" card**, ends with a **"what you just saw" summary**, and awards 1 to 3 stars.
**Demo mode** plays all seven games automatically (about 4 minutes), which is handy for presentations.
Press **S** anywhere to toggle **slow mode** (0.2x speed) to explain what is happening on screen; change `SLOW_SPEED` in `main.py` to adjust it.

## Setup (macOS)
1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/) (the installer includes everything needed).
2. Install pygame:
   ```bash
   python3 -m pip install pygame
   ```
3. Run:
   ```bash
   python3 main.py
   ```
Works the same on Windows (`python` instead of `python3`) and Linux.

## Controls
| Where | Keys |
|---|---|
| Menu | Click a card or press **1-7** · **D** demo mode · **S** slow mode · **Esc** quit |
| Any game | **P** pause · **S** slow mode (0.2x speed) · **Esc** back to menu |
| Packet Wrapper | Click a card or **1/2/3** |
| Subnet Sniper | Click a balloon or **1-4** |
| Router Rush | Click routers in order · **Backspace** undo · **T** peek at routing table |
| Lossy Link | **Up/Down** window size · **Left/Right** timeout |
| Congestion Arena | Hold **Up** to grow cwnd · **Down** to halve it |
| Firewall Defender | Click a packet to block its IP · click rule switches |
| DNS Detective | Click servers to query them · **C** check cache |

## Project structure
| File | Contents |
|---|---|
| `main.py` | The arcade: menu, learn cards, results, pause, demo mode, saved scores |
| `games.py` | The seven mini-games (each has its own auto-play bot for demo mode) |
| `engine.py` | Cartoon UI toolkit + the network simulator (`Packet`, `Link`) |
| `VIVA.md` | Concept-by-concept explanation and likely viva questions |

### How the network simulator works
`engine.Link` models a real link in three stages:
1. **Queue:** packets wait in a FIFO buffer; if it is full the packet is dropped (*tail drop*, like a congested router).
2. **Transmission:** packets leave one at a time at the link's `rate` (packets/second).
3. **Propagation:** each packet then takes `delay` seconds to arrive, and may be lost at random with probability `loss`.

Lossy Link and Congestion Arena run real protocol logic (Go-Back-N, TCP Reno-style AIMD) on top of it.
Router Rush runs Dijkstra's algorithm on a live topology.

Best scores are saved to `scores.json` (ignored by git).
