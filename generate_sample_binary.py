#!/usr/bin/env python3
"""
Generate sample binary CSI data for testing decoder
"""

import struct
from pathlib import Path

# Binary header struct (32 bytes)
def create_csi_packet(seq, mac, rssi, rate, noise_floor, fft_gain, agc_gain, 
                      channel, timestamp, sig_len, rx_state, csi_len, first_word_invalid, csi_data):
    """
    Create a binary CSI packet with header + payload
    
    uint8_t magic[2]           = 0xAA, 0xBB
    uint8_t version            = 1
    uint8_t chip_type          = 2 (ESP32C5)
    uint32_t sequence          (little-endian)
    uint8_t mac[6]            
    int8_t rssi                
    uint8_t rate               
    int8_t noise_floor         
    int8_t fft_gain            
    uint8_t agc_gain           
    uint8_t channel            
    uint16_t timestamp_lo      (little-endian)
    uint16_t timestamp_hi      (little-endian)
    uint16_t sig_len           (little-endian)
    uint16_t rx_state          (little-endian)
    uint16_t csi_len           (little-endian)
    uint8_t first_word_invalid 
    uint8_t reserved           
    [csi_data follows]
    """
    header = bytearray()
    
    # Magic marker
    header.extend([0xAA, 0xBB])
    
    # Version and chip type
    header.append(1)      # version
    header.append(2)      # chip_type ESP32C5
    
    # Sequence (uint32, little-endian)
    header.extend(struct.pack('<I', seq))
    
    # MAC (6 bytes)
    header.extend(bytes(mac))
    
    # RSSI (int8)
    header.append(rssi & 0xFF)
    
    # Rate (uint8)
    header.append(rate)
    
    # Noise floor (int8)
    header.append(noise_floor & 0xFF)
    
    # FFT gain (int8)
    header.append(fft_gain & 0xFF)
    
    # AGC gain (uint8)
    header.append(agc_gain)
    
    # Channel (uint8)
    header.append(channel)
    
    # Timestamp split into lo/hi (uint16, little-endian)
    timestamp_lo = timestamp & 0xFFFF
    timestamp_hi = (timestamp >> 16) & 0xFFFF
    header.extend(struct.pack('<H', timestamp_lo))
    header.extend(struct.pack('<H', timestamp_hi))
    
    # Signal length (uint16, little-endian)
    header.extend(struct.pack('<H', sig_len))
    
    # RX state (uint16, little-endian)
    header.extend(struct.pack('<H', rx_state))
    
    # CSI length (uint16, little-endian)
    header.extend(struct.pack('<H', csi_len))
    
    # First word invalid (uint8)
    header.append(first_word_invalid)
    
    # Reserved (uint8)
    header.append(0)
    
    # Verify header size
    assert len(header) == 32, f"Header size should be 32, got {len(header)}"
    
    # Concatenate header + CSI data
    packet = header + bytes(csi_data)
    return packet

# Generate sample data
if __name__ == "__main__":
    output_file = Path("/home/khanhdew/Documents/VienHLKH/WiVSD/csi_sample.bin")
    
    all_packets = bytearray()
    
    # Create 10 sample packets
    for pkt_idx in range(10):
        # Mock MAC address (1a:00:00:00:00:00)
        mac = bytes([0x1a, 0x00, 0x00, 0x00, 0x00, 0x00])
        
        # Mock CSI data (256 I/Q values, just random int8)
        csi_len = 256
        csi_data = bytearray()
        for i in range(csi_len):
            # Simulate sinusoidal CSI pattern
            import math
            val = int(50 * math.sin(2 * math.pi * i / 64))
            csi_data.append(val & 0xFF)
        
        # Create packet
        packet = create_csi_packet(
            seq=pkt_idx,
            mac=mac,
            rssi=-40 - pkt_idx % 5,  # RSSI between -40 to -45 dBm
            rate=1,
            noise_floor=-100,
            fft_gain=-5,
            agc_gain=50,
            channel=13,
            timestamp=pkt_idx * 10000,
            sig_len=0,
            rx_state=0,
            csi_len=csi_len,
            first_word_invalid=0,
            csi_data=csi_data
        )
        
        all_packets.extend(packet)
        print(f"Packet {pkt_idx}: header=32 bytes, csi={csi_len} bytes, total={len(packet)} bytes")
    
    # Write to file
    output_file.write_bytes(all_packets)
    print(f"\n[+] Generated {len(all_packets)} bytes ({len(all_packets)//(32+256)} packets)")
    print(f"[+] Saved to {output_file}")
    print(f"\nTest decoder:")
    print(f"  python3 csi_binary_decoder.py csi_sample.bin --csv output.csv")
