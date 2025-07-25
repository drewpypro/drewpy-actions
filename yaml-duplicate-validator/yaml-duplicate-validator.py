import os
import sys
import yaml
import base64
import requests
from collections import defaultdict

def load_yaml_file(filepath):
    try:
        with open(filepath, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML file {filepath}: {e}")
        write_github_output('error_type', 'load_error')
        sys.exit(2)

def format_rule_yaml(rule, ip_direction_key, highlight_ips=None, highlight_all_fields=False):
    lines = []
    lines.append(f"    - request_id: {rule.get('request_id')}")
    lines.append(f"      {ip_direction_key}:")
    lines.append(f"        ips:")
    for nip in rule[ip_direction_key]['ips']:
        if highlight_all_fields or (highlight_ips and nip in highlight_ips):
            lines.append(f">>          - {nip}")
        else:
            lines.append(f"            - {nip}")
    for key in ['protocol', 'port', 'appid', 'url']:
        value = rule.get(key)
        if highlight_all_fields:
            lines.append(f">>      {key}: {value}")
        else:
            lines.append(f"        {key}: {value}")
    return "\n".join(lines)

def extract_5tuple(rule, ip_direction_key):
    keys = []
    for ip in rule[ip_direction_key]["ips"]:
        keys.append((
            ip,
            rule["protocol"],
            str(rule["port"]),
            rule["appid"],
            rule["url"]
        ))
    return keys

def full_tuple_key(rule, ip_direction_key):
    return (
        tuple(rule[ip_direction_key]["ips"]),
        rule["protocol"],
        str(rule["port"]),
        rule["appid"],
        rule["url"]
    )

def check_duplicates_within_request(policy, ip_direction_key):
    rules = policy.get("rules", [])
    dupe_ip_map = defaultdict(set)
    dupe_full_tuple = set()
    found = False
    matches = defaultdict(set)

    full_tuple_to_idxs = defaultdict(list)
    for idx, rule in enumerate(rules):
        key = full_tuple_key(rule, ip_direction_key)
        full_tuple_to_idxs[key].append(idx)
    for idxs in full_tuple_to_idxs.values():
        if len(idxs) > 1:
            found = True
            for i in idxs:
                for j in idxs:
                    if i != j:
                        matches[i].add(j)
                dupe_full_tuple.add(i)

    tuple_to_rules = defaultdict(list)
    for idx, rule in enumerate(rules):
        for ip in rule[ip_direction_key]["ips"]:
            tup = (ip, rule["protocol"], str(rule["port"]), rule["appid"], rule["url"])
            tuple_to_rules[tup].append(idx)
    for tup, idxs in tuple_to_rules.items():
        if len(idxs) > 1:
            found = True
            for i in idxs:
                for j in idxs:
                    if i != j:
                        matches[i].add(j)
                dupe_ip_map[i].add(tup[0])

    if found:
        out = ["🏛️ Duplicates detected in submitted policy\n"]
        already_output = set()
        for idx in range(len(rules)):
            if idx in already_output:
                continue
            highlight_all = idx in dupe_full_tuple
            highlight_ips = set(rules[idx][ip_direction_key]['ips']) if highlight_all else dupe_ip_map[idx]
            has_any_highlight = highlight_all or highlight_ips

            if idx in matches and matches[idx]:
                match_indices = sorted(matches[idx])
                header = (
                    f"# Submitted policy rule index {idx+1} matches submitted policy index "
                    + ", ".join([f"{j+1}" for j in match_indices])
                )
                out.append(header)
            elif has_any_highlight:
                header = f"# Submitted policy rule index {idx+1} (duplicate values within rule)"
                out.append(header)
            else:
                continue

            out.append("```yaml")
            out.append(format_rule_yaml(
                rules[idx],
                ip_direction_key,
                highlight_ips,
                highlight_all_fields=highlight_all
            ))
            out.append("```")
            already_output.add(idx)
        return True, "\n".join(out)
    return False, ""

def check_duplicates_against_existing(request_policy, existing_policy, ip_direction_key, existing_filename):
    existing_map = defaultdict(list)
    for idx, rule in enumerate(existing_policy.get("rules", [])):
        for key in extract_5tuple(rule, ip_direction_key):
            existing_map[key].append((idx, rule))

    existing_full_tuples = defaultdict(list)
    for idx, rule in enumerate(existing_policy.get("rules", [])):
        existing_full_tuples[full_tuple_key(rule, ip_direction_key)].append(idx)
    submitted_full_tuples = defaultdict(list)
    for idx, rule in enumerate(request_policy.get("rules", [])):
        submitted_full_tuples[full_tuple_key(rule, ip_direction_key)].append(idx)

    submitted_dupe = defaultdict(set)
    existing_dupe = defaultdict(set)
    submitted_blocks = set()
    existing_blocks = set()
    highlight_all_fields_sub = set()
    highlight_all_fields_exist = set()

    submitted_matches = defaultdict(set)

    for sub_key, sub_idxs in submitted_full_tuples.items():
        if sub_key in existing_full_tuples:
            for sidx in sub_idxs:
                highlight_all_fields_sub.add(sidx)
                submitted_blocks.add(sidx)
            for eidx in existing_full_tuples[sub_key]:
                highlight_all_fields_exist.add(eidx)
                existing_blocks.add(eidx)
            for sidx in sub_idxs:
                for eidx in existing_full_tuples[sub_key]:
                    submitted_matches[sidx].add(eidx)

    for req_idx, rule in enumerate(request_policy.get("rules", [])):
        for key in extract_5tuple(rule, ip_direction_key):
            if key in existing_map:
                submitted_dupe[req_idx].add(key[0])
                submitted_blocks.add(req_idx)
                for ex_idx, _ in existing_map[key]:
                    existing_dupe[ex_idx].add(key[0])
                    existing_blocks.add(ex_idx)
                    submitted_matches[req_idx].add(ex_idx)

    if submitted_blocks or existing_blocks:
        out = [f"\n\n🏛️ Duplicates detected in existing policy {existing_filename}\n"]
        for idx in sorted(submitted_blocks):
            rule = request_policy["rules"][idx]
            highlight_ips = set(rule[ip_direction_key]["ips"]) if idx in highlight_all_fields_sub else submitted_dupe[idx]
            highlight_all = idx in highlight_all_fields_sub
            if idx in submitted_matches and submitted_matches[idx]:
                match_indices = ", ".join([f"{i+1}" for i in sorted(submitted_matches[idx])])
                out.append(f"# Submitted policy rule index {idx+1} matches existing policy rule index {match_indices}")
            else:
                out.append(f"# Submitted policy rule index {idx+1}")
            out.append("```yaml")
            out.append(format_rule_yaml(
                rule,
                ip_direction_key,
                highlight_ips,
                highlight_all_fields=highlight_all
            ))
            out.append("```")
        for idx in sorted(existing_blocks):
            rule = existing_policy["rules"][idx]
            highlight_ips = set(rule[ip_direction_key]["ips"]) if idx in highlight_all_fields_exist else existing_dupe[idx]
            highlight_all = idx in highlight_all_fields_exist
            out.append(f"# Existing policy rule index {idx+1}")
            out.append("```yaml")
            out.append(format_rule_yaml(
                rule,
                ip_direction_key,
                highlight_ips,
                highlight_all_fields=highlight_all
            ))
            out.append("```")
        return True, "\n".join(out), submitted_blocks
    return False, "", set()

def write_github_output(key, value):
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, 'a') as fh:
            fh.write(f"{key}={value}\n")

