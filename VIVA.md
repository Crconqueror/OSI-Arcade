# CN Arcade - Viva Sheet

## The project in one paragraph
CN Arcade is a single-player game with seven mini-games, each demonstrating one Computer Networks concept,
ordered roughly along the TCP/IP stack. It is written in Python with pygame. Instead of using real sockets
(which depend on the network at demo time), it contains its own **network simulator** that models queuing,
transmission rate, propagation delay and packet loss, and the games run real protocol logic on top of it:
Go-Back-N, TCP Reno congestion control, Dijkstra routing, first-match ACLs and iterative DNS resolution.

**Why single-player / simulated?** Repeatable demos, no dependency on lab Wi-Fi, and we can *control*
delay and loss to show their effects, which you can't do on a real network on demand.

---

## 1. Packet Wrapper - encapsulation
**Concept:** Data moves down the stack; each layer adds a header. Transport adds ports (TCP/UDP),
Internet adds source/destination IP, Link adds source/destination MAC plus a trailer (FCS).
**Key insight shown:** destination **IP = final host**, destination **MAC = next hop**. For a remote server
the frame goes to the *gateway's* MAC; for a device on the same subnet (printer, lab server) it goes directly.
**Likely questions**
- *Why does the MAC change at each hop but the IP doesn't?* MAC addresses are only meaningful on one LAN segment; each router rewrites the frame for the next link, while the IP header identifies the end hosts.
- *How does the laptop find the gateway's MAC?* ARP: it broadcasts "who has 192.168.1.1?" and caches the reply.
- *Why UDP for DNS and voice?* DNS is a single small request/response (a handshake would double the time); for live audio a retransmitted packet arrives too late to be useful.
- *What is the FCS?* Frame Check Sequence, a CRC used to detect corrupted frames.

## 2. Subnet Sniper - IP addressing
**Concept:** A /n prefix means n network bits and 32-n host bits.
Network address = host bits all 0; broadcast = all 1; usable hosts = 2^(32-n) - 2.
**Worked example:** 192.168.10.77/26 - mask 255.255.255.192, block size 64, so the subnet is
192.168.10.64 to .127; network .64, broadcast .127, first host .65, 62 usable hosts.
**Likely questions**
- *Why subtract 2?* The network and broadcast addresses can't be assigned to hosts.
- *Why subnet at all?* Smaller broadcast domains, better security separation, efficient address use (VLSM).
- *How does a host decide if a destination is local?* It ANDs both IPs with its mask; if the results match, it delivers directly, otherwise it sends to the gateway (this connects to game 1).

## 3. Router Rush - routing
**Concept:** Link-state routing (like OSPF): every router knows the full topology and runs **Dijkstra**
to find the lowest-cost path. Costs here are delays, so the cheapest path is not always the fewest hops.
When a link fails, the change is **flooded** to all routers and each recomputes its table (**convergence**).
**TTL** limits hops so packets can't loop forever. The routing-table peek shows *next hop + cost*:
real routers only store the next hop, not the whole path.
**Likely questions**
- *Link-state vs distance-vector?* Link-state: every router has the full map and runs Dijkstra (OSPF). Distance-vector: routers only share distance tables with neighbours and use Bellman-Ford (RIP); slower to converge and can suffer **count-to-infinity**.
- *Dijkstra's complexity?* O((V + E) log V) with a priority queue (that's what `heapq` does in the code).
- *What happens when TTL hits 0?* The router drops the packet and sends an ICMP "Time Exceeded" back (this is how traceroute works).

