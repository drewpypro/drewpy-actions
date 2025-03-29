#!/usr/bin/env python3
import argparse
import os
import json
import sys
import pandas as pd
from typing import Dict, List, Any


CONFIG = {
    "OUTPUT_DIR": "./sg_rules"
}

def read_existing_json(file_path: str) -> List[Dict[str, Any]]:
    """Read existing JSON file if it exists."""
    if os.path.exists(file_path):
        with open(file_path, "r") as jsonfile:
            try:
                return json.load(jsonfile)
            except json.JSONDecodeError:
                print(f"Warning: {file_path} is not a valid JSON. It will be overwritten.")
    return []

def rules_changed(existing_rules: List[Dict[str, Any]], new_rules: List[Dict[str, Any]]) -> bool:
    """Compare existing and new rules to determine if updates are needed."""
    return existing_rules != new_rules

def write_rule_count(rules):
    """Write the count of rules per security group per direction to rule_count.txt in the root directory."""
    rule_count_file = "rule_count.txt"
    with open(rule_count_file, "w") as f:
        f.write("# Security Group Rule Count:\n")
        
        for direction in ["ingress", "egress"]:
            f.write(f"\n## {direction.capitalize()} Rules:\n")
            for sg_name in sorted(rules[direction].keys()):
                rule_list = rules[direction][sg_name]
                f.write(f"- {sg_name} : {len(rule_list)} rules\n")
    
    print(f"Rule count written to {rule_count_file}")


def process_rules(input_file: str) -> None:
    """Main function to process rules into JSON."""
    # Create output directory if it doesn't exist
    os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)
    
    # Read CSV file into pandas DataFrame and replace NaN with "null"
    df = pd.read_csv(input_file).fillna("null")
   
    # Process valid rules
    rules = {"ingress": {}, "egress": {}}
    
    # Group rules by direction and security group
    for direction in ["ingress", "egress"]:
        direction_df = df[df['direction'] == direction]
        for sg_name, group in direction_df.groupby('security_group_id'):
            rules[direction][sg_name] = group.to_dict('records')
    
    # Get current security groups from CSV
    all_security_groups = set(rules["ingress"].keys()).union(rules["egress"].keys())
    
    # Get existing security group files
    existing_files = set(f.replace('.json', '') for f in os.listdir(CONFIG["OUTPUT_DIR"]) 
                        if f.endswith('.json'))
    
    # Find security groups that need to be emptied
    to_empty = existing_files - all_security_groups
    
    # Handle security groups no longer in CSV
    if to_empty:
        print("\nThe following security groups are no longer in the CSV and will be emptied:")
        for sg in to_empty:
            output_file = os.path.join(CONFIG["OUTPUT_DIR"], f"{sg}.json")
            with open(output_file, "w") as jsonfile:
                json.dump([], jsonfile, indent=4)
            print(f"- Cleared rules for: {sg}")
    
    # Process current security groups
    changes_detected = False
    for sg_name in all_security_groups:
        # Combine ingress and egress rules for the security group
        combined_rules = (rules["ingress"].get(sg_name, []) + 
                         rules["egress"].get(sg_name, []))
        
        output_file = os.path.join(CONFIG["OUTPUT_DIR"], f"{sg_name}.json")
        
        # Read existing JSON rules for comparison
        existing_rules = read_existing_json(output_file) or []
        
        # Sort combined rules for consistency
        combined_rules_sorted = sorted(combined_rules, key=lambda x: (
            x["direction"], str(x["from_port"]), str(x["to_port"]), 
            x["ip_protocol"], str(x.get("referenced_security_group_id", "")),
            str(x.get("cidr_ipv4", "")), str(x.get("cidr_ipv6", ""))
        ))
        
        # Overwrite only if rules have changed
        if rules_changed(existing_rules, combined_rules_sorted):
            with open(output_file, "w") as jsonfile:
                json.dump(combined_rules_sorted, jsonfile, indent=4)
            print(f"Updated: {output_file}")
            changes_detected = True
        else:
            print(f"No changes: {output_file}")
    
    print(f"\nJSON files have been synchronized in {CONFIG['OUTPUT_DIR']}")

    # Write rule count to the root folder
    write_rule_count(rules)
    

def main():
    parser = argparse.ArgumentParser(description='Convert firewall rules CSV into json.')
    parser.add_argument('--input-file', required=True, help='Input CSV file')
    args = parser.parse_args()
    process_rules(args.input_file)

if __name__ == "__main__":
    main()