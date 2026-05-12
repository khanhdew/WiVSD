#!/bin/bash
# Quick start script for real-time CSI detection

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== ESP32 CSI Real-time Detection Setup ===${NC}\n"

# Check Python version
echo -e "${BLUE}[1/4] Checking Python version...${NC}"
python3 --version || { echo "Python3 not found!"; exit 1; }

# Check dependencies
echo -e "${BLUE}[2/4] Checking dependencies...${NC}"
python3 -c "import pandas, numpy, scipy, serial, joblib" 2>/dev/null || {
    echo -e "${YELLOW}Some dependencies missing. Installing...${NC}"
    pip install --upgrade pip
    pip install pandas numpy scipy pyserial scikit-learn joblib numba
}

# Check model file
echo -e "${BLUE}[3/4] Checking model file...${NC}"
if [ -f "models/rf_person_detector.joblib" ]; then
    echo -e "${GREEN}✓ Model found${NC}"
else
    echo -e "${YELLOW}⚠ Model not found. Using default training model...${NC}"
fi

# List available ports
echo -e "${BLUE}[4/4] Available serial ports:${NC}"
python3 -c "
import serial.tools.list_ports
ports = list(serial.tools.list_ports.comports())
if ports:
    for i, p in enumerate(ports, 1):
        print(f'  {i}. {p.device} ({p.description})')
else:
    print('  No ports found. Please connect ESP32 first.')
" || echo "  Could not list ports"

echo ""
echo -e "${GREEN}Setup complete!${NC}\n"

# Show usage options
echo -e "${BLUE}Usage:${NC}\n"
echo -e "  ${GREEN}1. GUI Version (recommended for beginners):${NC}"
echo -e "     python3 realtime_detector_gui.py\n"

echo -e "  ${GREEN}2. CLI Version (for automation/scripts):${NC}"
echo -e "     python3 realtime_detector.py --port /dev/ttyUSB0\n"

echo -e "For more options, see: ${YELLOW}REALTIME_DETECTION.md${NC}\n"

# Detect ESP32 and suggest port
echo -e "${BLUE}Attempting to auto-detect ESP32...${NC}"
python3 << 'EOF'
import serial.tools.list_ports
ports = list(serial.tools.list_ports.comports())
esp_port = None
for p in ports:
    if 'USB' in p.description or 'CH340' in p.description or 'Silicon Labs' in p.description:
        esp_port = p.device
        break

if esp_port:
    print(f"\nDetected ESP32 on: {esp_port}")
    print(f"Quick start command:\n  python3 realtime_detector.py --port {esp_port}")
else:
    print("\nNo ESP32 detected. Manual setup needed.")
    print("Check available ports with: ls /dev/ttyUSB* /dev/ttyACM*")
EOF
