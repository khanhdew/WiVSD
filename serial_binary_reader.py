#!/usr/bin/env python3
"""
Serial Binary CSI Reader
Read binary CSI from ESP32 serial port → write directly to CSV
"""

import serial
import sys
import argparse
import csv
from pathlib import Path
from datetime import datetime

HEADER_SIZE = 32
CSV_FIELDS = [
    'type', 'seq', 'mac', 'rssi', 'rate', 'noise_floor', 'fft_gain', 'agc_gain',
    'channel', 'local_timestamp', 'sig_len', 'rx_state', 'len', 'first_word', 'data'
]

def parse_packet(data):
    """Parse 32-byte header + CSI payload → dict matching CSV format"""
    if len(data) < HEADER_SIZE or data[0] != 0xAA or data[1] != 0xBB:
        return None
    
    seq = int.from_bytes(data[4:8], 'little')
    mac = ':'.join(f'{b:02x}' for b in data[8:14])
    rssi = int.from_bytes(data[14:15], 'big', signed=True)
    rate = data[15]
    noise_floor = int.from_bytes(data[16:17], 'big', signed=True)
    fft_gain = int.from_bytes(data[17:18], 'big', signed=True)
    agc_gain = data[18]
    channel = data[19]
    timestamp_lo = int.from_bytes(data[20:22], 'little')
    timestamp_hi = int.from_bytes(data[22:24], 'little')
    sig_len = int.from_bytes(data[24:26], 'little')
    rx_state = int.from_bytes(data[26:28], 'little')
    csi_len = int.from_bytes(data[28:30], 'little')
    first_word_invalid = data[30]
    
    timestamp = (timestamp_hi << 16) | timestamp_lo
    
    # CSI data as signed int16 array (2 bytes per value, little-endian)
    csi_vals = []
    csi_byte_len = csi_len * 2  # Each value is int16_t = 2 bytes
    for i in range(0, min(csi_len * 2, len(data) - HEADER_SIZE), 2):
        offset = HEADER_SIZE + i
        if offset + 1 < len(data):
            v = int.from_bytes(data[offset:offset+2], 'little', signed=True)
            csi_vals.append(str(v))
    csi_str = '[' + ','.join(csi_vals) + ']'
    
    return {
        'type': 'CSI_DATA',
        'seq': seq,
        'mac': mac,
        'rssi': rssi,
        'rate': rate,
        'noise_floor': noise_floor,
        'fft_gain': fft_gain,
        'agc_gain': agc_gain,
        'channel': channel,
        'local_timestamp': timestamp,
        'sig_len': sig_len,
        'rx_state': rx_state,
        'len': csi_len,
        'first_word': first_word_invalid,
        'data': csi_str,
    }

def read_serial_to_csv(port="/dev/ttyACM0", baudrate=921600, duration=10, csv_file="csi_output.csv"):
    """Read binary CSI from serial port and write directly to CSV file"""
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
    except serial.SerialException as e:
        print(f"[!] Cannot open {port}: {e}")
        print("    Check: ls -la /dev/ttyACM* /dev/ttyUSB*")
        sys.exit(1)

    print(f"[+] Connected to {port} @ {baudrate} baud")
    print(f"[*] Writing to {csv_file}")
    print(f"[*] Reading for {duration} seconds... (Ctrl+C to stop early)")
    print("-" * 70)

    buf = bytearray()
    packet_count = 0
    skip_count = 0
    start = datetime.now()

    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()

        try:
            while (datetime.now() - start).total_seconds() < duration:
                if ser.in_waiting > 0:
                    buf.extend(ser.read(ser.in_waiting))

                    while len(buf) >= HEADER_SIZE:
                        # Find magic marker
                        if buf[0] == 0xAA and buf[1] == 0xBB:
                            csi_len = int.from_bytes(buf[28:30], 'little')
                            total = HEADER_SIZE + csi_len * 2  # int16_t = 2 bytes per value

                            if csi_len > 1000:
                                buf = buf[1:]
                                skip_count += 1
                                continue

                            if len(buf) < total:
                                break  # Wait for more data

                            pkt = parse_packet(bytes(buf[:total]))
                            buf = buf[total:]

                            if pkt:
                                writer.writerow(pkt)
                                packet_count += 1
                                if packet_count % 50 == 1:
                                    print(f"[PKT {packet_count:5d}] Seq={pkt['seq']:6d} RSSI={pkt['rssi']:4d}dBm CH={pkt['channel']:2d} CSI_LEN={pkt['len']:4d}")
                        else:
                            buf = buf[1:]
                            skip_count += 1

        except KeyboardInterrupt:
            print("\n[*] Stopped by user")

    ser.close()
    print("-" * 70)
    print(f"[+] Done: {packet_count} packets → {csv_file}")
    if skip_count:
        print(f"[*] Skipped {skip_count} invalid bytes")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read binary CSI from serial → CSV")
    parser.add_argument("--port", "-p", default="/dev/ttyACM0", help="Serial port (default: /dev/ttyACM0)")
    parser.add_argument("--baudrate", "-b", type=int, default=921600, help="Baud rate (default: 921600)")
    parser.add_argument("--duration", "-d", type=int, default=30, help="Duration in seconds (default: 30)")
    parser.add_argument("--csv", "-c", default="csi_output.csv", help="Output CSV file (default: csi_output.csv)")
    
    args = parser.parse_args()
    read_serial_to_csv(port=args.port, baudrate=args.baudrate, duration=args.duration, csv_file=args.csv)
