#!/usr/bin/env python3
import argparse
import sys
import pandas as pd
from typing import Dict, List, Any
import ipaddress
from pandas.errors import ParserError

CONFIG = {
    "VALID_PROTOCOLS": ["tcp", "udp", "icmp", "-1"]
}

def validate_required_fields(df: pd.DataFrame, line_numbers) -> List[Dict[str, Any]]:
    """Check all required fields are present"""
    errors = []
    required_fields = ['RequestID', 'name', 'security_group_id', 'direction', 
                      'from_port', 'to_port', 'ip_protocol' ]
    
    for field in required_fields:
        missing_mask = df[field].isna() | (df[field].astype(str).str.strip() == '')
        if missing_mask.any():
            for index, row in df[missing_mask].iterrows():
                errors.append({
                    "line_number": line_numbers.get(index, "Unknown"),
                    "row": row.to_dict(),
                    "error": f"Missing required field: {field}"
                })
    return errors

def validate_field_values(df: pd.DataFrame, line_numbers) -> List[Dict[str, Any]]:
    """Check direction and protocol values are valid"""
    errors = []
    
    invalid_direction = ~df['direction'].str.lower().isin(['ingress', 'egress'])
    if invalid_direction.any():
        for index, row in df[invalid_direction].iterrows():
            errors.append({
                "line_number": line_numbers.get(index, "Unknown"),
                "row": row.to_dict(),
                "error": "Direction must be either 'ingress' or 'egress'"
            })

    invalid_protocol = ~df['ip_protocol'].str.lower().isin(CONFIG['VALID_PROTOCOLS'])
    if invalid_protocol.any():
        for index, row in df[invalid_protocol].iterrows():
            errors.append({
                "line_number": line_numbers.get(index, "Unknown"),
                "row": row.to_dict(),
                "error": f"Protocol must be one of: {', '.join(CONFIG['VALID_PROTOCOLS'])}"
            })

    return errors

def validate_ports(df: pd.DataFrame, line_numbers) -> List[Dict[str, Any]]:
    """Validate port ranges based on protocol:
    - TCP/UDP: ports must be 0-65535 and from_port <= to_port
    - ICMP: ports must be 0-255 (representing type/code)
    """
    validation_rules = {
        'tcp/udp': "TCP/UDP: ports must be 0-65535 and from_port <= to_port",
        'icmp': "ICMP: ports must be 0-255 (representing type/code)"
    }
    errors = []
    
    for index, row in df.iterrows():
        try:
            protocol = row['ip_protocol'].lower()

            if protocol == '-1':
                continue

            from_port = int(row['from_port'])
            to_port = int(row['to_port'])
            
            if protocol == 'icmp':
                if not (0 <= from_port <= 255 and 0 <= to_port <= 255):
                    errors.append({
                        "line_number": line_numbers.get(index, "Unknown"),
                        "row": row.to_dict(),
                        "error": f"Invalid ICMP ports: {from_port}, {to_port}. {validation_rules['icmp']}"
                    })
            else: 
                if not (0 <= from_port <= 65535 and 0 <= to_port <= 65535):
                    errors.append({
                        "line_number": line_numbers.get(index, "Unknown"),
                        "row": row.to_dict(),
                        "error": f"Invalid port range: {from_port}, {to_port}. {validation_rules['tcp/udp']}"
                    })
                elif from_port > to_port:
                    errors.append({
                        "line_number": line_numbers.get(index, "Unknown"),
                        "row": row.to_dict(),
                        "error": f"From port ({from_port}) cannot be greater than to port ({to_port})"
                    })
        except ValueError:
            errors.append({
                "line_number": line_numbers.get(index, "Unknown"),
                "row": row.to_dict(),
                "error": f"Port values must be integers, got from_port={row['from_port']}, to_port={row['to_port']}"
            })
    return errors

