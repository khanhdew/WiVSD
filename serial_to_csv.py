#!/usr/bin/env python3
"""
Script đọc dữ liệu từ Serial Port và ghi vào file CSV
Dùng cho ESP32-C6 WiFi CSI Data Collection
"""

import serial
import csv
import time
from datetime import datetime
import argparse
import sys

def read_serial_to_csv(port='/dev/ttyUSB0', baudrate=115200, output_file=None, timeout=1):
    """
    Đọc dữ liệu từ serial port và ghi vào CSV file
    
    Args:
        port: Serial port (VD: '/dev/ttyUSB0', 'COM3')
        baudrate: Baud rate (mặc định: 115200)
        output_file: Tên file CSV output (nếu None, tự động tạo theo timestamp)
        timeout: Serial timeout (giây)
    """
    
    # Tạo tên file CSV nếu không được chỉ định
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"csi_data_{timestamp}.csv"
    
    print(f"[INFO] Đang kết nối tới {port} @ {baudrate} baud...")
    
    try:
        # Mở serial port
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        print(f"[SUCCESS] Đã kết nối tới {port}")
        print(f"[INFO] Ghi dữ liệu vào: {output_file}")
        print("[INFO] Nhấn Ctrl+C để dừng...\n")
        
        # Mở file CSV để ghi
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            
            # Ghi header (có thể tùy chỉnh)
            csv_writer.writerow(['timestamp', 'data'])
            
            line_count = 0
            
            try:
                while True:
                    # Đọc một dòng từ serial
                    if ser.in_waiting > 0:
                        try:
                            line = ser.readline().decode('utf-8', errors='ignore').strip()
                            
                            if line:  # Chỉ ghi khi có dữ liệu
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                
                                # Ghi vào CSV
                                csv_writer.writerow([timestamp, line])
                                csvfile.flush()  # Đảm bảo dữ liệu được ghi ngay
                                
                                line_count += 1
                                
                                # Hiển thị tiến trình
                                if line_count % 10 == 0:
                                    print(f"[{line_count}] {timestamp}: {line[:80]}...")
                                    
                        except UnicodeDecodeError as e:
                            print(f"[WARNING] Lỗi decode: {e}")
                            continue
                    
                    time.sleep(0.001)  # Ngủ ngắn để tránh CPU quá tải
                    
            except KeyboardInterrupt:
                print(f"\n[INFO] Đã dừng. Tổng cộng ghi {line_count} dòng.")
                
    except serial.SerialException as e:
        print(f"[ERROR] Lỗi kết nối serial: {e}")
        print(f"[TIP] Kiểm tra:")
        print(f"  - Port {port} có tồn tại không?")
        print(f"  - Thiết bị có được kết nối?")
        print(f"  - Có quyền truy cập? (có thể cần: sudo chmod 666 {port})")
        sys.exit(1)
        
    except Exception as e:
        print(f"[ERROR] Lỗi: {e}")
        sys.exit(1)
        
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("[INFO] Đã đóng kết nối serial.")


