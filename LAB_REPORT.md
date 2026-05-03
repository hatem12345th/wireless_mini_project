# GTP-U Tunneling Exploit Lab Report

## Scope

All work is for an isolated local Open5GS/UERANSIM lab. No production or public mobile network infrastructure was targeted.

## Environment

- Host: Kali Linux 6.12.20-amd64
- Open5GS: 2.7.7
- UERANSIM: 3.2.8, built locally in `UERANSIM/`
- UPF GTP-U address: `127.0.0.7:2152`
- UE subnet: `10.45.0.0/16`
- Lab IMSI: `999700000000001`

## Completed Setup

- Built UERANSIM locally.
- Added UERANSIM gNB and UE config templates:
  - `ueransim-open5gs-gnb.yaml`
  - `ueransim-open5gs-ue.yaml`
- Inserted the lab subscriber into MongoDB with `add_lab_subscriber.js`.
- Replaced the original hardcoded Scapy proof of concept with an argument-driven helper in `index.py`.
- Verified `index.py` builds a valid GTP-U packet in dry-run mode.

## Current Blocker

The exploit was not confirmed yet because Open5GS and UERANSIM were not running, `ogstun` had no IPv4 address, and this Codex session cannot run `sudo` commands that require an interactive password.

The next required step is to start Open5GS, bring up `ogstun`, start UERANSIM, and capture a live TEID.

## Evidence To Capture

### TEID Capture

Command:

```bash
sudo tcpdump -i any -w gtpu_capture.pcap udp port 2152
tshark -r gtpu_capture.pcap -Y "gtp" -T fields \
  -e ip.src -e ip.dst -e gtp.teid -e gtp.message_type
```

Result:

```text
<paste tshark output here>
```

### Injection Dry Run

Command:

```bash
sudo python3 index.py --gnb-ip <captured-gnb-ip> --upf-ip 127.0.0.7 \
  --teid <captured-teid> --ue-ip <captured-ue-ip> --payload icmp --dry-run
```

Result:

```text
<paste packet structure here>
```

### Decapsulation Confirmation

Command:

```bash
sudo tcpdump -i ogstun -n -v
```

Result:

```text
<paste ogstun output showing inner packet source as UE IP>
```

## Expected Finding

If the captured TEID is valid, Open5GS UPF should decapsulate the injected GTP-U packet and emit the inner IP packet on `ogstun` as if it originated from the UE PDU session.

## Mitigations

- Enable IPsec or equivalent authenticated transport on N3.
- Restrict UDP/2152 at the UPF to known gNB addresses.
- Isolate N3 on a dedicated VLAN, VRF, or host network policy.
- Use high-entropy TEIDs to reduce guessing risk.
- Deploy GTP-aware filtering and anomaly detection.
- Enforce UPF source validation by binding TEIDs to expected outer gNB addresses.