def validate_input_declarations(df: pd.DataFrame, line_numbers) -> List[Dict[str, Any]]:
    """Check that only one source (security group, CIDR IPv4, CIDR IPv6 or prefix_list_id) is specified per rule"""
    errors = []
    rule_conditions = [
        (df['referenced_security_group_id'].fillna('null') != 'null') & 
        (df['referenced_security_group_id'].fillna('null').str.lower() != 'null'),
        (df['cidr_ipv4'].fillna('null') != 'null') & 
        (df['cidr_ipv4'].fillna('null').str.lower() != 'null'),
        (df['cidr_ipv6'].fillna('null') != 'null') & 
        (df['cidr_ipv6'].fillna('null').str.lower() != 'null'),
        (df['prefix_list_id'].fillna('null') != 'null') & 
        (df['prefix_list_id'].fillna('null').str.lower() != 'null')
    ]
    
    multiple_inputs = sum(rule_conditions) > 1
    if multiple_inputs.any():
        for index, row in df[multiple_inputs].iterrows():
            errors.append({
                "line_number": line_numbers.get(index, "Unknown"),
                "row": row.to_dict(),
                "error": "Only one source (security group, CIDR IPv4, CIDR IPv6 or prefix_list_id) can be specified per rule"
            })

    return errors

def validate_null_input(df: pd.DataFrame, line_numbers) -> List[Dict[str, Any]]:
    """Ensure that at least one input (security group, CIDR IPv4, CIDR IPv6 or prefix_list_id) is set per rule."""

    errors = []
    rule_conditions = [
        (df['referenced_security_group_id'].fillna('null').str.lower() != 'null'),
        (df['cidr_ipv4'].fillna('null').str.lower() != 'null'),
        (df['cidr_ipv6'].fillna('null').str.lower() != 'null'),
        (df['prefix_list_id'].fillna('null').str.lower() != 'null')
    ]

    missing_inputs = sum(rule_conditions) == 0
    if missing_inputs.any():
        for index, row in df[missing_inputs].iterrows():
            errors.append({
                "line_number": line_numbers.get(index, "Unknown"),
                "row": row.to_dict(),
                "error": "At least one input (security group, CIDR IPv4, CIDR IPv6 or prefix_list_id) must be specified."
            })

        return errors



def validate_ip_addresses(df: pd.DataFrame, line_numbers) -> List[Dict[str, Any]]:
    """Check IP address formats and ensure proper CIDR notation for security group rules.
    IPv4: Must use /0 to /32
    IPv6: Must use /0 to /128
    """
    errors = []
    
    for index, row in df.iterrows():
        for ip_field, version in [('cidr_ipv4', 4), ('cidr_ipv6', 6)]:
            ip = row[ip_field]
            if pd.isna(ip) or str(ip).lower() == 'null':
                continue

            # Check for CIDR notation
            if '/' not in str(ip):
                errors.append({
                    "line_number": line_numbers.get(index, "Unknown"),
                    "row": row.to_dict(),
                    "error": f"IP address {ip} must be in CIDR notation (e.g., x.x.x.x/32 for IPv4, x:x:x:x:x:x:x:x/128 for IPv6)"
                })
                continue
                
            try:
                ip_obj = ipaddress.ip_network(ip, strict=False)
                
                # Verify IP version
                if ip_obj.version != version:
                    errors.append({
                        "line_number": line_numbers.get(index, "Unknown"),
                        "row": row.to_dict(),
                        "error": f"IP address {ip} must be a valid IPv{version} CIDR block"
                    })
                    continue

                # Verify prefix length
                max_prefix = 32 if version == 4 else 128
                if not (0 <= ip_obj.prefixlen <= max_prefix):
                    errors.append({
                        "line_number": line_numbers.get(index, "Unknown"),
                        "row": row.to_dict(),
                        "error": f"IPv{version} CIDR {ip} must have a prefix length between 0 and {max_prefix}"
                    })
                    
            except ValueError as e:
                errors.append({
                    "line_number": line_numbers.get(index, "Unknown"),
                    "row": row.to_dict(),
                    "error": f"Invalid CIDR block {ip}: Must be a valid IPv{version} CIDR notation"
                })
            except TypeError:
                errors.append({
                    "line_number": line_numbers.get(index, "Unknown"),
                    "row": row.to_dict(),
                    "error": f"Invalid IP format: {ip} must be a string in CIDR notation"
                })
    return errors