def read_serial_to_csv_parsed(port='/dev/ttyUSB0', baudrate=115200, output_file=None, 
                                delimiter=',', timeout=1):
    """
    Đọc dữ liệu từ serial port, parse theo delimiter và ghi vào CSV
    Dùng khi dữ liệu từ ESP32 đã được format sẵn (VD: "value1,value2,value3")
    
    Args:
        port: Serial port
        baudrate: Baud rate
        output_file: Tên file CSV output
        delimiter: Ký tự phân tách trong dữ liệu serial (mặc định: ',')
        timeout: Serial timeout
    """
    
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"csi_data_parsed_{timestamp}.csv"
    
    print(f"[INFO] Đang kết nối tới {port} @ {baudrate} baud...")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        print(f"[SUCCESS] Đã kết nối tới {port}")
        print(f"[INFO] Ghi dữ liệu vào: {output_file}")
        print(f"[INFO] Delimiter: '{delimiter}'")
        print("[INFO] Nhấn Ctrl+C để dừng...\n")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            
            line_count = 0
            header_written = False
            
            try:
                while True:
                    if ser.in_waiting > 0:
                        try:
                            line = ser.readline().decode('utf-8', errors='ignore').strip()
                            
                            if line:
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                
                                # Parse dữ liệu theo delimiter
                                data_parts = line.split(delimiter)
                                
                                # Ghi header tự động từ dòng đầu tiên (nếu có)
                                if not header_written and line_count == 0:
                                    # Kiểm tra xem dòng đầu có phải header không
                                    # (có chứa chữ hoặc bắt đầu bằng #)
                                    if any(c.isalpha() for c in line) or line.startswith('#'):
                                        csv_writer.writerow(['timestamp'] + data_parts)
                                        header_written = True
                                        csvfile.flush()
                                        continue
                                    else:
                                        # Tạo header mặc định
                                        header = ['timestamp'] + [f'col_{i+1}' for i in range(len(data_parts))]
                                        csv_writer.writerow(header)
                                        header_written = True
                                
                                # Ghi dữ liệu
                                csv_writer.writerow([timestamp] + data_parts)
                                csvfile.flush()
                                
                                line_count += 1
                                
                                if line_count % 10 == 0:
                                    print(f"[{line_count}] {timestamp}: {line[:80]}...")
                                    
                        except Exception as e:
                            print(f"[WARNING] Lỗi parse dòng: {e}")
                            continue
                    
                    time.sleep(0.001)
                    
            except KeyboardInterrupt:
                print(f"\n[INFO] Đã dừng. Tổng cộng ghi {line_count} dòng.")
                
    except serial.SerialException as e:
        print(f"[ERROR] Lỗi kết nối serial: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"[ERROR] Lỗi: {e}")
        sys.exit(1)
        
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("[INFO] Đã đóng kết nối serial.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Đọc dữ liệu từ Serial Port và ghi vào CSV file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  # Chế độ cơ bản - ghi toàn bộ dòng vào CSV
  python serial_to_csv.py --port /dev/ttyUSB0 --baudrate 115200
  
  # Chế độ parse - tự động parse dữ liệu có delimiter
  python serial_to_csv.py --port /dev/ttyUSB0 --mode parse --delimiter ","
  
  # Chỉ định file output
  python serial_to_csv.py --port COM3 --output data.csv
        """
    )
    
    parser.add_argument('-p', '--port', 
                        default='/dev/ttyUSB0',
                        help='Serial port (mặc định: /dev/ttyUSB0)')
    
    parser.add_argument('-b', '--baudrate', 
                        type=int,
                        default=115200,
                        help='Baud rate (mặc định: 115200)')
    
    parser.add_argument('-o', '--output',
                        help='File CSV output (mặc định: tự động tạo theo timestamp)')
    
    parser.add_argument('-m', '--mode',
                        choices=['simple', 'parse'],
                        default='simple',
                        help='Chế độ: simple (ghi toàn bộ dòng) hoặc parse (tự động parse)')
    
    parser.add_argument('-d', '--delimiter',
                        default=',',
                        help='Delimiter cho chế độ parse (mặc định: ",")')
    
    parser.add_argument('-t', '--timeout',
                        type=float,
                        default=1.0,
                        help='Serial timeout (giây, mặc định: 1.0)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Serial to CSV Data Logger - ESP32-C6 CSI")
    print("=" * 60)
    
    if args.mode == 'simple':
        read_serial_to_csv(
            port=args.port,
            baudrate=args.baudrate,
            output_file=args.output,
            timeout=args.timeout
        )
    else:
        read_serial_to_csv_parsed(
            port=args.port,
            baudrate=args.baudrate,
            output_file=args.output,
            delimiter=args.delimiter,
            timeout=args.timeout
        )
