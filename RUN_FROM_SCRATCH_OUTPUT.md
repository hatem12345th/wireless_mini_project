# Run From Scratch Transcript

Date: 2026-05-03

Working directory:

```bash
/home/hatem/tps/wireless_project
```

This file records the commands run from this session and the important output.

## Result Summary

Open5GS was already running, and `ogstun` was already up.

The gNB and UE were started from this session without `sudo`. The control-plane registration and PDU session setup succeeded, but the UE could not create `uesimtun0` because creating the TUN interface requires `sudo`.

Main blocker:

```text
[app] [error] TUN interface could not be setup. Permission denied. Please run the UE with 'sudo'
```

So the full successful run must start `nr-ue` with `sudo` in a real terminal.

## 1. Check Current Directory

Command:

```bash
pwd
```

Output:

```text
/home/hatem/tps/wireless_project
```

## 2. Check Current User

Command:

```bash
id
```

Output:

```text
uid=1000(hatem) gid=1000(hatem) groups=1000(hatem),4(adm),20(dialout),24(cdrom),25(floppy),27(sudo),29(audio),30(dip),44(video),46(plugdev),100(users),101(netdev),117(bluetooth),121(wireshark),123(lpadmin),129(scanner),137(kaboxer)
```

## 3. Check Passwordless sudo

Command:

```bash
sudo -n true
```

Output:

```text
sudo: a password is required
```

Meaning:

This session cannot run commands that require `sudo` unless a user enters the password in a real terminal.

## 4. Check Running Open5GS Processes

Command:

```bash
pgrep -af 'open5gs|nr-gnb|nr-ue|tcpdump'
```

Output:

```text
125678 /usr/bin/open5gs-nrfd -c /etc/open5gs/nrf.yaml
125679 /usr/bin/open5gs-scpd -c /etc/open5gs/scp.yaml
125791 /usr/bin/open5gs-amfd -c /etc/open5gs/amf.yaml
125792 /usr/bin/open5gs-smfd -c /etc/open5gs/smf.yaml
125793 /usr/bin/open5gs-upfd -c /etc/open5gs/upf.yaml
125799 /usr/bin/open5gs-ausfd -c /etc/open5gs/ausf.yaml
125800 /usr/bin/open5gs-udmd -c /etc/open5gs/udm.yaml
125803 /usr/bin/open5gs-udrd -c /etc/open5gs/udr.yaml
125820 /usr/bin/open5gs-pcfd -c /etc/open5gs/pcf.yaml
125823 /usr/bin/open5gs-nssfd -c /etc/open5gs/nssf.yaml
125826 /usr/bin/open5gs-bsfd -c /etc/open5gs/bsf.yaml
```

Meaning:

Open5GS core services were already running.

## 5. Check Interfaces

Command:

```bash
ip addr show
```

Output:

```text
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host noprefixroute
       valid_lft forever preferred_lft forever
2: eth0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc fq_codel state DOWN group default qlen 1000
    link/ether ec:79:49:41:60:44 brd ff:ff:ff:ff:ff:ff
3: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    link/ether 8c:55:4a:ca:63:b3 brd ff:ff:ff:ff:ff:ff
    inet 172.19.64.11/24 brd 172.19.64.255 scope global dynamic noprefixroute wlan0
       valid_lft 1987sec preferred_lft 1987sec
    inet6 fe80::9337:7fd3:cc23:c079/64 scope link noprefixroute
       valid_lft forever preferred_lft forever
4: ogstun: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1400 qdisc fq_codel state UP group default qlen 500
    link/none
    inet 10.45.0.1/16 brd 10.45.255.255 scope global ogstun
       valid_lft forever preferred_lft forever
    inet6 2001:db8:cafe::1/48 scope global
       valid_lft forever preferred_lft forever
    inet6 fe80::877d:c560:3b84:ca2/64 scope link stable-privacy proto kernel_ll
       valid_lft forever preferred_lft forever
```

Meaning:

`ogstun` is correctly up with `10.45.0.1/16`.

## 6. Check systemctl Access

Command:

```bash
systemctl is-active open5gs-upfd open5gs-amfd open5gs-smfd
```

Output:

```text
zsh:1: permission denied: systemctl
```

Meaning:

This session cannot manage Open5GS with `systemctl`. Run those service commands manually in a normal terminal.

## 7. Start gNB

Command:

```bash
cd /home/hatem/tps/wireless_project/UERANSIM
./build/nr-gnb -c ../ueransim-open5gs-gnb.yaml
```

