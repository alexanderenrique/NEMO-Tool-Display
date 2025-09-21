#!/bin/bash

# NEMO Tool Display - Dynamic IP Setup Script
# Automatically detects IP address and configures the system

echo "NEMO Tool Display - Dynamic IP Setup"
echo "===================================="

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is required but not installed."
    exit 1
fi

# Run the dynamic IP setup script
echo "🔍 Detecting current IP address..."
python3 vm_server/dynamic_ip_setup.py

# Check if the script ran successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dynamic IP setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Compile and upload ESP32 code:"
    echo "   pio run -t upload"
    echo ""
    echo "2. Start the MQTT broker and VM server:"
    echo "   ./vm_server/quick_restart.sh"
    echo ""
    echo "3. Or start them separately:"
    echo "   cd vm_server && python main.py"
else
    echo "❌ Dynamic IP setup failed. Please check the error messages above."
    exit 1
fi
