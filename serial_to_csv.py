#!/usr/bin/env python3
"""
Script đọc dữ liệu CSI từ Serial Port và ghi vào file CSV
Dành riêng cho ESP32-C5/C6 (15 cột)
Dựa trên csi_data_read_parse.py nhưng bỏ phần UI

Kiến trúc 2-thread producer/consumer:
  - Reader thread: đọc serial + parse → đẩy vào queue
  - Writer thread: lấy từ queue → ghi CSV
  Khi hết duration, reader dừng nhận dữ liệu mới,
  writer drain hết queue rồi mới thoát.
"""

import serial
import csv
import json
import argparse
import sys
import time
import threading
import queue
from io import StringIO
from datetime import datetime

# Expected number of columns from Serial (ESP32-C5/C6)
EXPECTED_CSV_COLUMNS = 15

# CSI data column definitions for CSV file (Added system 'timestamp' at index 0)
DATA_COLUMNS_NAMES = ['timestamp', 'type', 'id', 'mac', 'rssi', 'rate', 'noise_floor', 'fft_gain', 'agc_gain',
                      'channel', 'local_timestamp', 'sig_len', 'rx_state', 'len', 'first_word', 'data']

# Sentinel value to signal writer thread to finish
_SENTINEL = None


def serial_reader_thread(ser, data_queue, log_file_fd, duration, max_count, stats, stop_event, print_func=print):
    """
    Reader thread: đọc từ serial, parse, đẩy parsed rows vào queue.
    Dừng khi hết duration, đủ max_count (CHỈ ĐẾM PACKET HỢP LỆ), hoặc stop_event được set (Ctrl+C).
    """
    start_time = time.time()

    try:
        while not stop_event.is_set():
            # Kiểm tra duration
            if duration is not None:
                elapsed = time.time() - start_time
                if elapsed >= duration:
                    print_func(f'\n[READER] Reached duration limit: {duration}s (elapsed: {elapsed:.2f}s)')
                    break

            # Đọc một dòng từ serial (timeout giúp thoát vòng lặp khi stop_event)
            try:
                if not ser.is_open:
                    break
                if ser.in_waiting == 0:
                    time.sleep(0.01)
                    continue
                raw = ser.readline()
            except (serial.SerialException, AttributeError, TypeError):
                break
            except Exception:
                break
            if not raw:
                continue

            try:
                strings = raw.decode('utf-8', errors='ignore').strip()
            except Exception:
                continue

            # Tìm CSI_DATA
            if strings.find('CSI_DATA') == -1:
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
                stats['invalid'] += 1
                continue

            # Lấy độ dài CSI data
            try:
                csi_data_len = int(csi_data[-3])
            except (ValueError, IndexError):
                if log_file_fd:
                    log_file_fd.write('Invalid csi_data_len\n')
                    log_file_fd.write(strings + '\n')
                    log_file_fd.flush()
                stats['invalid'] += 1
                continue

            # Validate số lượng cột (So với format gốc từ ESP32 là 15 cột)
            if len(csi_data) != EXPECTED_CSV_COLUMNS:
                if log_file_fd:
                    log_file_fd.write('element number is not equal to C5/C6 format\n')
                    log_file_fd.write(strings + '\n')
                    log_file_fd.flush()
                stats['invalid'] += 1
                continue

            # Parse JSON data từ cột cuối
            try:
                csi_raw_data = json.loads(csi_data[-1])
            except json.JSONDecodeError:
                if log_file_fd:
                    log_file_fd.write('data is incomplete\n')
                    log_file_fd.write(strings + '\n')
                    log_file_fd.flush()
                stats['invalid'] += 1
                continue

            # Validate độ dài CSI raw data
            if csi_data_len != len(csi_raw_data):
                if log_file_fd:
                    log_file_fd.write('csi_data_len is not equal\n') 
                    log_file_fd.write(strings + '\n')
                    log_file_fd.flush()
                stats['invalid'] += 1
                continue

            # Thêm system timestamp vào đầu list (epoch format)
            csi_data.insert(0, time.time())

            # Đẩy dữ liệu hợp lệ vào queue, nhưng không để Reader bị treo nếu Writer chết hoặc Queue đầy
            # Ta thử đẩy trong vòng 0.1s, nếu không được thì check stop_event rồi thử tiếp
            success = False
            while not stop_event.is_set():
                try:
                    data_queue.put(csi_data, timeout=0.1)
                    success = True
                    break
                except queue.Full:
                    continue
            
            if success:
                stats['valid_count'] += 1  # CHỈ đếm packet HỢP LỆ, KHÔNG tính invalid

            # Kiểm tra max_count (chỉ dựa trên số packet HỢP LỆ)
            if max_count is not None and stats['valid_count'] >= max_count:
                elapsed = time.time() - start_time
                print_func(f'\n[READER] Reached VALID packet limit: {max_count} in {elapsed:.2f}s')
                print_func(f'[READER] (Invalid packets encountered: {stats["invalid"]} - NOT counted toward limit)')
                break

    except Exception as e:
        print_func(f'[READER] Error: {e}')
    finally:
        stats['elapsed'] = time.time() - start_time
        # Gửi sentinel để writer biết reader đã xong, dùng timeout để tránh treo nếu writer đã dừng
        try:
            if not data_queue.full():
                data_queue.put(_SENTINEL, timeout=0.1)
        except:
            pass
        print_func(f'[READER] Finished – valid packets: {stats["valid_count"]}, '
              f'invalid packets: {stats["invalid"]} (not counted), '
              f'elapsed: {stats["elapsed"]:.2f}s')


