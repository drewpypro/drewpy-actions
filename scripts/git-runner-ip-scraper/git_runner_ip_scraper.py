#!/usr/bin/env python3
"""
GitHub Runner IP Tracker
Tracks actual git-runner IPs over time by detecting current IP and maintaining a map.
Map tracks "last seen date" for each unique IP. Removes IPs not seen in 30 days.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def get_current_ip(test_ip: str = None) -> str:
    """
    Get the current public IPv4 address using multiple fallback services.

    Args:
        test_ip: Optional test IP to use instead of detecting

    Returns:
        Current IP address as string
    """
    if test_ip:
        print(f"Using test IP: {test_ip}", file=sys.stderr)
        return test_ip

    services = [
        "https://ifconfig.me/ip",
        "https://api.ipify.org",
        "https://icanhazip.com",
        "https://checkip.amazonaws.com"
    ]

    print("Detecting current runner IP...", file=sys.stderr)
    for service in services:
        try:
            req = Request(service)
            req.add_header('User-Agent', 'github-runner-ip-tracker/1.0')
            with urlopen(req, timeout=5) as response:
                ip = response.read().decode('utf-8').strip()
                print(f"Current IP: {ip} (via {service})", file=sys.stderr)
                return ip
        except (URLError, HTTPError, TimeoutError) as e:
            print(f"  Failed {service}: {e}", file=sys.stderr)
            continue

    print("Could not determine current IP from any service", file=sys.stderr)
    sys.exit(1)


def check_existing_map(current_ip: str, map_file: str, retention_days: int = 30) -> Dict[str, str]:
    """
    Load existing map, update with current IP, remove old entries, and save.

    Logic:
    1. Load existing map (or start fresh)
    2. Check if current IP exists in map
       - If yes: remove old entry and add with today's date
       - If no: add new entry with today's date
    3. Remove any entries older than retention_days
    4. Save updated map

    Args:
        current_ip: The current runner IP
        map_file: Path to the map file
        retention_days: Number of days to retain IPs (default 30)

    Returns:
        Updated IP map (date -> IP)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    # Load existing map
    print(f"\nLoading map from {map_file}...", file=sys.stderr)
    try:
        with open(map_file, 'r') as f:
            ip_map = json.load(f)
            print(f"Loaded {len(ip_map)} existing entries", file=sys.stderr)
    except FileNotFoundError:
        print("No existing map found, starting fresh", file=sys.stderr)
        ip_map = {}
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in map: {e}", file=sys.stderr)
        print("Starting with empty map", file=sys.stderr)
        ip_map = {}

    # Check if current IP already exists in map
    print(f"\nChecking for IP {current_ip}...", file=sys.stderr)
    existing_date = None
    for date, ip in ip_map.items():
        if ip == current_ip:
            existing_date = date
            break

    if existing_date:
        if existing_date == today:
            print(f"IP {current_ip} already recorded for today", file=sys.stderr)
        else:
            print(f"Updating {current_ip} from {existing_date} to {today}", file=sys.stderr)
            del ip_map[existing_date]
            ip_map[today] = current_ip
    else:
        print(f"Adding new IP {current_ip} for {today}", file=sys.stderr)
        ip_map[today] = current_ip

    # Remove old entries
    print(f"\nRemoving entries older than {retention_days} days...", file=sys.stderr)
    entries_to_remove = []
    for date_str, ip in ip_map.items():
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d")
            if entry_date < cutoff_date:
                entries_to_remove.append(date_str)
                print(f"  Removing old entry: {date_str} -> {ip}", file=sys.stderr)
        except ValueError:
            print(f"Invalid date format: {date_str}, keeping entry", file=sys.stderr)

    for date_str in entries_to_remove:
        del ip_map[date_str]

    if entries_to_remove:
        print(f"Removed {len(entries_to_remove)} old entries", file=sys.stderr)
    else:
        print(f"No entries older than {retention_days} days", file=sys.stderr)

    # Save updated map
    print(f"\nSaving map to {map_file}...", file=sys.stderr)
    with open(map_file, 'w') as f:
        json.dump(ip_map, f, indent=2, sort_keys=True)
    print(f"Saved map with {len(ip_map)} entries", file=sys.stderr)

    return ip_map


def save_output(ip_map: Dict[str, str], output_dir: str = ".") -> None:
    """
    Generate output files from the IP map.

    Generates:
    1. git-runner-ips.json - Simple list of unique IPs with metadata
    2. git-runner-ips.auto.tfvars - Terraform variable assignments

    Args:
        ip_map: The IP map (date -> IP)
        output_dir: Directory for output files
    """
    import os

    # Extract unique IPs
    unique_ips = sorted(set(ip_map.values()))

    print(f"\nGenerating output files...", file=sys.stderr)
    print(f"  Unique IPs: {len(unique_ips)}", file=sys.stderr)
    print(f"  IP list: {', '.join(unique_ips)}", file=sys.stderr)

    # Generate git-runner-ips.json
    ips_json_file = os.path.join(output_dir, "git-runner-ips.json")
    with open(ips_json_file, 'w') as f:
        json.dump({
            "git_runner_ips": [f"{ip}/32" for ip in unique_ips],
            "count": len(unique_ips),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        }, f, indent=2)
    print(f"Saved {ips_json_file}", file=sys.stderr)

    # Generate github-runner-ips.auto.tfvars
    tfvars_file = os.path.join(output_dir, "github-runner-ips.auto.tfvars")
    with open(tfvars_file, 'w') as f:
        f.write("# GitHub Actions Runner IPs\n")
        f.write("# Auto-generated - do not edit manually\n")
        f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write("# This file is automatically loaded by Terraform\n\n")

        # IP list variable
        f.write("git_runner_ips = ")
        if unique_ips:
            quoted_ips = [f'  "{ip}/32"' for ip in unique_ips]
            f.write("[\n" + ",\n".join(quoted_ips) + "\n]\n\n")
        else:
            f.write("[]\n\n")

        # IP map variable
        f.write("git_runner_ip_map = ")
        if ip_map:
            lines = [f'  "{date}" = "{ip}/32"' for date, ip in sorted(ip_map.items())]
            f.write("{\n" + "\n".join(lines) + "\n}\n")
        else:
            f.write("{}\n")

    print(f"Saved {tfvars_file}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Track GitHub Actions runner IPs over time'
    )
    parser.add_argument(
        '--map-file',
        default='git-runner-ip-map.json',
        help='Path to runner IP map file (default: git-runner-ip-map.json)'
    )
    parser.add_argument(
        '--retention-days',
        type=int,
        default=30,
        help='Number of days to retain IPs (default: 30)'
    )
    parser.add_argument(
        '--output-dir',
        default='.',
        help='Directory for output files (default: current directory)'
    )
    parser.add_argument(
        '--test-ip',
        help='Test with a specific IP instead of detecting current IP'
    )

    args = parser.parse_args()

    print("=== GitHub Runner IP Tracker ===", file=sys.stderr)

    # Step 1: Get current IP
    current_ip = get_current_ip(args.test_ip)

    # Step 2: Check/update existing map (handles everything)
    ip_map = check_existing_map(current_ip, args.map_file, args.retention_days)

    # Step 3: Save output files
    save_output(ip_map, args.output_dir)

    print("\nComplete!", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
