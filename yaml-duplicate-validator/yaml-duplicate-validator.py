import os
import sys
import yaml
from collections import Counter

def load_yaml_file(filepath):
    with open(filepath, "r") as f:
        return yaml.safe_load(f)

def normalize_ip(ip):
    return ip.strip()

def normalize_url(url):
    url = (url or "").lower()
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url.rstrip("/")

def rules_five_tuple_key(rule, ip_direction_key):
    ips = frozenset(normalize_ip(ip) for ip in rule[ip_direction_key]['ips'])
    protocol = str(rule.get("protocol", "")).lower()
    port = str(rule.get("port", "")).strip()
    appid = str(rule.get("appid", "")).lower()
    url = normalize_url(rule.get("url", ""))
    return (ips, protocol, port, appid, url)

def highlight_rule(rule, ip_direction_key, highlight_ips=None, highlight_all=False):
    lines = []
    lines.append(f"    - request_id: {rule.get('request_id')}")
    lines.append(f"      {ip_direction_key}:")
    lines.append(f"        ips:")
    for ip in rule[ip_direction_key]['ips']:
        prefix = ">>" if highlight_all or (highlight_ips and ip in highlight_ips) else "  "
        lines.append(f"{prefix}          - {ip}")
    for key in ["protocol", "port", "appid", "url"]:
        val = rule.get(key)
        prefix = ">>" if highlight_all else "  "
        lines.append(f"{prefix}      {key}: {val}")
    return "\n".join(lines)

def find_duplicate_ips_within_rule(rules, ip_direction_key):
    result = []
    for idx, rule in enumerate(rules):
        ips = rule[ip_direction_key]['ips']
        dup_ips = [ip for ip, c in Counter(ips).items() if c > 1]
        if dup_ips:
            block = []
            block.append(f"### Duplicate detected within requested policy rule {idx+1}")
            block.append("```yaml")
            block.append(highlight_rule(rule, ip_direction_key, set(dup_ips)))
            block.append("```")
            result.append("\n".join(block))
    return result

def find_five_tuple_dupes_within(rules, ip_direction_key):
    result = []
    seen = {}
    for i, rule_i in enumerate(rules):
        key = rules_five_tuple_key(rule_i, ip_direction_key)
        if key in seen:
            j = seen[key]
            block = []
            block.append(f"### Duplicate detected between requested policy rule {j+1} and rule {i+1}")
            block.append("")
            block.append(f"#### Requested policy rule {j+1}")
            block.append("```yaml")
            block.append(highlight_rule(rules[j], ip_direction_key, highlight_all=True))
            block.append("```")
            block.append("")
            block.append(f"#### Requested policy rule {i+1}")
            block.append("```yaml")
            block.append(highlight_rule(rule_i, ip_direction_key, highlight_all=True))
            block.append("```")
            result.append("\n".join(block))
        else:
            seen[key] = i
    return result

def find_per_ip_5tuple_dupes_within(rules, ip_direction_key):
    result = []
    seen = {}
    for idx, rule in enumerate(rules):
        proto = str(rule.get("protocol", "")).lower()
        port = str(rule.get("port", "")).strip()
        appid = str(rule.get("appid", "")).lower()
        url = normalize_url(rule.get("url", ""))
        for ip in rule[ip_direction_key]['ips']:
            key = (normalize_ip(ip), proto, port, appid, url)
            if key in seen:
                for other_idx in seen[key]:
                    if idx == other_idx:
                        continue
                    if set(rule[ip_direction_key]['ips']) != set(rules[other_idx][ip_direction_key]['ips']):
                        pair = tuple(sorted([idx, other_idx]))
                        block = []
                        block.append(f"### Duplicate detected between requested policy rule {other_idx+1} and rule {idx+1}")
                        block.append("")
                        block.append(f"#### Requested policy rule {other_idx+1}")
                        block.append("```yaml")
                        block.append(highlight_rule(rules[other_idx], ip_direction_key, highlight_ips={ip}))
                        block.append("```")
                        block.append("")
                        block.append(f"#### Requested policy rule {idx+1}")
                        block.append("```yaml")
                        block.append(highlight_rule(rule, ip_direction_key, highlight_ips={ip}))
                        block.append("```")
                        result.append("\n".join(block))
                seen[key].append(idx)
            else:
                seen[key] = [idx]
    return result

def find_five_tuple_dupes_between(req_rules, exist_rules, ip_direction_key):
    result = []
    matched_req = set()
    matched_exist = set()
    for i, req_rule in enumerate(req_rules):
        req_key = rules_five_tuple_key(req_rule, ip_direction_key)
        for j, exist_rule in enumerate(exist_rules):
            exist_key = rules_five_tuple_key(exist_rule, ip_direction_key)
            if req_key == exist_key:
                matched_req.add(i)
                matched_exist.add(j)
                block = []
                block.append(f"### Duplicate detected between requested policy rule {i+1} and existing policy rule {j+1}")
                block.append("")
                block.append(f"#### Requested policy rule {i+1}")
                block.append("```yaml")
                block.append(highlight_rule(req_rule, ip_direction_key, highlight_all=True))
                block.append("```")
                block.append("")
                block.append(f"#### Existing policy rule {j+1}")
                block.append("```yaml")
                block.append(highlight_rule(exist_rule, ip_direction_key, highlight_all=True))
                block.append("```")
                result.append("\n".join(block))
    return result