def csv_writer_thread(data_queue, csv_writer, save_file_fd, stats, print_func=print):
    """
    Writer thread: lấy parsed rows từ queue và ghi vào CSV.
    Tiếp tục chạy cho đến khi nhận sentinel (reader đã xong) VÀ queue rỗng.
    """
    written = 0

    try:
        while True:
            try:
                item = data_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if item is _SENTINEL:
                # Drain các phần tử còn lại trong queue
                while not data_queue.empty():
                    remaining = data_queue.get_nowait()
                    if remaining is not _SENTINEL:
                        csv_writer.writerow(remaining)
                        written += 1
                break

            csv_writer.writerow(item)
            written += 1

            # Flush mỗi 50 dòng để giảm I/O overhead nhưng vẫn persist
            if written % 50 == 0:
                save_file_fd.flush()

            # Hiển thị tiến trình
            if written % 100 == 0:
                pending = data_queue.qsize()
                print_func(f'[WRITER] {written} rows written (queue: ~{pending} pending)')

    except Exception as e:
        print_func(f'[WRITER] Error: {e}')
    finally:
        save_file_fd.flush()
        stats['written'] = written
        print_func(f'[WRITER] Finished – {written} rows written to CSV')


def csi_data_read_parse(port, csv_writer, save_file_fd, log_file_fd=None, duration=None, max_count=None, stop_event=None, baudrate=2000000, print_func=print):
    """
    Khởi chạy 2 thread: reader (serial→queue) và writer (queue→CSV).
    """
    ser = serial.Serial(port=port, baudrate=baudrate, bytesize=8, parity='N', stopbits=1,
                        timeout=0.1)  # timeout cho readline để reader thread có thể thoát

    if ser.isOpen():
        print_func('[SUCCESS] Serial port opened successfully')
    else:
        print_func('[ERROR] Failed to open serial port')
        return

    data_queue = queue.Queue(maxsize=2000)
    if stop_event is None:
        stop_event = threading.Event()
    # valid_count: chỉ đếm packet HỢP LỆ (đã pass validation), KHÔNG tính invalid
    stats = {'valid_count': 0, 'invalid': 0, 'written': 0, 'elapsed': 0.0}

    reader = threading.Thread(
        target=serial_reader_thread,
        args=(ser, data_queue, log_file_fd, duration, max_count, stats, stop_event, print_func),
        name='csi-reader',
        daemon=True
    )
    writer = threading.Thread(
        target=csv_writer_thread,
        args=(data_queue, csv_writer, save_file_fd, stats, print_func),
        name='csi-writer',
        daemon=True
    )

    reader.start()
    writer.start()

    def force_close_serial(s):
        """Hàm này chạy trong luồng riêng để nếu driver treo cũng không làm đứng GUI"""
        try:
            if s and s.is_open:
                if hasattr(s, 'cancel_read'): s.cancel_read()
                s.close()
        except:
            pass

    try:
        # Chờ reader xong HOẶC stop_event được set
        # KHÔNG dùng join() vì join() có thể treo driver
        while reader.is_alive():
            if stop_event.is_set():
                break
            time.sleep(0.1)
        
        # Nếu dừng do stop_event, ta "vứt" việc đóng port cho một luồng riêng
        # Luồng chính (GUI) sẽ đi tiếp ngay lập tức
        closer_thread = threading.Thread(target=force_close_serial, args=(ser,), daemon=True)
        closer_thread.start()

        # Gửi tín hiệu dừng cho writer (không chờ)
        try:
            data_queue.put_nowait(_SENTINEL)
        except:
            pass

        # Thoát ngay lập tức, không join() bất cứ thứ gì
        print_func('[INFO] Session logic finished, returning control to GUI.')
        
    except Exception as e:
        print_func(f'[ERROR] Critical error in session: {e}')
    finally:
        # Thống kê nhanh và thoát
        print_func(f'[DONE] Packets logged: {stats["valid_count"]}')
        
        print_func(f'[STATS] Duration: {stats["elapsed"]:.2f}s | '
              f'Valid packets: {stats["valid_count"]} | '
              f'Written to CSV: {stats["written"]} | '
              f'Invalid (not counted): {stats["invalid"]} | '
              f'Dropped: {stats["valid_count"] - stats["written"]}')


