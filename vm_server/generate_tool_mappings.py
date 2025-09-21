#!/usr/bin/env python3
"""
Tool Mappings Generator
Helper script to generate tool_mappings.yaml from various data sources
"""

import yaml
import csv
import json
import argparse
from typing import Dict, Any


def generate_from_csv(csv_file: str, output_file: str = "tool_mappings.yaml") -> None:
    """Generate YAML mappings from CSV file with columns: tool_id, tool_name"""
    mappings = {}
    
    try:
        with open(csv_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                tool_id = str(row['tool_id']).strip()
                tool_name = row['tool_name'].strip().lower()
                mappings[tool_id] = tool_name
                
        print(f"Loaded {len(mappings)} mappings from {csv_file}")
        
    except Exception as e:
        print(f"Error reading CSV file {csv_file}: {e}")
        return
    
    write_yaml(mappings, output_file)


def generate_from_json(json_file: str, output_file: str = "tool_mappings.yaml") -> None:
    """Generate YAML mappings from JSON file with tool data"""
    mappings = {}
    
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
        # Handle different JSON structures
        if isinstance(data, list):
            # List of tool objects
            for tool in data:
                tool_id = str(tool.get('id', tool.get('tool_id', ''))).strip()
                tool_name = tool.get('name', tool.get('tool_name', '')).strip().lower()
                if tool_id and tool_name:
                    mappings[tool_id] = tool_name
        elif isinstance(data, dict):
            # Dictionary with tool_id as keys
            for tool_id, tool_data in data.items():
                if isinstance(tool_data, dict):
                    tool_name = tool_data.get('name', tool_data.get('tool_name', '')).strip().lower()
                else:
                    tool_name = str(tool_data).strip().lower()
                
                if tool_name:
                    mappings[str(tool_id).strip()] = tool_name
                    
        print(f"Loaded {len(mappings)} mappings from {json_file}")
        
    except Exception as e:
        print(f"Error reading JSON file {json_file}: {e}")
        return
    
    write_yaml(mappings, output_file)


def generate_sequential(start_id: int, tool_names: list, output_file: str = "tool_mappings.yaml") -> None:
    """Generate YAML mappings with sequential IDs starting from start_id"""
    mappings = {}
    
    for i, tool_name in enumerate(tool_names, start_id):
        mappings[str(i)] = tool_name.strip().lower()
    
    print(f"Generated {len(mappings)} sequential mappings starting from ID {start_id}")
    write_yaml(mappings, output_file)


def write_yaml(mappings: Dict[str, str], output_file: str) -> None:
    """Write mappings to YAML file with proper formatting"""
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write("# NEMO Tool Display - Tool ID to Name Mappings\n")
            file.write("# Generated automatically - update as needed for production\n\n")
            
            yaml.dump(mappings, file, default_flow_style=False, sort_keys=True)
            
        print(f"Successfully wrote {len(mappings)} mappings to {output_file}")
        
    except Exception as e:
        print(f"Error writing YAML file {output_file}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Generate tool mappings YAML file")
    parser.add_argument("--csv", help="Generate from CSV file (columns: tool_id, tool_name)")
    parser.add_argument("--json", help="Generate from JSON file")
    parser.add_argument("--sequential", nargs="+", help="Generate sequential mappings from tool names")
    parser.add_argument("--start-id", type=int, default=1, help="Starting ID for sequential generation")
    parser.add_argument("--output", default="tool_mappings.yaml", help="Output YAML file")
    
    args = parser.parse_args()
    
    if args.csv:
        generate_from_csv(args.csv, args.output)
    elif args.json:
        generate_from_json(args.json, args.output)
    elif args.sequential:
        generate_sequential(args.start_id, args.sequential, args.output)
    else:
        print("Please specify --csv, --json, or --sequential")
        parser.print_help()


if __name__ == "__main__":
    main()