## 4. Lossy Link - reliable delivery (Go-Back-N)
**Concept:** Reliability over an unreliable network using **sequence numbers, cumulative ACKs and a timer**.
The connection starts with a **3-way handshake** (SYN, SYN-ACK, ACK).
The sender keeps up to N unacknowledged packets in flight (the **window**); on timeout it resends the whole window.
**What the 3 phases prove** (measured with a parameter sweep of the game itself):
| Phase | Best setting | Why |
|---|---|---|
| Clear skies (0.4 s delay, 2% loss) | big window (~10), short timeout | keep the pipe full |
| Stormy (25% loss) | small window (3-4) | each loss resends the whole window; big windows go **negative** |
| Satellite (1.5 s delay) | window 16, timeout 4 s | window must be ~ rate x RTT; a timeout shorter than the RTT causes useless resends |
**Likely questions**
- *Go-Back-N vs Selective Repeat?* SR buffers out-of-order packets and resends only the lost one: more efficient on lossy links, but needs receiver buffers and individual ACKs.
- *How is RTT measured?* From ACKs of packets sent once. Retransmitted packets are excluded (**Karn's algorithm**), because you can't tell which copy the ACK is for. This is in the code.
- *Why is the ideal window rate x RTT?* That's the **bandwidth-delay product**: the number of packets that fit "in the pipe" at once.

## 5. Congestion Arena - congestion control
**Concept:** Three flows share one bottleneck (12 packets/s, 16-packet router queue). The two bots run
**TCP Reno-style** control: **slow start** (cwnd +1 per ACK, doubling per RTT) until ssthresh, then
**additive increase** (+1 per RTT) and **multiplicative decrease** (halve on loss), giving the **AIMD sawtooth**.
The player does the same by hand. **Jain's fairness index** = (sum x)^2 / (n x sum x^2): 1.0 is perfectly fair.
**Likely questions**
- *Flow control vs congestion control?* Flow control protects the *receiver* (advertised window); congestion control protects the *network* (cwnd). The sender uses the smaller of the two.
- *Why does AIMD converge to fairness?* Additive increase raises every flow equally; multiplicative decrease cuts bigger flows by more, so they move toward equal shares.
- *What is bufferbloat?* Very large queues: few drops, but huge delay, which you can see in the queue meter.
- *Reno vs CUBIC/BBR?* CUBIC grows the window as a cubic function of time since the last loss (default in Linux); BBR models bandwidth and RTT instead of reacting to loss.

## 6. Firewall Defender - packet filtering
**Concept:** A stateless packet filter checks header fields (source IP, protocol, destination port, TCP flags)
against an **ordered ACL**; the **first match wins**, with a default rule at the end.
**Waves and the right defence:**
| Attack | What it looks like | Right rule |
|---|---|---|
| Port scan | one source IP, SYNs to many ports | block that source IP |
| Brute force | many IPs hitting SSH (22) / Telnet (23) | block the *service* from outside (allow internal 10.x admin) |
| SYN flood | huge SYN rate from spoofed random IPs | **rate limiting** (IP blocks are useless against spoofing) |
Blocking all TCP scores far below zero: it stops the attack *and* every real user.
**Likely questions**
- *Stateless vs stateful firewall?* Stateful firewalls track connections (e.g. allow replies to connections you opened). Ours is stateless.
- *How do servers survive SYN floods?* SYN cookies (no state stored until the handshake completes), rate limiting, upstream filtering.
- *Default allow vs default deny?* Real firewalls use default **deny** for inbound traffic; we use default allow to make the game possible.

## 7. DNS Detective - name resolution
**Concept:** The resolver resolves names **iteratively**: root server, then the TLD server (.com), then the
**authoritative** server for the domain, which returns the record. Referrals and answers are **cached for
their TTL**, so later lookups skip steps. A **CNAME** is an alias that restarts resolution with a new name.
**Likely questions**
- *Iterative vs recursive?* Your laptop asks its resolver *recursively* ("give me the final answer"); the resolver then asks root/TLD/authoritative *iteratively* (each returns a referral). The game shows the resolver's side.
- *Why TTLs?* A trade-off: long TTLs mean faster lookups and less load; short TTLs mean changes spread quickly.
- *What transport does DNS use?* UDP port 53 normally; TCP for large responses and zone transfers.
- *Record types?* A (IPv4), AAAA (IPv6), CNAME (alias), MX (mail server), NS (name server), TXT.

---

## Code questions
- **How is the simulator built?** `Link` = FIFO queue + serialisation at `rate` + propagation `delay` + random `loss`, using a heap (priority queue) of in-flight packets ordered by arrival time. It's a small discrete-event simulation stepped every frame.
- **How does demo mode work?** Every game has a `bot()` method that plays by calling the same functions as mouse/keyboard input, so the demo exercises the real game logic.
- **How were the star thresholds chosen?** By running each game's bot for its full length over several random seeds and measuring the scores, then checking that bad strategies (e.g. "block all TCP") score low.
- **Limitations:** simulated rather than real packets; Go-Back-N rather than full TCP; stateless firewall; simplified DNS (no DNSSEC, no real root servers).
