#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial.tools.list_ports
import threading
import time
import os
import csv
from datetime import datetime
from collections import defaultdict
from serial_to_csv import csi_data_read_parse, DATA_COLUMNS_NAMES
from weather_collector import collect_loop, default_csv_filename as weather_csv_filename

class CSILoggerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 CSI Logger GUI")
        self.root.geometry("600x800")
        
        self.stop_event = threading.Event()
        self.is_running = False
        self.weather_thread = None
        
        self.create_widgets()
        self.refresh_ports()

    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="CSI Data Logger Configuration", font=("Helvetica", 14, "bold"))
        title_label.pack(pady=10)

        # Serial Configuration
        serial_group = ttk.LabelFrame(main_frame, text="Serial Configuration", padding="10")
        serial_group.pack(fill=tk.X, pady=5)

        ttk.Label(serial_group, text="Port:").grid(row=0, column=0, sticky=tk.W)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(serial_group, textvariable=self.port_var, width=30)
        self.port_combo.grid(row=0, column=1, padx=5)
        
        ttk.Button(serial_group, text="Refresh", command=self.refresh_ports).grid(row=0, column=2)

        ttk.Label(serial_group, text="Baudrate:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.baudrate_var = tk.StringVar(value="2000000")
        self.baudrate_combo = ttk.Combobox(serial_group, textvariable=self.baudrate_var, values=["115200", "921600", "2000000"], width=30)
        self.baudrate_combo.grid(row=1, column=1, padx=5, pady=5)

        # Data Configuration
        data_group = ttk.LabelFrame(main_frame, text="Data Configuration", padding="10")
        data_group.pack(fill=tk.X, pady=5)

        ttk.Label(data_group, text="Duration (s):").grid(row=0, column=0, sticky=tk.W)
        self.duration_var = tk.StringVar(value="None")
        ttk.Entry(data_group, textvariable=self.duration_var).grid(row=0, column=1, padx=5)
        ttk.Label(data_group, text="(leave 'None' for unlimited)").grid(row=0, column=2, sticky=tk.W)

        ttk.Label(data_group, text="Max Packets:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.max_count_var = tk.StringVar(value="None")
        ttk.Entry(data_group, textvariable=self.max_count_var).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(data_group, text="(leave 'None' for unlimited)").grid(row=1, column=2, sticky=tk.W)

        # Scheduling
        schedule_group = ttk.LabelFrame(main_frame, text="Scheduling & Intervals", padding="10")
        schedule_group.pack(fill=tk.X, pady=5)

        ttk.Label(schedule_group, text="Delay Start (min):").grid(row=0, column=0, sticky=tk.W)
        self.delay_var = tk.DoubleVar(value=0.0)
        ttk.Entry(schedule_group, textvariable=self.delay_var, width=10).grid(row=0, column=1, padx=5, sticky=tk.W)

        ttk.Label(schedule_group, text="Repeat every (min):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.interval_var = tk.DoubleVar(value=0.0)
        ttk.Entry(schedule_group, textvariable=self.interval_var, width=10).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(schedule_group, text="(0 = repeat immediately, 0.1 = 6s)").grid(row=1, column=2, sticky=tk.W)

        # Storage
        storage_group = ttk.LabelFrame(main_frame, text="Storage", padding="10")
        storage_group.pack(fill=tk.X, pady=5)

        ttk.Label(storage_group, text="Output Directory:").grid(row=0, column=0, sticky=tk.W)
        self.dir_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(storage_group, textvariable=self.dir_var, width=40).grid(row=0, column=1, padx=5)
        ttk.Button(storage_group, text="Browse", command=self.browse_dir).grid(row=0, column=2)

        # Weather Collector
        weather_group = ttk.LabelFrame(main_frame, text="Weather Collector (UDP + Open-Meteo)", padding="10")
        weather_group.pack(fill=tk.X, pady=5)

        self.weather_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(weather_group, text="Enable Weather Collection", variable=self.weather_enabled).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)

        ttk.Label(weather_group, text="Weather API Interval (s):").grid(row=1, column=0, sticky=tk.W)
        self.weather_interval_var = tk.StringVar(value="60")
        ttk.Entry(weather_group, textvariable=self.weather_interval_var, width=10).grid(row=1, column=1, padx=5, sticky=tk.W)

        ttk.Label(weather_group, text="UDP Port:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.udp_port_var = tk.StringVar(value="12345")
        ttk.Entry(weather_group, textvariable=self.udp_port_var, width=10).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(weather_group, text="(UDP messages: temp_in,humi_in)").grid(row=2, column=2, sticky=tk.W)

        # Controls (Moved up for visibility)
        control_frame = ttk.Frame(main_frame, padding="10")
        control_frame.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(control_frame, text="START LOGGING", command=self.start_logging)
        self.start_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.stop_btn = ttk.Button(control_frame, text="STOP", command=self.stop_logging, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Status / Log
        status_group = ttk.LabelFrame(main_frame, text="Status & Logs", padding="10")
        status_group.pack(fill=tk.BOTH, expand=True, pady=5)

        self.status_text = tk.Text(status_group, height=12, state=tk.DISABLED, bg="#f0f0f0")
        self.status_text.pack(fill=tk.BOTH, expand=True)

        # Bottom info
        ttk.Label(main_frame, text="ESP32-C5/C6 CSI Logger v1.0", foreground="gray").pack(side=tk.BOTTOM)

    def log(self, message):
        # Ensure log updates are scheduled on the main thread
        self.root.after(0, self._perform_log, message)

    def _perform_log(self, message):
        try:
            self.status_text.config(state=tk.NORMAL)
            msg_str = str(message).strip()
            self.status_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg_str}\n")
            self.status_text.see(tk.END)
            self.status_text.config(state=tk.DISABLED)
        except Exception:
            pass # Avoid crashing GUI loop if logging fails

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            # Prefer /dev/ttyACM0 if available, otherwise select first
            if '/dev/ttyACM0' in ports:
                self.port_combo.set('/dev/ttyACM0')
            else:
                self.port_combo.current(0)

    def browse_dir(self):
        directory = filedialog.askdirectory(initialdir=self.dir_var.get())
        if directory:
            self.dir_var.set(directory)

    def start_logging(self):
        if self.is_running:
            return

        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Please select a serial port.")
            return

        # Parse parameters
        try:
            baudrate = int(self.baudrate_var.get())
            duration = None if self.duration_var.get().lower() == 'none' else float(self.duration_var.get())
            max_count = None if self.max_count_var.get().lower() == 'none' else int(self.max_count_var.get())
            delay = self.delay_var.get()
            interval = self.interval_var.get()
            weather_interval = int(self.weather_interval_var.get())
            udp_port = int(self.udp_port_var.get())
        except ValueError:
            messagebox.showerror("Error", "Check your parameter formats (numbers needed).")
            return

        self.is_running = True
        self.stop_event.clear() # PHẢI CÓ dòng này để có thể bắt đầu lại
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # Run scheduler in a separate thread
        t = threading.Thread(target=self.logging_scheduler, args=(port, baudrate, duration, max_count, delay, interval, weather_interval, udp_port), daemon=True)
        t.start()

    def logging_scheduler(self, port, baudrate, duration, max_count, delay, interval, weather_interval, udp_port):
        try:
            if delay > 0:
                self.log(f"Delaying start for {delay} minutes...")
                # Sleep in chunks to check for stop_event (use 0.1s granularity)
                start_delay = time.time()
                while time.time() - start_delay < delay * 60:
                    if self.stop_event.is_set():
                        self.log("Scheduled start cancelled.")
                        return
                    time.sleep(0.1)

            first_run = True
            while True:
                if not first_run and interval >= 0:
                    # Convert interval (in minutes) to seconds
                    interval_secs = interval * 60
                    if interval_secs > 0:
                        self.log(f"Waiting for next interval: {interval} min ({interval_secs:.1f}s)...")
                        start_wait = time.time()
                        # Use finer granularity (0.1s) for accurate small intervals
                        while time.time() - start_wait < interval_secs:
                            if self.stop_event.is_set():
                                self.log("Interval recording stopped.")
                                return
                            time.sleep(0.1)  # More responsive than 1s
                    else:
                        self.log("No wait - repeating immediately")
                
                if self.stop_event.is_set():
                    break

                # Thêm log để biết đang ở bước nào
                self.log(f"DEBUG: Starting session core logic...")
                self.run_one_session(port, baudrate, duration, max_count, weather_interval, udp_port)
                self.log(f"DEBUG: Session core logic returned.")
                
                first_run = False
                if interval < 0:
                    break

        except Exception as e:
            self.log(f"Scheduler Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            # Trả lại trạng thái cho các nút bấm
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            self.log("FINISH: Logging system is now idle.")

    def run_one_session(self, port, baudrate, duration, max_count, weather_interval, udp_port):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csi_file_path = os.path.join(self.dir_var.get(), f"csi_data_{timestamp}.csv")
        weather_file_path = os.path.join(self.dir_var.get(), f".weather_tmp_{timestamp}.csv")  # Temp file
        
        self.log(f"Starting session: {csi_file_path}")
        
        # Start weather collector thread if enabled
        weather_thread = None
        if self.weather_enabled.get():
            self.log(f"Starting weather collector (background)...")
            try:
                weather_thread = threading.Thread(
                    target=self._run_weather_collector,
                    args=(weather_file_path, weather_interval, udp_port),
                    daemon=True
                )
                weather_thread.start()
            except Exception as e:
                self.log(f"WARNING: Failed to start weather collector: {e}")
        
        try:
            with open(csi_file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(DATA_COLUMNS_NAMES)
                
                # Execute core logic from serial_to_csv with GUI logger
                csi_data_read_parse(
                    port=port,
                    csv_writer=writer,
                    save_file_fd=f,
                    duration=duration,
                    max_count=max_count,
                    stop_event=self.stop_event,
                    baudrate=baudrate,
                    print_func=self.log
                )
            self.log(f"SUCCESS: CSI data collected. Saved to: {csi_file_path}")
        except Exception as e:
            self.log(f"ERROR: CSI session failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Stop weather collector if running
            if weather_thread is not None and self.weather_enabled.get():
                self.log("Stopping weather collector...")
                self.stop_event.set()
                weather_thread.join(timeout=3)  # Wait for weather collector to finish
                
                # Merge weather data into CSI file
                time.sleep(1)  # Give file time to close
                try:
                    self.log("Merging weather data into CSI file...")
                    self._merge_weather_to_csi(csi_file_path, weather_file_path)
                    if os.path.exists(weather_file_path):
                        os.remove(weather_file_path)
                    self.log("SUCCESS: Files merged!")
                    time.sleep(0.5)  # Extra delay to ensure merge complete before next session
                except Exception as e:
                    self.log(f"WARNING: Merge failed: {e}")
                finally:
                    # Clear stop_event so next session can repeat
                    self.stop_event.clear()
            
            self.log(f"DEBUG: run_one_session for {timestamp} clean exit.")

    def _run_weather_collector(self, weather_file_path, interval, udp_port):
        """Run weather collector in a separate thread."""
        try:
            self.log(f"DEBUG: Weather collector starting on port {udp_port}...")
            
            collect_loop(
                csv_file=weather_file_path,
                interval=interval,
                stop_event=self.stop_event,
                scenarios=[],
                udp_port=udp_port
            )
            
            self.log("DEBUG: Weather collector finished")
        except Exception as e:
            self.log(f"ERROR in weather collector: {e}")
            import traceback
            traceback.print_exc()

    def _merge_weather_to_csi(self, csi_file, weather_file):
        """Merge weather data into CSI file by timestamp alignment."""
        # Read weather data
        weather_data = {}
        
        self.log(f"DEBUG: Checking weather file: {weather_file}")
        self.log(f"DEBUG: Weather file exists: {os.path.exists(weather_file)}")
        
        if not os.path.exists(weather_file):
            self.log("WARNING: No weather file to merge - skipping merge")
            return
        
        try:
            with open(weather_file, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)
                time_idx = header.index('time') if 'time' in header else 0
                temp_in_idx = header.index('temp_in') if 'temp_in' in header else -1
                humi_in_idx = header.index('humi_in') if 'humi_in' in header else -1
                temp_out_idx = header.index('temp_out') if 'temp_out' in header else -1
                humi_out_idx = header.index('humi_out') if 'humi_out' in header else -1
                
                self.log(f"DEBUG: Weather header indices - time:{time_idx}, temp_in:{temp_in_idx}, humi_in:{humi_in_idx}, temp_out:{temp_out_idx}, humi_out:{humi_out_idx}")
                
                row_count = 0
                for row in reader:
                    if len(row) > time_idx:
                        try:
                            ts = int(row[time_idx])
                            weather_data[ts] = {
                                'temp_in': row[temp_in_idx] if temp_in_idx >= 0 and temp_in_idx < len(row) else '',
                                'humi_in': row[humi_in_idx] if humi_in_idx >= 0 and humi_in_idx < len(row) else '',
                                'temp_out': row[temp_out_idx] if temp_out_idx >= 0 and temp_out_idx < len(row) else '',
                                'humi_out': row[humi_out_idx] if humi_out_idx >= 0 and humi_out_idx < len(row) else ''
                            }
                            row_count += 1
                        except (ValueError, IndexError) as e:
                            self.log(f"DEBUG: Skip row - {e}")
                            continue
            
            self.log(f"DEBUG: Loaded {len(weather_data)} weather records from {row_count} rows")
        except Exception as e:
            self.log(f"ERROR reading weather file: {e}")
            import traceback
            traceback.print_exc()
            return
        
        if not weather_data:
            self.log("WARNING: No weather data loaded - skipping merge")
            return
        
        # Read CSI data and create merged file
        temp_file = csi_file + ".tmp"
        try:
            with open(csi_file, 'r') as f_in, open(temp_file, 'w', newline='') as f_out:
                reader = csv.reader(f_in)
                writer = csv.writer(f_out)
                
                # Read header
                header = next(reader)
                new_header = header + ['temp_in', 'humi_in', 'temp_out', 'humi_out']
                writer.writerow(new_header)
                
                # Find timestamp column in CSI data
                time_idx = -1
                for i, col in enumerate(header):
                    if 'time' in col.lower() or i == 0:
                        time_idx = i
                        break
                
                # Get sorted weather timestamps for quick lookup
                sorted_weather_times = sorted(weather_data.keys())
                self.log(f"DEBUG: Weather timestamps range: {sorted_weather_times[0] if sorted_weather_times else 'N/A'} to {sorted_weather_times[-1] if sorted_weather_times else 'N/A'}")
                
                merged_count = 0
                # Process CSI rows
                for row in reader:
                    if len(row) > time_idx and time_idx >= 0:
                        try:
                            csi_ts = int(float(row[time_idx]))
                            # Find closest weather data
                            closest_ts = min(sorted_weather_times, 
                                           key=lambda x: abs(x - csi_ts))
                            weather = weather_data[closest_ts]
                            merged_count += 1
                        except (ValueError, IndexError):
                            weather = {'temp_in': '', 'humi_in': '', 'temp_out': '', 'humi_out': ''}
                    else:
                        weather = {'temp_in': '', 'humi_in': '', 'temp_out': '', 'humi_out': ''}
                    
                    new_row = row + [weather.get('temp_in', ''), 
                                     weather.get('humi_in', ''),
                                     weather.get('temp_out', ''), 
                                     weather.get('humi_out', '')]
                    writer.writerow(new_row)
            
            # Replace original file
            os.replace(temp_file, csi_file)
            self.log(f"SUCCESS: Merged {merged_count} CSI records with {len(weather_data)} weather records")
        except Exception as e:
            self.log(f"ERROR merging files: {e}")
            import traceback
            traceback.print_exc()
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def stop_logging(self):
        if not self.is_running:
            return
        self.log("Stopping... please wait for cleanup.")
        self.stop_event.set()
        # Đổi trạng thái nút ngay lập tức để người dùng biết đã ghi nhận lệnh dừng
        self.stop_btn.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = CSILoggerGUI(root)
    root.mainloop()