def main():
    # Load required env vars and args
    repo = os.getenv("repo")
    token = os.getenv("token")
    existing_policy_filelist = os.getenv("existing_policy")
    if not existing_policy_filelist and len(sys.argv) > 2:
        existing_policy_filelist = sys.argv[2]

    request_file = os.getenv("created_yaml")
    if not request_file and len(sys.argv) > 1:
        request_file = sys.argv[1]
    if not request_file:
        print("Missing request policy filename (env var 'created_yaml' or argv[1])")
        write_github_output('error_type', 'missing_var')
        sys.exit(4)

    request_policy = load_yaml_file(request_file)
    if request_policy is None:
        print("Failed to load or parse request policy YAML.")
        sys.exit(2)
    
    service_type = request_policy["security_group"].get("serviceType", "")
    ip_direction_key = "source" if service_type == "privatelink-consumer" else "destination"

    # Check duplicates within request
    has_within_dupe, within_output = check_duplicates_within_request(request_policy, ip_direction_key)

    # Check duplicates against ALL existing policies
    has_ext_dupe = False
    ext_output_list = []
    dupe_indices = set()
    if existing_policy_filelist:
        with open(existing_policy_filelist) as f:
            files = f.read().splitlines()
            for file in files:
                # Try local first
                local_path = f'policies/{file}'
                if os.path.exists(local_path):
                    existing_policy = load_yaml_file(local_path)
                else:
                    if repo and token:
                        existing_policy = fetch_policy_file_from_github(repo, file, token)
                    else:
                        existing_policy = None
                if not existing_policy:
                    continue
                has_dupe, ext_output, ext_dupes = check_duplicates_against_existing(
                    request_policy, existing_policy, ip_direction_key, file
                )
                if has_dupe:
                    has_ext_dupe = True
                    ext_output_list.append(ext_output)
                    dupe_indices.update(ext_dupes)

    output_printed = False
    if has_within_dupe:
        print(within_output)
        output_printed = True
    if has_ext_dupe:
        print("\n".join(ext_output_list))
        output_printed = True

    write_github_output('duplicates_within', "true" if has_within_dupe else "false")
    write_github_output('duplicates', "true" if has_ext_dupe else "false")

    if output_printed:
        sys.exit(1)

    print("💦 No Duplicates detected!")
 
if __name__ == "__main__":
    main()