def find_per_ip_5tuple_dupes_between(req_rules, exist_rules, ip_direction_key):
    result = []
    emitted = set()
    for i, req_rule in enumerate(req_rules):
        ips_req = set(normalize_ip(ip) for ip in req_rule[ip_direction_key]['ips'])
        for j, exist_rule in enumerate(exist_rules):
            ips_exist = set(normalize_ip(ip) for ip in exist_rule[ip_direction_key]['ips'])
            common_ips = ips_req & ips_exist
            if not common_ips:
                continue
            req_key = rules_five_tuple_key(req_rule, ip_direction_key)
            exist_key = rules_five_tuple_key(exist_rule, ip_direction_key)
            if req_key == exist_key:
                continue
            pair = (i, j)
            if pair in emitted:
                continue
            emitted.add(pair)
            block = []
            block.append(f"### Duplicate detected between requested policy rule {i+1} and existing policy rule {j+1}")
            block.append("")
            block.append(f"#### Requested policy rule {i+1}")
            block.append("```yaml")
            block.append(highlight_rule(req_rule, ip_direction_key, common_ips))
            block.append("```")
            block.append("")
            block.append(f"#### Existing policy rule {j+1}")
            block.append("```yaml")
            block.append(highlight_rule(exist_rule, ip_direction_key, common_ips))
            block.append("```")
            result.append("\n".join(block))
    return result

def main():
    try:
        print("DEBUG: yaml-duplicate-validator starting...", file=sys.stderr)

        if len(sys.argv) < 2:
            print("Usage: python yaml-duplicate-validator.py <request_file> [existing_file]", file=sys.stderr)
            sys.exit(2)

        request_file = sys.argv[1]
        existing_file = sys.argv[2] if len(sys.argv) > 2 else None

        print(f"DEBUG: request_file={request_file}", file=sys.stderr)
        if existing_file:
            print(f"DEBUG: existing_file={existing_file}", file=sys.stderr)

        if not os.path.isfile(request_file):
            print(f"ERROR: Cannot find request_file {request_file}", file=sys.stderr)
            sys.exit(3)

        request_policy = load_yaml_file(request_file)
        service_type = request_policy.get("security_group", {}).get("serviceType", "")
        ip_direction_key = "source" if service_type == "privatelink-consumer" else "destination"
        rules = request_policy.get("rules", [])

        print(f"DEBUG: Loaded {len(rules)} rules from {request_file}", file=sys.stderr)

        sections_within = {}
        sections_between = {}

        key_within_5tuple = "Full 5-tuple rule duplicate within requested policy"
        key_within_per_ip = "Per-IP 5-tuple duplicate within requested policy"
        key_within_dupe_ips = "Duplicate IPs within a single rule"
        key_between_5tuple = "Full 5-tuple duplicate between requested and existing policy"
        key_between_per_ip = "Per-IP 5-tuple duplicates across files"

        within_5tuple = find_five_tuple_dupes_within(rules, ip_direction_key)
        if within_5tuple:
            sections_within[key_within_5tuple] = within_5tuple
        within_per_ip = find_per_ip_5tuple_dupes_within(rules, ip_direction_key)
        if within_per_ip:
            sections_within[key_within_per_ip] = within_per_ip
        within_dupe_ips = find_duplicate_ips_within_rule(rules, ip_direction_key)
        if within_dupe_ips:
            sections_within[key_within_dupe_ips] = within_dupe_ips

        exist_rules = []
        if existing_file and os.path.isfile(existing_file):
            existing_policy = load_yaml_file(existing_file)
            exist_rules = existing_policy.get("rules", [])
            between_5tuple = find_five_tuple_dupes_between(rules, exist_rules, ip_direction_key)
            if between_5tuple:
                sections_between[key_between_5tuple] = between_5tuple
            between_per_ip = find_per_ip_5tuple_dupes_between(rules, exist_rules, ip_direction_key)
            if between_per_ip:
                sections_between[key_between_per_ip] = between_per_ip

        output_lines = []

        if sections_within:
            output_lines.append("# ❌ Duplicates detected within requested policy")
            for header in [
                key_within_5tuple,
                key_within_per_ip,
                key_within_dupe_ips,
            ]:
                if header in sections_within:
                    output_lines.append("")  
                    output_lines.append(f"## {header}")
                    for block in sections_within[header]:
                        output_lines.append("")
                        output_lines.append(block)

        if sections_between:
            if output_lines:
                output_lines.append("")
            output_lines.append("# ❌ Duplicates detected between requested and existing policy")
            for header in [
                key_between_5tuple,
                key_between_per_ip,
            ]:
                if header in sections_between:
                    output_lines.append("")
                    output_lines.append(f"## {header}")
                    for block in sections_between[header]:
                        output_lines.append("")
                        output_lines.append(block)

        if output_lines:
            print("\n".join(output_lines).rstrip())
            sys.exit(2)
        else:
            print("💦 No Duplicates detected!")
            sys.exit(0)
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
