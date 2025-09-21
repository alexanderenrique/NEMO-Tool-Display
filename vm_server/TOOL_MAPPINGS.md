# Tool Mappings Configuration

This document explains how to configure tool ID to name mappings for the NEMO Tool Display system.

## Overview

The broker needs to map tool IDs from the NEMO backend to human-readable tool names for ESP32 displays. This mapping is stored in `tool_mappings.yaml`.

## File Format

The `tool_mappings.yaml` file uses a simple key-value format:

```yaml
# Tool ID (from NEMO backend) -> Tool Name (for ESP32 topics)
1: woollam
2: fiji2
3: savannah
4: electron_microscope_1
5: xray_diffractometer
# ... continue for all tools
```

## Configuration Methods

### 1. Manual Configuration

Edit `tool_mappings.yaml` directly:

```yaml
1: woollam
2: fiji2
3: savannah
4: electron_microscope_1
5: electron_microscope_2
6: xray_diffractometer
7: atomic_force_microscope
8: scanning_tunneling_microscope
# Add all 300+ tools...
```

### 2. Generate from CSV

If you have a CSV file with tool data:

```bash
python generate_tool_mappings.py --csv tools.csv --output tool_mappings.yaml
```

CSV format:
```csv
tool_id,tool_name
1,woollam
2,fiji2
3,savannah
4,electron_microscope_1
```

### 3. Generate from JSON

If you have a JSON file with tool data:

```bash
python generate_tool_mappings.py --json tools.json --output tool_mappings.yaml
```

JSON format (list):
```json
[
  {"id": 1, "name": "woollam"},
  {"id": 2, "name": "fiji2"},
  {"id": 3, "name": "savannah"}
]
```

JSON format (dict):
```json
{
  "1": {"name": "woollam"},
  "2": {"name": "fiji2"},
  "3": {"name": "savannah"}
}
```

### 4. Generate Sequential Mappings

For testing or simple setups:

```bash
python generate_tool_mappings.py --sequential woollam fiji2 savannah --start-id 1
```

## Production Setup

For production with 300+ tools:

1. **Export tool data** from your NEMO backend or database
2. **Generate mappings** using the appropriate method above
3. **Review the generated YAML** file
4. **Deploy** the updated `tool_mappings.yaml` file
5. **Restart the broker** to load new mappings

## Broker Behavior

- **YAML file exists**: Loads mappings from file
- **YAML file missing**: Falls back to sequential mapping using `ESP32_DISPLAY_TOOLS` environment variable
- **Error loading YAML**: Falls back to sequential mapping with error logging

## ESP32 Configuration

Each ESP32 display needs to be configured with the correct tool name:

```cpp
// In config.h
#define TARGET_TOOL_NAME "woollam"  // Must match YAML mapping
```

## MQTT Topics

- **NEMO sends to**: `nemo/tools/{tool_id}/{event_type}`
- **Broker maps to**: `nemo/esp32/{tool_name}/status`
- **ESP32 subscribes to**: `nemo/esp32/{tool_name}/status`

## Troubleshooting

### Broker not loading mappings
- Check YAML file syntax
- Verify file permissions
- Check broker logs for errors

### ESP32 not receiving messages
- Verify tool name in ESP32 config matches YAML mapping
- Check MQTT topic subscription logs
- Verify broker is sending to correct topic

### Missing tool mappings
- Add missing tools to YAML file
- Restart broker after updating
- Check that tool IDs match NEMO backend

## Example Production YAML

```yaml
# Production tool mappings (300+ tools)
1: woollam
2: fiji2
3: savannah
4: electron_microscope_1
5: electron_microscope_2
6: xray_diffractometer
7: atomic_force_microscope
8: scanning_tunneling_microscope
9: transmission_electron_microscope
10: scanning_electron_microscope
# ... continue for all tools
```

## Maintenance

- **Regular updates**: Update YAML when tools are added/removed
- **Backup**: Keep backup copies of working configurations
- **Version control**: Track changes to tool mappings
- **Documentation**: Document any special tool naming conventions
