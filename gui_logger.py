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
import subprocess
import signal
import sys

class CSILoggerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 CSI Logger GUI")
        self.root.geometry("600x800")
        
        self.stop_event = threading.Event()
        self.is_running = False
        self.weather_thread = None
        # In-memory weather data for fast/online merging
        self.weather_data_lock = threading.Lock()
        self.weather_data = {}
        
        self.create_widgets()
        self.refresh_ports()
        self.current_port = None
        self.scheduler_thread = None
        self.serial_handle_ref = {'serial': None}

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

        # Scenarios
        scenario_group = ttk.LabelFrame(main_frame, text="Scenario Information", padding="10")
        scenario_group.pack(fill=tk.X, pady=5)

        ttk.Label(scenario_group, text="Scene 1 - Number of People:").grid(row=0, column=0, sticky=tk.W)
        self.scenario_1_var = tk.StringVar(value="")
        ttk.Entry(scenario_group, textvariable=self.scenario_1_var, width=15).grid(row=0, column=1, padx=5, sticky=tk.W)

        ttk.Label(scenario_group, text="Scene 2 - Action:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.scenario_2_var = tk.StringVar(value="")
        scenario_2_combo = ttk.Combobox(scenario_group, textvariable=self.scenario_2_var, 
                                        values=["ngồi yên", "đi lại", "vẫy tay", "ngồi nhìn", "nằm"], 
                                        width=13)
        scenario_2_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(scenario_group, text="Scene 3 - Environment:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.scenario_3_var = tk.StringVar(value="")
        scenario_3_combo = ttk.Combobox(scenario_group, textvariable=self.scenario_3_var, 
                                        values=["tĩnh lặng", "quạt", "điều hòa", "TV", "nhạc"], 
                                        width=13)
        scenario_3_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

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
            # Scenarios
            scenario_1 = self.scenario_1_var.get()
            scenario_2 = self.scenario_2_var.get()
            scenario_3 = self.scenario_3_var.get()
        except ValueError:
            messagebox.showerror("Error", "Check your parameter formats (numbers needed).")
            return

        self.is_running = True
        self.stop_event.clear() # PHẢI CÓ dòng này để có thể bắt đầu lại
        self.current_port = port
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # Run scheduler in a separate thread
        t = threading.Thread(target=self.logging_scheduler, args=(port, baudrate, duration, max_count, delay, interval, weather_interval, udp_port, scenario_1, scenario_2, scenario_3), daemon=True)
        t.start()
        self.scheduler_thread = t

    def logging_scheduler(self, port, baudrate, duration, max_count, delay, interval, weather_interval, udp_port, scenario_1, scenario_2, scenario_3):
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
                self.run_one_session(port, baudrate, duration, max_count, weather_interval, udp_port, scenario_1, scenario_2, scenario_3)
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

    def run_one_session(self, port, baudrate, duration, max_count, weather_interval, udp_port, scenario_1, scenario_2, scenario_3):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csi_file_path = os.path.join(self.dir_var.get(), f"csi_data_{timestamp}.csv")
        weather_file_path = os.path.join(self.dir_var.get(), f".weather_tmp_{timestamp}.csv")  # Temp file
        
        self.log(f"Starting session: {csi_file_path}")
        self.log(f"Scenarios - People: {scenario_1}, Action: {scenario_2}, Environment: {scenario_3}")
        
        # Start weather collector thread if enabled
        weather_thread = None
        if self.weather_enabled.get():
            self.log(f"Starting weather collector (background)...")
            try:
                # Build scenarios list for weather collector
                scenarios = [scenario_1, scenario_2, scenario_3, "", ""]
                weather_thread = threading.Thread(
                    target=self._run_weather_collector,
                    args=(weather_file_path, weather_interval, udp_port, scenarios),
                    daemon=True
                )
                weather_thread.start()
            except Exception as e:
                self.log(f"WARNING: Failed to start weather collector: {e}")
        
        try:
            # Time the CSI collection (exclude merge time)
            start_collect = time.time()
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
                    print_func=self.log,
                    serial_handle_ref=self.serial_handle_ref
                )
            end_collect = time.time()
            collect_seconds = end_collect - start_collect
            self.log(f"SUCCESS: CSI data collected. Saved to: {csi_file_path}")
            self.log(f"STAT: CSI collection time (s): {collect_seconds:.3f}")
        except Exception as e:
            self.log(f"ERROR: CSI session failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Stop weather collector if running
            if weather_thread is not None and self.weather_enabled.get():
                self.log("Stopping weather collector...")
                # Preserve existing state of stop_event so we don't clear a user-requested stop
                was_stop_set = self.stop_event.is_set()
                try:
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
                    # Restore stop_event to previous state: clear only if it wasn't set before
                    if not was_stop_set:
                        self.stop_event.clear()

            # Ensure serial reference is cleared at the end of the session
            try:
                self._close_active_serial()
            except Exception:
                pass

            try:
                self.current_port = None
            except Exception:
                pass
            
            self.log(f"DEBUG: run_one_session for {timestamp} clean exit.")

    def _run_weather_collector(self, weather_file_path, interval, udp_port, scenarios=None):
        """Run weather collector in a separate thread."""
        try:
            if scenarios is None:
                scenarios = []
            self.log(f"DEBUG: Weather collector starting on port {udp_port} with scenarios: {scenarios}...")
            # Pass an update_callback so we receive each weather row as it's written
            collect_loop(
                csv_file=weather_file_path,
                interval=interval,
                stop_event=self.stop_event,
                scenarios=scenarios,
                udp_port=udp_port,
                update_callback=self._weather_update_callback
            )
            
            self.log("DEBUG: Weather collector finished")
        except Exception as e:
            self.log(f"ERROR in weather collector: {e}")
            import traceback
            traceback.print_exc()

    def _weather_update_callback(self, now, temp_in, humi_in, temp_out, humi_out, scenarios=None):
        """Callback invoked by weather_collector.collect_loop for each written row.
        Stores latest weather row indexed by integer-second timestamp for fast merging.
        """
        try:
            ts = int(now)
        except Exception:
            try:
                ts = int(float(now))
            except Exception:
                return

        if scenarios is None:
            scenarios = [''] * 5
        else:
            # ensure list of length 5
            scenarios = list(scenarios)
            if len(scenarios) < 5:
                scenarios += [''] * (5 - len(scenarios))

        with self.weather_data_lock:
            self.weather_data[ts] = {
                'temp_in': str(temp_in) if temp_in is not None else '',
                'humi_in': str(humi_in) if humi_in is not None else '',
                'temp_out': str(temp_out) if temp_out is not None else '',
                'humi_out': str(humi_out) if humi_out is not None else '',
                'scenarios': scenarios[:5]
            }

    def _merge_weather_to_csi(self, csi_file, weather_file):
        """Merge weather data into CSI file by timestamp alignment."""
        # Prefer in-memory weather data (populated live via update_callback) for fast merging.
        with self.weather_data_lock:
            if self.weather_data:
                weather_data = dict(self.weather_data)
                self.log(f"DEBUG: Using in-memory weather data with {len(weather_data)} records for merge")
            else:
                weather_data = {}

        # If no in-memory data, fall back to reading the weather temp file
        if not weather_data:
            self.log(f"DEBUG: No in-memory weather data, checking weather file: {weather_file}")
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
                    # scenario columns
                    scenario_idxs = []
                    for i in range(1, 6):
                        col = f'scenario_{i}'
                        scenario_idxs.append(header.index(col) if col in header else -1)

                    row_count = 0
                    for row in reader:
                        if len(row) > time_idx:
                            try:
                                ts = int(row[time_idx])
                                scenarios_vals = []
                                for idx in scenario_idxs:
                                    scenarios_vals.append(row[idx] if idx >= 0 and idx < len(row) else '')

                                weather_data[ts] = {
                                    'temp_in': row[temp_in_idx] if temp_in_idx >= 0 and temp_in_idx < len(row) else '',
                                    'humi_in': row[humi_in_idx] if humi_in_idx >= 0 and humi_in_idx < len(row) else '',
                                    'temp_out': row[temp_out_idx] if temp_out_idx >= 0 and temp_out_idx < len(row) else '',
                                    'humi_out': row[humi_out_idx] if humi_out_idx >= 0 and humi_out_idx < len(row) else '',
                                    'scenarios': scenarios_vals
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
                # Append weather columns + scenario columns
                scenario_headers = [f'scenario_{i}' for i in range(1, 6)]
                new_header = header + ['temp_in', 'humi_in', 'temp_out', 'humi_out'] + scenario_headers
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
                            weather = {'temp_in': '', 'humi_in': '', 'temp_out': '', 'humi_out': '', 'scenarios': ['']*5}
                    else:
                        weather = {'temp_in': '', 'humi_in': '', 'temp_out': '', 'humi_out': '', 'scenarios': ['']*5}

                    new_row = row + [weather.get('temp_in', ''), 
                                     weather.get('humi_in', ''),
                                     weather.get('temp_out', ''), 
                                     weather.get('humi_out', '')]
                    # Append scenario values
                    new_row += weather.get('scenarios', ['']*5)
                    writer.writerow(new_row)

            # Replace original file
            os.replace(temp_file, csi_file)
            self.log(f"SUCCESS: Merged {merged_count} CSI records with {len(weather_data)} weather records and appended scenarios")
        except Exception as e:
            self.log(f"ERROR merging files: {e}")
            import traceback
            traceback.print_exc()
            if os.path.exists(temp_file):
                os.remove(temp_file)
        finally:
            # Clear in-memory data after merge to free memory and avoid stale entries
            with self.weather_data_lock:
                self.weather_data.clear()

    def stop_logging(self):
        if not self.is_running:
            return
        self.log("Stopping... please wait for cleanup.")
        self.stop_event.set()
        self._close_active_serial()
        self._set_idle_ui()
        # Đổi trạng thái nút ngay lập tức để người dùng biết đã ghi nhận lệnh dừng
        self.stop_btn.config(state=tk.DISABLED)
        # Start a watchdog to force-free the serial port if stop hangs
        def _watchdog():
            waited = 0.0
            interval = 0.2
            timeout = 8.0
            while waited < timeout:
                if not self.is_running:
                    return
                time.sleep(interval)
                waited += interval

            # Still running: attempt to free port processes holding the device
            port = getattr(self, 'current_port', None)
            if port:
                self.log(f"WARNING: Stop timed out ({int(timeout)}s). Attempting to free {port}...")
                try:
                    self._force_free_port(port)
                    self.log(f"INFO: Free attempt sent for {port}")
                except Exception as e:
                    self.log(f"ERROR: Force free failed: {e}")
            else:
                self.log("WARNING: Stop timed out but no port recorded to free.")

        wd = threading.Thread(target=_watchdog, daemon=True)
        wd.start()

    def _get_port_pids(self, dev_path):
        try:
            out = subprocess.check_output(['lsof', '-t', dev_path], stderr=subprocess.DEVNULL)
            pids = [int(x) for x in out.decode().split() if x.strip()]
            return pids
        except Exception:
            return []

    def _force_free_port(self, dev_path, wait=2.0):
        pids = self._get_port_pids(dev_path)
        if not pids:
            return
        for pid in pids:
            try:
                if pid == os.getpid():
                    continue
                self.log(f"INFO: Terminating process {pid} holding {dev_path}...")
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass

        end = time.time() + wait
        while time.time() < end:
            remaining = self._get_port_pids(dev_path)
            if not remaining:
                return
            time.sleep(0.1)

        for pid in self._get_port_pids(dev_path):
            try:
                if pid == os.getpid():
                    continue
                self.log(f"WARN: Killing process {pid} (force) holding {dev_path}...")
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass

    def _close_active_serial(self):
        ser = None
        try:
            ser = self.serial_handle_ref.get('serial')
        except Exception:
            ser = None

        if ser is None:
            return

        try:
            if hasattr(ser, 'cancel_read'):
                try:
                    ser.cancel_read()
                except Exception:
                    pass
            if getattr(ser, 'is_open', False):
                ser.close()
                self.log("INFO: Active serial closed on STOP.")
        except Exception as e:
            self.log(f"WARNING: Failed to close active serial: {e}")
        finally:
            try:
                if self.serial_handle_ref.get('serial') is ser:
                    self.serial_handle_ref['serial'] = None
            except Exception:
                pass

    def _set_idle_ui(self):
        self.is_running = False
        self.current_port = None
        try:
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = CSILoggerGUI(root)
    root.mainloop()