Output:

```text
UERANSIM v3.2.8
[2026-05-03 05:32:31.169] [sctp] [info] Trying to establish SCTP connection... (127.0.0.5:38412)
[2026-05-03 05:32:31.178] [sctp] [info] SCTP connection established (127.0.0.5:38412)
[2026-05-03 05:32:31.179] [sctp] [debug] SCTP association setup ascId[198]
[2026-05-03 05:32:31.179] [ngap] [debug] Sending NG Setup Request
[2026-05-03 05:32:31.187] [ngap] [debug] NG Setup Response received
[2026-05-03 05:32:31.187] [ngap] [info] NG Setup procedure is successful
[2026-05-03 05:32:32.143] [rrc] [debug] UE[1] new signal detected
[2026-05-03 05:32:32.144] [rrc] [info] RRC Setup for UE[1]
[2026-05-03 05:32:32.145] [ngap] [debug] Initial NAS message received from UE[1]
[2026-05-03 05:32:32.211] [ngap] [debug] Initial Context Setup Request received
[2026-05-03 05:32:32.425] [ngap] [info] PDU session resource(s) setup for UE[1] count[1]
```

Meaning:

The gNB connected to AMF successfully, and the PDU session setup was reached.

## 8. Start UE Without sudo

Command:

```bash
cd /home/hatem/tps/wireless_project/UERANSIM
./build/nr-ue -c ../ueransim-open5gs-ue.yaml
```

Output:

```text
UERANSIM v3.2.8
[2026-05-03 05:32:31.140] [nas] [info] UE switches to state [MM-DEREGISTERED/PLMN-SEARCH]
[2026-05-03 05:32:32.143] [rrc] [debug] New signal detected for cell[1], total [1] cells in coverage
[2026-05-03 05:32:32.143] [nas] [info] Selected plmn[999/70]
[2026-05-03 05:32:32.144] [rrc] [info] Selected cell plmn[999/70] tac[1] category[SUITABLE]
[2026-05-03 05:32:32.144] [nas] [info] UE switches to state [MM-DEREGISTERED/PS]
[2026-05-03 05:32:32.144] [nas] [info] UE switches to state [MM-DEREGISTERED/NORMAL-SERVICE]
[2026-05-03 05:32:32.144] [nas] [debug] Initial registration required due to [MM-DEREG-NORMAL-SERVICE]
[2026-05-03 05:32:32.144] [nas] [debug] UAC access attempt is allowed for identity[0], category[MO_sig]
[2026-05-03 05:32:32.144] [nas] [debug] Sending Initial Registration
[2026-05-03 05:32:32.144] [nas] [info] UE switches to state [MM-REGISTER-INITIATED]
[2026-05-03 05:32:32.144] [rrc] [debug] Sending RRC Setup Request
[2026-05-03 05:32:32.145] [rrc] [info] RRC connection established
[2026-05-03 05:32:32.145] [rrc] [info] UE switches to state [RRC-CONNECTED]
[2026-05-03 05:32:32.145] [nas] [info] UE switches to state [CM-CONNECTED]
[2026-05-03 05:32:32.170] [nas] [debug] Authentication Request received
[2026-05-03 05:32:32.170] [nas] [debug] Received SQN [000000000081]
[2026-05-03 05:32:32.170] [nas] [debug] SQN-MS [000000000000]
[2026-05-03 05:32:32.183] [nas] [debug] Security Mode Command received
[2026-05-03 05:32:32.183] [nas] [debug] Selected integrity[2] ciphering[0]
[2026-05-03 05:32:32.212] [nas] [debug] Registration accept received
[2026-05-03 05:32:32.212] [nas] [info] UE switches to state [MM-REGISTERED/NORMAL-SERVICE]
[2026-05-03 05:32:32.212] [nas] [debug] Sending Registration Complete
[2026-05-03 05:32:32.212] [nas] [info] Initial Registration is successful
[2026-05-03 05:32:32.212] [nas] [debug] Sending PDU Session Establishment Request
[2026-05-03 05:32:32.212] [nas] [debug] UAC access attempt is allowed for identity[0], category[MO_sig]
[2026-05-03 05:32:32.414] [nas] [debug] Configuration Update Command received
[2026-05-03 05:32:32.425] [nas] [debug] PDU Session Establishment Accept received
[2026-05-03 05:32:32.425] [nas] [info] PDU Session establishment is successful PSI[1]
[2026-05-03 05:32:32.425] [app] [error] TUN interface could not be setup. Permission denied. Please run the UE with 'sudo'
```

