#!/usr/bin/env python3
"""
CSI Binary Protocol Decoder
Converts binary CSI packets to CSV or JSON
"""

import struct
import sys
from pathlib import Path
from typing import List, Tuple

# Binary packet structure (28 bytes header)
CSI_BINARY_HEADER_FORMAT = '<BBBBIB6BbbBBBBHHHBB'
CSI_BINARY_HEADER_SIZE = 28

CHIP_TYPES = {
    0: "ESP32",
    1: "ESP32C6",
    2: "ESP32C5/C61",
}

class CSIBinaryPacket:
    def __init__(self, data: bytes):
        """Parse binary CSI packet"""
        if len(data) < CSI_BINARY_HEADER_SIZE:
            raise ValueError(f"Packet too short: {len(data)} < {CSI_BINARY_HEADER_SIZE}")
        
        # Unpack header
        header_data = data[:CSI_BINARY_HEADER_SIZE]
        (magic0, magic1, version, chip_type, sequence, mac0, mac1, mac2, mac3, mac4, mac5,
         rssi, rate, noise_floor, fft_gain, agc_gain, channel, bandwidth,
         timestamp_lo, timestamp_hi, csi_len, first_word_invalid, reserved) = \
            struct.unpack(CSI_BINARY_HEADER_FORMAT, header_data)
        
        # Validate magic
        if magic0 != 0xAA or magic1 != 0xBB:
            raise ValueError(f"Invalid magic: 0x{magic0:02X}{magic1:02X}")
        
        self.version = version
        self.chip_type = CHIP_TYPES.get(chip_type, f"Unknown({chip_type})")
        self.sequence = sequence
        self.mac = f"{mac0:02X}:{mac1:02X}:{mac2:02X}:{mac3:02X}:{mac4:02X}:{mac5:02X}"
        self.rssi = rssi
        self.rate = rate
        self.noise_floor = noise_floor
        self.fft_gain = fft_gain
        self.agc_gain = agc_gain
        self.channel = channel
        self.bandwidth = ["20MHz", "40MHz", "80MHz", "160MHz"][bandwidth & 0x03] if bandwidth < 4 else f"BW{bandwidth}"
        self.timestamp = (timestamp_hi << 16) | timestamp_lo
        self.csi_len = csi_len
        self.first_word_invalid = first_word_invalid
        
        # Extract CSI data
        csi_start = CSI_BINARY_HEADER_SIZE
        csi_end = csi_start + csi_len
        
        if len(data) < csi_end:
            raise ValueError(f"Incomplete CSI data: got {len(data)}, need {csi_end}")
        
        csi_raw = data[csi_start:csi_end]
        self.csi = struct.unpack(f'<{csi_len}b', csi_raw)  # signed int8
    
    def to_csv_row(self) -> str:
        """Convert to CSV row"""
        csi_str = ','.join(str(x) for x in self.csi)
        return f"{self.sequence},{self.mac},{self.rssi},{self.rate},{self.noise_floor},{self.fft_gain},{self.agc_gain},{self.channel},{self.bandwidth},{self.timestamp},{self.csi_len},{self.first_word_invalid},\"{csi_str}\""
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'sequence': self.sequence,
            'chip': self.chip_type,
            'mac': self.mac,
            'rssi': self.rssi,
            'rate': self.rate,
            'noise_floor': self.noise_floor,
            'fft_gain': self.fft_gain,
            'agc_gain': self.agc_gain,
            'channel': self.channel,
            'bandwidth': self.bandwidth,
            'timestamp': self.timestamp,
            'csi_len': self.csi_len,
            'first_word_invalid': bool(self.first_word_invalid),
            'csi': list(self.csi)
        }
    
    def __repr__(self):
        return f"CSI(seq={self.sequence}, mac={self.mac}, rssi={self.rssi}, csi_len={self.csi_len})"


