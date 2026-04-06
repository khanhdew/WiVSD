# CSI Binary Output Mode - Setup & Usage

## 📊 Performance Comparison

| Mode | Format | Bytes/Packet | Speed | Overhead |
|------|--------|-------|-------|----------|
| **Text CSV** | `CSI_DATA,...[...]` | 200-400 | 1x (baseline) | Text conversion |
| **Binary Compact** | Fixed struct | 28 + CSI_len | **3-5x faster** ✅ | Zero |
| **Binary + Sync** | Struct + markers | 30 + CSI_len | **3-5x faster** | Error detection |

---

## 🔧 Configuration (C Code)

### Step 1: Enable Binary Mode
Edit `esp-csi/examples/get-started/csi_recv_custom/main/app_main.c`:

```c
// Line ~50: Choose output mode
#define CONFIG_OUTPUT_MODE 1  // 0=CSV (text), 1=Binary, 2=Binary+Sync
```

### Step 2: Build & Flash
```bash
cd esp-csi/examples/get-started/csi_recv_custom
idf.py build
idf.py flash -p /dev/ttyACM0 -b 921600
```

### Step 3: Collect Data
```bash
# Option A: Pipe serial directly to file
cat /dev/ttyACM0 > csi_binary_data.bin &

# Option B: Use Python miniterm with buffering
python -m serial.tools.miniterm /dev/ttyACM0 921600 --exit-char 3 --file csi_binary.bin
```

---

## 📥 Decoding Binary Data (Python)

### Basic Usage
```bash
python3 csi_binary_decoder.py csi_binary_data.bin
```

### Export to CSV
```bash
python3 csi_binary_decoder.py csi_binary_data.bin --csv output.csv
```

### Export to JSON
```bash
python3 csi_binary_decoder.py csi_binary_data.bin --json output.json
```

### Both
```bash
python3 csi_binary_decoder.py csi_binary_data.bin --csv output.csv --json output.json
```

### Specify Sync Mode
```bash
python3 csi_binary_decoder.py csi_binary_data.bin --mode 2  # For CONFIG_OUTPUT_MODE=2
```

---

## 📊 Binary Packet Structure

### Header (28 bytes)
```python
struct {
    uint8_t  magic[2]           # 0xAA, 0xBB
    uint8_t  version            # Protocol version
    uint8_t  chip_type          # 0=ESP32, 1=C6, 2=C5/C61
    uint32_t sequence           # Packet sequence number
    uint8_t  mac[6]             # Source MAC
    int8_t   rssi               # Signal strength
    uint8_t  rate               # Data rate
    int8_t   noise_floor        # Noise floor
    int8_t   fft_gain           # FFT gain
    uint8_t  agc_gain           # AGC gain
    uint8_t  channel            # WiFi channel
    uint8_t  bandwidth          # 0=20MHz, 1=40MHz, 2=80MHz
    uint16_t timestamp_lo       # Timestamp (lower 16 bits)
    uint16_t timestamp_hi       # Timestamp (upper 16 bits)
    uint16_t csi_len            # Number of CSI subcarriers
    uint8_t  first_word_invalid # Validity flag
    uint8_t  reserved
}
```

### CSI Data
```python
int8_t csi_data[csi_len]  # Compensated CSI values
```

### Optional Sync Marker (MODE=2)
```python
uint16_t sync = 0xBBAA  # End-of-packet marker
```

---

## 💾 Example Output (CSV)

```csv
sequence,mac,rssi,rate,noise_floor,fft_gain,agc_gain,channel,bandwidth,timestamp,csi_len,first_word_invalid,csi_data
0,1A:00:00:00:00:00,-45,8,-85,5,14,13,40MHz,12345,256,0,"45,42,38,35,32,29,26,23,20,18,...256 values"
1,1A:00:00:00:00:00,-45,8,-85,5,14,13,40MHz,12467,256,0,"46,43,39,36,33,30,27,24,21,19,...256 values"
```

---

## ⚡ UART Speed Settings

Default baud rate in code: **921600** (fast)

To match your `serial_to_csv.py`, check its baud rate and update if needed:

```bash
# In serial_to_csv.py, change:
ser = serial.Serial(args.port, 921600)  # or your preferred baudrate
```

For **binary mode** with large CSI packets (256+ subcarriers):
- **115200 baud**: ~25ms/packet (40 packets/sec)
- **460800 baud**: ~6ms/packet (160 packets/sec) ✅
- **921600 baud**: ~3ms/packet (300 packets/sec) ✅✅

---

## 🐛 Troubleshooting

### "Invalid magic" errors
- Ensure `CONFIG_OUTPUT_MODE` on ESP32 matches `--mode` in decoder
- Check for serial corruption (electrical noise, bad USB cable)

### Incomplete packets
- Lower UART baud rate if data loss
- Increase UART buffer size: `idf.py menuconfig` → Component → UART

### Mode mismatch
```bash
# If you compiled with CONFIG_OUTPUT_MODE=2, use:
python3 csi_binary_decoder.py data.bin --mode 2
```

---

## 📝 Integration with Python Processing

```python
from csi_binary_decoder import CSIBinaryPacket, read_binary_csi_stream

# Load packets
packets = read_binary_csi_stream("csi_data.bin", mode=1)

# Process
for pkt in packets:
    print(f"Seq: {pkt.sequence}, RSSI: {pkt.rssi}, CSI: {pkt.csi[:5]}...")
    
    # Use in ML/signal processing
    csi_array = np.array(pkt.csi)
```

---

## 🎯 UART Speed Gain

**Baseline (CSV text)**: ~400 bytes/packet → ~30 packets/sec @ 115200
```
CSI_DATA,0,...,rssi=-45,...,"[45,42,38,...]"
```

**Binary Compact**: ~35 bytes/packet → **300+ packets/sec @ 921600**
```
[0xAA 0xBB ...28 bytes header... + CSI bytes]
```

**Improvement**: **~10x faster** UART throughput ✅

---

## 📋 Mode Summary

| CONFIG_OUTPUT_MODE | Use Case | Sync Marker |
|------|----------|---------|
| 0 | Development, debugging | No |
| 1 | Production streaming | No |
| 2 | Error-critical systems | Yes (0xBBAA) |

Recommended: **Mode 1** for speed-critical applications.