Meaning:

The UE can find the cell and register correctly. The failure is only at TUN creation because the UE was not run with `sudo`.

## 9. Check UE Tunnel

Command:

```bash
ip addr show uesimtun0
```

Output:

```text
Device "uesimtun0" does not exist.
```

Meaning:

The UE session reached PDU setup, but no local `uesimtun0` interface was created because `nr-ue` did not have enough privileges.

## 10. Validate tshark Field Names

Command:

```bash
tshark -G fields | rg '^F\s+Message Type\s+gtp\.message\b|^F\s+TEID\s+gtp\.teid\b'
```

Output:

```text
F	Message Type	gtp.message	FT_UINT8	gtp	BASE_HEX	0x0	GTP Message Type
F	TEID	gtp.teid	FT_UINT32	gtp	BASE_HEX_DEC	0x0	Tunnel Endpoint Identifier
```

Meaning:

Use `gtp.message`, not `gtp.message_type`, on this system.

## 11. Validate Python Syntax

Command:

```bash
python3 -m py_compile index.py
```

Output:

```text

```

Meaning:

No syntax errors were found.

## 12. Dry Run `index.py`

Command:

```bash
python3 index.py \
  --gnb-ip 127.0.0.1 \
  --upf-ip 127.0.0.7 \
  --teid 0x00000001 \
  --ue-ip 10.45.0.3 \
  --payload icmp \
  --dry-run
```

Output:

```text
[*] Crafted GTP-U packet
    outer: 127.0.0.1 -> 127.0.0.7:2152
    teid : 0x00000001
    inner: 10.45.0.3 -> 8.8.8.8 (icmp)
###[ IP ]###
  version   = 4
  ihl       = None
  tos       = 0x0
  len       = None
  id        = 1
  flags     =
  frag      = 0
  ttl       = 64
  proto     = udp
  chksum    = None
  src       = 127.0.0.1
  dst       = 127.0.0.7
  \options   \
###[ UDP ]###
     sport     = 2152
     dport     = 2152
     len       = None
     chksum    = None
###[ GTP-U Header ]###
        version   = 1
        PT        = 1
        reserved  = 0
        E         = 0
        S         = 0
        PN        = 0
        gtp_type  = g_pdu
        length    = None
        teid      = 1
###[ IP ]###
           version   = 4
           ihl       = None
           tos       = 0x0
           len       = None
           id        = 1
           flags     =
           frag      = 0
           ttl       = 64
           proto     = icmp
           chksum    = None
           src       = 10.45.0.3
           dst       = 8.8.8.8
           \options   \
###[ ICMP ]###
              type      = echo-request
              code      = 0
              chksum    = None
              id        = 0x0
              seq       = 0x0
              unused    = b''

[*] Dry run requested; not sending.
```

Meaning:

The injector can build the GTP-U packet. The actual `--teid` must still come from a live packet capture when the UE is run with `sudo`.

## 13. Commands To Run Manually For Full Success

Because this session cannot provide an interactive sudo password, run these in real terminals.

Terminal 1:

```bash
cd /home/hatem/tps/wireless_project/UERANSIM
sudo ./build/nr-gnb -c ../ueransim-open5gs-gnb.yaml
```

Terminal 2:

```bash
cd /home/hatem/tps/wireless_project/UERANSIM
sudo ./build/nr-ue -c ../ueransim-open5gs-ue.yaml
```

Terminal 3:

```bash
ip addr show uesimtun0
```

Terminal 4, capture GTP-U:

```bash
cd /home/hatem/tps/wireless_project
sudo tcpdump -i lo -w gtpu_capture.pcap udp port 2152
```

Terminal 5, generate UE traffic:

```bash
ping -I uesimtun0 8.8.8.8
```

Extract the TEID:

```bash
cd /home/hatem/tps/wireless_project
tshark -r gtpu_capture.pcap -Y "gtp" -T fields -e ip.src -e ip.dst -e gtp.teid -e gtp.message
```

Run injection with the captured TEID and actual UE IP:

```bash
sudo python3 index.py \
  --gnb-ip 127.0.0.1 \
  --upf-ip 127.0.0.7 \
  --teid <captured-teid> \
  --ue-ip <uesimtun0-ip> \
  --payload icmp
```

Verify:

```bash
sudo tcpdump -i ogstun -n -v
```