def read_binary_csi_stream(file_path: str, mode: int = 1) -> List[CSIBinaryPacket]:
    """
    Read binary CSI stream from UART serial file
    
    mode: 1 = Binary compact (no sync markers)
          2 = Binary + sync markers (0xBBAA at start/end)
    """
    packets = []
    
    with open(file_path, 'rb') as f:
        data = f.read()
    
    print(f"[*] Read {len(data)} bytes from {file_path}")
    print(f"[*] Mode: {mode}, Expected header size: {CSI_BINARY_HEADER_SIZE} bytes\n")
    
    pos = 0
    packet_count = 0
    error_count = 0
    
    while pos < len(data):
        # Look for magic marker (0xAABB)
        if data[pos:pos+2] == b'\xAA\xBB':
            # Found header start
            try:
                # Determine packet size by reading header first
                if pos + CSI_BINARY_HEADER_SIZE > len(data):
                    print(f"[!] Incomplete header at offset {pos}")
                    break
                
                # Peek at csi_len field (offset +24 in header)
                csi_len_bytes = data[pos+24:pos+26]
                if len(csi_len_bytes) == 2:
                    csi_len = struct.unpack('<H', csi_len_bytes)[0]
                    
                    # Sanity check: CSI length should be reasonable (< 1000)
                    if csi_len > 1000:
                        print(f"[!] Invalid CSI length {csi_len} at offset {pos}, skipping")
                        error_count += 1
                        pos += 1
                        continue
                    
                    # Check if packet is complete
                    packet_end = pos + CSI_BINARY_HEADER_SIZE + csi_len
                    if mode == 2:
                        packet_end += 2  # Trailing sync marker
                    
                    if packet_end <= len(data):
                        packet_data = data[pos:packet_end]
                        
                        try:
                            packet = CSIBinaryPacket(packet_data)
                            packets.append(packet)
                            packet_count += 1
                            pos = packet_end
                            continue
                        except ValueError as e:
                            print(f"[!] Error parsing packet at {pos}: {e}")
                            error_count += 1
                            pos += 1
                    else:
                        print(f"[!] Incomplete packet at offset {pos} (need {packet_end - len(data)} more bytes)")
                        break
                else:
                    pos += 1
            except Exception as e:
                print(f"[!] Error at offset {pos}: {e}")
                error_count += 1
                pos += 1
        else:
            pos += 1
    
    print(f"[+] Parsed {packet_count} valid packets")
    if error_count > 0:
        print(f"[!] {error_count} errors/malformed packets\n")
    else:
        print()
    
    return packets


def save_as_csv(packets: List[CSIBinaryPacket], output_file: str = None):
    """Save packets as CSV"""
    if output_file is None:
        output_file = Path('csi_binary_output.csv')
    else:
        output_file = Path(output_file)
    
    with open(output_file, 'w') as f:
        # Header
        f.write("sequence,mac,rssi,rate,noise_floor,fft_gain,agc_gain,channel,bandwidth,timestamp,csi_len,first_word_invalid,csi_data\n")
        
        # Rows
        for packet in packets:
            f.write(packet.to_csv_row() + '\n')
    
    print(f"[+] Saved {len(packets)} packets to {output_file}")


def save_as_json(packets: List[CSIBinaryPacket], output_file: str = None):
    """Save packets as JSON"""
    import json
    
    if output_file is None:
        output_file = Path('csi_binary_output.json')
    else:
        output_file = Path(output_file)
    
    data = [p.to_dict() for p in packets]
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"[+] Saved {len(packets)} packets to {output_file}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 csi_binary_decoder.py <input_binary_file> [--csv output.csv] [--json output.json] [--mode 1|2]")
        print("\nmode: 1 = Binary compact (default)")
        print("      2 = Binary + sync markers")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_csv = None
    output_json = None
    mode = 1
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--csv' and i+1 < len(sys.argv):
            output_csv = sys.argv[i+1]
            i += 2
        elif sys.argv[i] == '--json' and i+1 < len(sys.argv):
            output_json = sys.argv[i+1]
            i += 2
        elif sys.argv[i] == '--mode' and i+1 < len(sys.argv):
            mode = int(sys.argv[i+1])
            i += 2
        else:
            i += 1
    
    print(f"\n[*] CSI Binary Decoder v1.0")
    print(f"[*] Input: {input_file}")
    print(f"[*] Mode: {mode}\n")
    
    # Parse binary stream
    packets = read_binary_csi_stream(input_file, mode=mode)
    
    if packets:
        print("--- First 3 packets ---")
        for i, p in enumerate(packets[:3]):
            print(f"{i+1}. {p}")
        
        # Save outputs
        if output_csv:
            save_as_csv(packets, output_csv)
        else:
            save_as_csv(packets)
        
        if output_json:
            save_as_json(packets, output_json)
    else:
        print("[!] No packets found")


if __name__ == '__main__':
    main()
