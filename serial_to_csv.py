#!/usr/bin/env python3
"""
Script đọc dữ liệu CSI từ Serial Port và ghi vào file CSV
Dành riêng cho ESP32-C5/C6 (15 cột)
Dựa trên csi_data_read_parse.py nhưng bỏ phần UI
"""

import serial
import csv
import json
import argparse
import sys
import time
from io import StringIO
from datetime import datetime

# CSI data column definitions for ESP32-C5/C6
DATA_COLUMNS_NAMES = ['type', 'id', 'mac', 'rssi', 'rate', 'noise_floor', 'fft_gain', 'agc_gain', 
                      'channel', 'local_timestamp', 'sig_len', 'rx_state', 'len', 'first_word', 'data']


def csi_data_read_parse(port, csv_writer, log_file_fd=None, duration=None):
    """
    Đọc và parse dữ liệu CSI từ serial port
    
    Args:
        port: Serial port path
        csv_writer: CSV writer object để ghi dữ liệu hợp lệ
        log_file_fd: File descriptor để ghi log các dòng không hợp lệ (optional)
        duration: Thời gian thu thập dữ liệu tính bằng giây (None = không giới hạn)
    """
    
    # Mở serial với baudrate 921600 như trong csi_data_read_parse.py
    ser = serial.Serial(port=port, baudrate=2000000, bytesize=8, parity='N', stopbits=1)
    
    if ser.isOpen():
        print('[SUCCESS] Serial port opened successfully')
    else:
        print('[ERROR] Failed to open serial port')
        return
    
    valid_count = 0
    invalid_count = 0
    start_time = time.time() if duration else None
    
    try:
        while True:
            # Kiểm tra thời gian nếu có giới hạn duration
            if duration is not None:
                elapsed = time.time() - start_time
                if elapsed >= duration:
                    print(f'\n[INFO] Reached duration limit: {duration}s (elapsed: {elapsed:.2f}s)')
                    break
            # Đọc một dòng từ serial
            strings = str(ser.readline())
            if not strings:
                break
                
            # Xử lý string format từ serial
            strings = strings.lstrip('b\'').rstrip('\\r\\n\'')
            
            # Tìm CSI_DATA trong string
            index = strings.find('CSI_DATA')
            
            # Nếu không phải CSI_DATA, ghi vào log file (nếu có)
            if index == -1:
                if log_file_fd:
                    log_file_fd.write(strings + '\n')
                    log_file_fd.flush()
                continue
            
            # Parse CSV data
            csv_reader = csv.reader(StringIO(strings))
            try:
                csi_data = next(csv_reader)
            except StopIteration:
                if log_file_fd:
                    log_file_fd.write('CSV parse error: empty data\n')
                    log_file_fd.write(strings + '\n')
                    log_file_fd.flush()
                invalid_count += 1
                continue
            
            # Lấy độ dài CSI data
            try:
                csi_data_len = int(csi_data[-3])
            except (ValueError, IndexError):
                if log_file_fd:
                    log_file_fd.write('Invalid csi_data_len\n')
                    log_file_fd.write(strings + '\n')
                    log_file_fd.flush()
                invalid_count += 1
                continue
            
            # Validate số lượng cột (chỉ chấp nhận ESP32-C5/C6 format)
            if len(csi_data) != len(DATA_COLUMNS_NAMES):
                print(f'[WARNING] Column count mismatch: got {len(csi_data)}, expected {len(DATA_COLUMNS_NAMES)} (C5/C6 format)')
                if log_file_fd:
                    log_file_fd.write('element number is not equal to C5/C6 format\n')
                    log_file_fd.write(strings + '\n')
                    log_file_fd.flush()
                invalid_count += 1
                continue
            
            # Parse JSON data từ cột cuối
            try:
                csi_raw_data = json.loads(csi_data[-1])
            except json.JSONDecodeError:
                print('[WARNING] JSON decode error - data is incomplete')
                if log_file_fd:
                    log_file_fd.write('data is incomplete\n')
                    log_file_fd.write(strings + '\n')
                    log_file_fd.flush()
                invalid_count += 1
                continue
            
            # Validate độ dài CSI raw data
            if csi_data_len != len(csi_raw_data):
                print(f'[WARNING] CSI data length mismatch: expected {csi_data_len}, got {len(csi_raw_data)}')
                if log_file_fd:
                    log_file_fd.write('csi_data_len is not equal\n')
                    log_file_fd.write(strings + '\n')
                    log_file_fd.flush()
                invalid_count += 1
                continue
            
            # Dữ liệu hợp lệ - ghi vào CSV
            csv_writer.writerow(csi_data)
            valid_count += 1
            
            # Hiển thị tiến trình mỗi 100 dòng hợp lệ
            if valid_count % 100 == 0:
                print(f'[{valid_count}] Valid CSI packets received (Invalid: {invalid_count})')
                
    except KeyboardInterrupt:
        print(f'\n[INFO] Stopped by user')
        if start_time:
            elapsed = time.time() - start_time
            print(f'[STATS] Duration: {elapsed:.2f}s')
        print(f'[STATS] Valid packets: {valid_count}, Invalid packets: {invalid_count}')
        
    finally:
        ser.close()
        print('[INFO] Serial port closed')