if __name__ == "__main__":
    if sys.version_info < (3, 6):
        print('[ERROR] Python version should >= 3.6')
        exit()

    parser = argparse.ArgumentParser(
        description='Đọc và parse dữ liệu CSI từ Serial Port, ghi vào CSV file (multi-threaded)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  # Đọc từ /dev/ttyUSB0 và ghi vào file mặc định
  python serial_to_csv.py -p /dev/ttyUSB0

  # Thu thập dữ liệu trong 40 giây
  python serial_to_csv.py -p /dev/ttyUSB0 -d 40

  # Thu thập đúng 4000 packet
  python serial_to_csv.py -p /dev/ttyUSB0 -n 4000

  # Kết hợp: tối đa 40s HOẶC 4000 packet (cái nào đến trước)
  python serial_to_csv.py -p /dev/ttyUSB0 -d 40 -n 4000

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

    parser.add_argument('-n', '--count',
                        dest='max_count',
                        action='store',
                        type=int,
                        default=None,
                        help='Số lượng packet tối đa cần thu. VD: 4000 (mặc định: không giới hạn)')

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
    print("CSI Data Logger - ESP32-C5/C6 (15 columns) [Multi-threaded]")
    print("=" * 70)
    print(f"[CONFIG] Serial port: {serial_port}")
    print(f"[CONFIG] Baudrate: 2000000")
    print(f"[CONFIG] CSV output: {file_name}")
    if log_file_name:
        print(f"[CONFIG] Log output: {log_file_name}")
    else:
        print(f"[CONFIG] Log output: disabled")
    if args.duration:
        print(f"[CONFIG] Duration: {args.duration}s")
    else:
        print(f"[CONFIG] Duration: unlimited")
    if args.max_count:
        print(f"[CONFIG] Max packets: {args.max_count}")
    else:
        print(f"[CONFIG] Max packets: unlimited")
    if not args.duration and not args.max_count:
        print(f"[CONFIG] Stop: Ctrl+C")
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

        # Bắt đầu đọc và parse dữ liệu (multi-threaded)
        csi_data_read_parse(serial_port, csv_writer, save_file_fd, log_file_fd, args.duration, args.max_count, baudrate=2000000)

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
