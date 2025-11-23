#!/usr/bin/env python3
"""
GitHub Runner IP Tracker
Tracks actual git-runner IPs over time by detecting current IP and maintaining a map.
Map structure: IP -> last_seen_date (allows multiple IPs on the same day).
Removes IPs not seen in 30 days.
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


def load_ip_map(map_file: str) -> Dict[str, str]:
    """
    Load existing IP map from file.

    Args:
        map_file: Path to the map file

    Returns:
        IP map (IP -> last_seen_date) or empty dict if file doesn't exist
    """
    print(f"\nLoading map from {map_file}...", file=sys.stderr)
    try:
        with open(map_file, 'r') as f:
            ip_map = json.load(f)
            print(f"Loaded {len(ip_map)} existing IP entries", file=sys.stderr)
            for ip, date in ip_map.items():
                print(f"  {ip} -> last seen {date}", file=sys.stderr)
            return ip_map
    except FileNotFoundError:
        print("No existing map found, starting fresh", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in map: {e}", file=sys.stderr)
        print("Starting with empty map", file=sys.stderr)
        return {}


def update_current_ip(ip_map: Dict[str, str], current_ip: str) -> Dict[str, str]:
    """
    Update the IP map with the current IP.

    If the IP already exists, updates its last-seen date to today.
    If the IP is new, adds it with today's date.

    Args:
        ip_map: The existing IP map (IP -> last_seen_date)
        current_ip: The current runner IP

    Returns:
        Updated IP map (modified in place but also returned)
    """
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"\nChecking for IP {current_ip}...", file=sys.stderr)

    if current_ip in ip_map:
        existing_date = ip_map[current_ip]
        if existing_date == today:
            print(f"IP {current_ip} already recorded for today", file=sys.stderr)
        else:
            print(f"Updating {current_ip} last-seen from {existing_date} to {today}", file=sys.stderr)
            ip_map[current_ip] = today
    else:
        print(f"Adding new IP {current_ip} with date {today}", file=sys.stderr)
        ip_map[current_ip] = today

    return ip_map


def remove_old_ips(ip_map: Dict[str, str], retention_days: int = 30) -> Dict[str, str]:
    """
    Remove IP entries older than the retention period.

    Args:
        ip_map: The IP map (IP -> last_seen_date)
        retention_days: Number of days to retain IPs (default 30)

    Returns:
        Updated IP map (modified in place but also returned)
    """
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    print(f"\nRemoving IPs not seen in {retention_days} days...", file=sys.stderr)
    ips_to_remove = []
    for ip, date_str in ip_map.items():
        try:
            last_seen = datetime.strptime(date_str, "%Y-%m-%d")
            if last_seen < cutoff_date:
                ips_to_remove.append(ip)
                print(f"  Removing old IP: {ip} (last seen {date_str})", file=sys.stderr)
        except ValueError:
            print(f"Invalid date format for {ip}: {date_str}, keeping entry", file=sys.stderr)

    for ip in ips_to_remove:
        del ip_map[ip]

    if ips_to_remove:
        print(f"Removed {len(ips_to_remove)} old IPs", file=sys.stderr)
    else:
        print(f"No IPs older than {retention_days} days", file=sys.stderr)

    return ip_map


def save_ip_map(ip_map: Dict[str, str], map_file: str) -> None:
    """
    Save the IP map to file.

    Args:
        ip_map: The IP map to save (IP -> last_seen_date)
        map_file: Path to the map file
    """
    print(f"\nSaving map to {map_file}...", file=sys.stderr)
    with open(map_file, 'w') as f:
        json.dump(ip_map, f, indent=2, sort_keys=True)
    print(f"Saved map with {len(ip_map)} IP entries", file=sys.stderr)


def generate_output_files(ip_map: Dict[str, str], output_dir: str = ".") -> None:
    """
    Generate output files based on the IP map.

    Generates:
    1. git-runner-ips.json - Simple list of unique IPs with metadata
    2. git-runner-ips.auto.tfvars - Terraform variable assignments

    Args:
        ip_map: The IP map (IP -> last_seen_date)
        output_dir: Directory for output files
    """
    import os

    # Get all IPs (keys in the map)
    all_ips = sorted(ip_map.keys())

    print(f"\nGenerating output files...", file=sys.stderr)
    print(f"  Total IPs: {len(all_ips)}", file=sys.stderr)
    print(f"  IP list: {', '.join(all_ips)}", file=sys.stderr)

    # Generate git-runner-ips.json
    ips_json_file = os.path.join(output_dir, "git-runner-ips.json")
    with open(ips_json_file, 'w') as f:
        json.dump({
            "git_runner_ips": [f"{ip}/32" for ip in all_ips],
            "count": len(all_ips),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        }, f, indent=2)
    print(f"Saved {ips_json_file}", file=sys.stderr)

    # Generate github-runner-ips.auto.tfvars
    tfvars_file = os.path.join(output_dir, "git-runner-ips.auto.tfvars")
    with open(tfvars_file, 'w') as f:
        f.write("# GitHub Actions Runner IPs\n")
        f.write("# Auto-generated - do not edit manually\n")
        f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write("# This file is automatically loaded by Terraform\n\n")

        # IP list variable
        f.write("git_runner_ips = ")
        if all_ips:
            quoted_ips = [f'  "{ip}/32"' for ip in all_ips]
            f.write("[\n" + ",\n".join(quoted_ips) + "\n]\n\n")
        else:
            f.write("[]\n\n")

        # IP list no cidr variable
        f.write("git_runner_ips_no_cidr = ")
        if all_ips:
            quoted_ips = [f'  "{ip}"' for ip in all_ips]
            f.write("[\n" + ",\n".join(quoted_ips) + "\n]\n\n")
        else:
            f.write("[]\n\n")

        # IP map variable (IP -> last_seen_date)
        f.write("git_runner_ip_map = ")
        if ip_map:
            lines = [f'  "{ip}" = "{date}"' for ip, date in sorted(ip_map.items())]
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

    # Step 2: Load existing IP map
    ip_map = load_ip_map(args.map_file)

    # Step 3: Update map with current IP (add or overwrite)
    ip_map = update_current_ip(ip_map, current_ip)

    # Step 4: Remove old IP entries
    ip_map = remove_old_ips(ip_map, args.retention_days)

    # Step 5: Save updated IP map
    save_ip_map(ip_map, args.map_file)

    # Step 6: Generate output files based on the IP map
    generate_output_files(ip_map, args.output_dir)

    print("\nComplete!", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