if __name__ == "__main__":
    if sys.version_info < (3, 6):
        print('[ERROR] Python version should >= 3.6')
        exit()
    
    parser = argparse.ArgumentParser(
        description='Đọc và parse dữ liệu CSI từ Serial Port, ghi vào CSV file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  # Đọc từ /dev/ttyUSB0 và ghi vào file mặc định
  python serial_to_csv.py -p /dev/ttyUSB0
  
  # Thu thập dữ liệu trong 40 giây
  python serial_to_csv.py -p /dev/ttyUSB0 -d 40
  
  # Chỉ định file output cụ thể
  python serial_to_csv.py -p /dev/ttyUSB0 -s my_csi_data.csv -l my_log.txt
  
  # Trên Windows
  python serial_to_csv.py -p COM3 -s csi_data.csv
        """
    )
    
    parser.add_argument('-p', '--port', 
                        dest='port',
                        action='store',
                        required=True,
                        help='Serial port (VD: /dev/ttyUSB0, COM3)')
    
    parser.add_argument('-s', '--store',
                        dest='store_file',
                        action='store',
                        default=None,
                        help='File CSV để lưu dữ liệu CSI hợp lệ (mặc định: tự động tạo theo timestamp)')
    
    parser.add_argument('-l', '--log',
                        dest='log_file',
                        action='store',
                        default=None,
                        help='File log để lưu dữ liệu không hợp lệ (mặc định: không ghi log)')
    
    parser.add_argument('-d', '--duration',
                        dest='duration',
                        action='store',
                        type=float,
                        default=None,
                        help='Thời gian thu thập dữ liệu (giây). VD: 40, 60.5 (mặc định: không giới hạn)')
    
    args = parser.parse_args()
    serial_port = args.port
    
    # Tự động tạo tên file theo timestamp nếu không chỉ định
    if args.store_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"csi_data_{timestamp}.csv"
    else:
        file_name = args.store_file
    
    log_file_name = args.log_file
    
    print("=" * 70)
    print("CSI Data Logger - ESP32-C5/C6 Only (15 columns)")
    print("Based on esp-csi csi_data_read_parse.py (No GUI)")
    print("=" * 70)
    print(f"[CONFIG] Serial port: {serial_port}")
    print(f"[CONFIG] Baudrate: 921600")
    print(f"[CONFIG] CSV output: {file_name}")
    if log_file_name:
        print(f"[CONFIG] Log output: {log_file_name}")
    else:
        print(f"[CONFIG] Log output: disabled")
    if args.duration:
        print(f"[CONFIG] Duration: {args.duration}s")
    else:
        print(f"[CONFIG] Duration: unlimited")
    print("=" * 70)
    print("[INFO] Press Ctrl+C to stop...\n")
    
    try:
        # Mở file CSV để ghi
        save_file_fd = open(file_name, 'w', newline='')
        csv_writer = csv.writer(save_file_fd)
        
        # Ghi header cho ESP32-C5/C6
        csv_writer.writerow(DATA_COLUMNS_NAMES)
        
        # Mở file log (nếu được chỉ định)
        log_file_fd = None
        if log_file_name:
            log_file_fd = open(log_file_name, 'w')
        
        # Bắt đầu đọc và parse dữ liệu
        csi_data_read_parse(serial_port, csv_writer, log_file_fd, args.duration)
        
    except serial.SerialException as e:
        print(f'\n[ERROR] Serial error: {e}')
        print(f'[TIP] Kiểm tra:')
        print(f'  - Port {serial_port} có tồn tại?')
        print(f'  - Thiết bị đã kết nối?')
        print(f'  - Có quyền truy cập? (thử: sudo chmod 666 {serial_port})')
        sys.exit(1)
        
    except FileNotFoundError as e:
        print(f'\n[ERROR] File error: {e}')
        sys.exit(1)
        
    except Exception as e:
        print(f'\n[ERROR] Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        # Đóng các file
        if 'save_file_fd' in locals():
            save_file_fd.close()
            print(f'[INFO] Saved CSI data to: {file_name}')
        if 'log_file_fd' in locals() and log_file_fd:
            log_file_fd.close()
            print(f'[INFO] Saved log to: {log_file_name}')