def validate_prefix_lists(df: pd.DataFrame, line_numbers) -> List[Dict[str, Any]]:
    """Ensure prefix_list_id is only 's3' or 'dynamodb'."""
    errors = []
    valid_prefix_lists = [ "s3", "dynamodb", "null"]

    invalid_rows = ~df["prefix_list_id"].isin(valid_prefix_lists)

    if invalid_rows.any():
        errors.extend([
            {
                "line_number": line_numbers.get(index, "Unknown"),
                "row": row.to_dict(),
                "error": f"Invalid prefix_list_id: '{row['prefix_list_id']}'. "
                         f"Must be one of {', '.join(valid_prefix_lists)}."
            }
            for index, row in df[invalid_rows].iterrows()
        ])
    
    return errors

def check_duplicates(df: pd.DataFrame, line_numbers) -> List[Dict[str, Any]]:
    """Check for duplicate rules."""
    errors = []
    duplicate_mask = df.duplicated(subset=[
        'name', 'security_group_id', 'direction', 'from_port', 
        'to_port', 'ip_protocol', 'referenced_security_group_id',
        'cidr_ipv4', 'cidr_ipv6', 'prefix_list_id'
    ], keep=False)
    
    if duplicate_mask.any():
        return [
            {"line_number": line_numbers.get(index, "Unknown"), "row": row.to_dict(), "error": "Duplicate rule detected"}
            for index, row in df[duplicate_mask].iterrows()
        ]
    return errors


def validate_rules(df: pd.DataFrame, line_numbers) -> Dict[str, List[Dict[str, Any]]]:
    """Main validation function that calls all validators in sequence"""
    issues = {}
    
    # 1. Required fields
    if field_errors := validate_required_fields(df, line_numbers):
        issues["missing_fields"] = field_errors

    # 2. Field values
    if value_errors := validate_field_values(df, line_numbers):
        issues["invalid_fields"] = value_errors

    # 3. Ports
    if port_errors := validate_ports(df, line_numbers):
        issues["port_validation"] = port_errors

    # 4. Source declarations
    if input_errors := validate_input_declarations(df, line_numbers):
        issues["multiple_input_declarations"] = input_errors
        
    # 5. IPs
    if ip_errors := validate_ip_addresses(df, line_numbers):
        issues["ip_validation"] = ip_errors

    # 6. Duplicates
    if duplicate_errors := check_duplicates(df, line_numbers):
        issues["duplicates"] = duplicate_errors

    # 7. Prefix Lists 
    if prefix_errors := validate_prefix_lists(df, line_numbers):
        issues["prefix_validation"] = prefix_errors

    # 8. Null input
    if invalid_input := validate_null_input(df, line_numbers):
        issues["invalid_input"] = invalid_input


    return issues

def main():
    parser = argparse.ArgumentParser(description='Validate firewall rules CSV.')
    parser.add_argument('--input-file', required=True, help='Input CSV file')
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.input_file).fillna("null")
    except ParserError as e:
        print("Error: malformed CSV input.")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print("Error: unknown error reading CSV.")
        sys.exit(1)

    line_numbers = df.index.to_series() + 2
    issues = validate_rules(df, line_numbers)

    if issues:
        print("Validation failed with the following issues:")
        for issue_type, items in issues.items():
            print(f"\n{issue_type.replace('_', ' ').title()}:")
            for item in items:
                print(f"Error: Line {item['line_number']}: {item['error']}")
                print(f"Row data: {item['row']}\n")
        sys.exit(1)
    else:
        print("Validation successful.")
        sys.exit(0)

if __name__ == "__main__":
    main()