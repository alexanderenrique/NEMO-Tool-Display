#!/usr/bin/env python3
"""
Script to download all tools from the NEMO API and create a lookup mapping.
This creates a mapping from tool names to tool IDs for use in rate creation.
Also provides generate_from_api() for VM server startup (writes tool_mappings.yaml).
"""

import json
import os
import requests
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Load environment variables from .env file
load_dotenv()

# NEMO API endpoint for tools (used when run as script)
NEMO_TOOLS_API_URL = os.getenv("NEMO_API_URL") or "http://localhost:8000/api/tools/"

# Get NEMO token from environment (for script usage)
NEMO_TOKEN = os.getenv("NEMO_TOKEN")
if not NEMO_TOKEN or NEMO_TOKEN == "your_nemo_token_here":
    API_HEADERS = {}
else:
    API_HEADERS = {
        "Authorization": f"Token {NEMO_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get_env_stripped(key: str) -> Optional[str]:
    """Get env var and strip whitespace; try key with trailing space (tolerate 'KEY = value' in .env)."""
    v = os.getenv(key) or os.getenv(key + " ")
    return v.strip() if v else None


def test_api_connection(api_url: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
    """Test the API connection and authentication."""
    url = api_url or NEMO_TOOLS_API_URL
    h = headers or API_HEADERS
    try:
        response = requests.get(url, headers=h)
        if response.status_code == 200:
            print("✓ API connection successful")
            return True
        elif response.status_code == 401:
            print("✗ Authentication failed: Check your NEMO_TOKEN")
            return False
        elif response.status_code == 403:
            print("✗ Permission denied: Check your API permissions")
            return False
        else:
            print(f"✗ API connection failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Network error connecting to API: {e}")
        return False

def download_tools(api_url: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> List[Dict]:
    """Download all tools from the NEMO API."""
    url = api_url or NEMO_TOOLS_API_URL
    h = headers or API_HEADERS
    print("Downloading tools from NEMO API...")
    all_tools = []
    page = 1
    while True:
        try:
            params = {"page": page}
            response = requests.get(url, headers=h, params=params)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Check if this is a paginated response
                if 'results' in response_data:
                    tools = response_data['results']
                    print(f"  Page {page}: Retrieved {len(tools)} tools")
                else:
                    # Direct list response
                    tools = response_data
                    print(f"  Retrieved {len(tools)} tools (no pagination)")
                
                if not tools:
                    break
                
                all_tools.extend(tools)
                
                # Check if there are more pages
                if 'next' in response_data and response_data['next']:
                    page += 1
                else:
                    break
                    
            elif response.status_code == 401:
                print("✗ Authentication failed: Check your NEMO_TOKEN")
                return []
            elif response.status_code == 403:
                print("✗ Permission denied: Check your API permissions")
                return []
            else:
                print(f"✗ Failed to download tools: HTTP {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Network error downloading tools: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing API response: {e}")
            return []
    
    print(f"✓ Total tools downloaded: {len(all_tools)}")
    return all_tools

def save_tools_to_json(tools: list, filename: str = "tools_download.json"):
    """Save the downloaded tools to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(tools, f, indent=2)
        print(f"✓ Tools saved to {filename}")
    except Exception as e:
        print(f"✗ Error saving tools to {filename}: {e}")

def create_tool_lookup(tools: list) -> Dict[str, int]:
    """Create a lookup mapping from tool names to tool IDs."""
    tool_lookup = {}
    
    for tool in tools:
        if 'name' in tool and 'id' in tool:
            tool_name = tool['name']
            tool_id = tool['id']
            tool_lookup[tool_name] = tool_id
    
    print(f"✓ Created tool lookup with {len(tool_lookup)} tools")
    return tool_lookup

def save_tool_lookup(tool_lookup: Dict[str, int], filename: str = "tool_lookup.json"):
    """Save the tool lookup to a JSON file."""
    try:
        with open(filename, "w") as f:
            json.dump(tool_lookup, f, indent=2)
        print(f"✓ Tool lookup saved to {filename}")
    except Exception as e:
        print(f"✗ Error saving tool lookup to {filename}: {e}")


def generate_from_api(
    output_file: str = "tool_mappings.yaml",
    tools: Optional[List[Dict]] = None,
) -> bool:
    """
    Generate tool_mappings.yaml (id -> name) from NEMO API for VM server startup.
    If tools is provided, write from that list; otherwise load config.env and fetch.
    Returns True on success, False otherwise.
    """
    if tools is None:
        _dir = os.path.dirname(os.path.abspath(__file__)) or "."
        load_dotenv()
        load_dotenv(os.path.join(_dir, "config.env"))
        api_url = _get_env_stripped("NEMO_API_URL")
        api_token = _get_env_stripped("NEMO_TOKEN")
        custom_header = _get_env_stripped("NEMO_AUTH_HEADER")
        auth_scheme = (_get_env_stripped("NEMO_AUTH_SCHEME") or "Token").strip().lower()
        if auth_scheme not in ("token", "bearer"):
            auth_scheme = "token"
        auth_scheme = "Token" if auth_scheme == "token" else "Bearer"
        if not api_url:
            return False
        if not api_token or api_token == "your_nemo_token_here":
            return False
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if custom_header:
            headers[custom_header] = api_token
        else:
            headers["Authorization"] = f"{auth_scheme} {api_token}"
        tools = download_tools(api_url=api_url, headers=headers)
    if not tools:
        return False
    mappings = {}
    for tool in tools:
        tool_id = str(tool.get("id", tool.get("tool_id", ""))).strip()
        tool_name = (tool.get("name") or tool.get("tool_name") or "").strip().lower()
        if tool_id and tool_name:
            mappings[tool_id] = tool_name
    if not mappings:
        return False
    try:
        import yaml
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# NEMO Tool Display - Tool ID to Name Mappings\n")
            f.write("# Generated from NEMO API (download_tools)\n\n")
            yaml.dump(mappings, f, default_flow_style=False, sort_keys=True)
        return True
    except Exception:
        return False


def main():
    """Main function to download tools and create lookup."""
    if not NEMO_TOKEN or NEMO_TOKEN == "your_nemo_token_here":
        print("Error: NEMO_TOKEN not found in environment or .env")
        print("Set NEMO_TOKEN in .env or config.env, or export NEMO_TOKEN=your_token_here")
        exit(1)
    print("Starting tool download from NEMO API...")
    print(f"API Endpoint: {NEMO_TOOLS_API_URL}")
    print("-" * 60)
    if not test_api_connection():
        print("Cannot proceed without valid API connection.")
        return
    
    # Download tools
    tools = download_tools(NEMO_TOOLS_API_URL)
    
    if not tools:
        print("No tools downloaded. Cannot proceed.")
        return
    
    # Save raw tools data
    save_tools_to_json(tools)
    
    # Create and save tool lookup
    tool_lookup = create_tool_lookup(tools)
    save_tool_lookup(tool_lookup)
    # Also write tool_mappings.yaml for VM server compatibility (no extra API call)
    if generate_from_api("tool_mappings.yaml", tools=tools):
        print("✓ tool_mappings.yaml updated for VM server")
    # Show sample of the lookup
    print("\nSample tool lookup (first 10 tools):")
    count = 0
    for tool_name, tool_id in tool_lookup.items():
        if count < 10:
            print(f"  {tool_name} → ID {tool_id}")
            count += 1
        else:
            break
    
    if len(tool_lookup) > 10:
        print(f"  ... and {len(tool_lookup) - 10} more tools")
    
    print("\n" + "=" * 60)
    print("TOOL DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Total tools downloaded: {len(tools)}")
    print(f"Tools in lookup: {len(tool_lookup)}")
    print(f"✓ Tool lookup ready for use in rate creation!")
    print("\nFiles created:")
    print(f"  - tools_download.json (raw tool data)")
    print(f"  - tool_lookup.json (name → ID mapping)")

if __name__ == "__main__":
    main()