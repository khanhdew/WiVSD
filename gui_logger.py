#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial.tools.list_ports
import threading
import time
import os
import csv
from datetime import datetime
from serial_to_csv import csi_data_read_parse, DATA_COLUMNS_NAMES

class CSILoggerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 CSI Logger GUI")
        self.root.geometry("600x700")
        
        self.stop_event = threading.Event()
        self.is_running = False
        
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
        ttk.Label(schedule_group, text="(0 to disable repeat)").grid(row=1, column=2, sticky=tk.W)

        # Storage
        storage_group = ttk.LabelFrame(main_frame, text="Storage", padding="10")
        storage_group.pack(fill=tk.X, pady=5)

        ttk.Label(storage_group, text="Output Directory:").grid(row=0, column=0, sticky=tk.W)
        self.dir_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(storage_group, textvariable=self.dir_var, width=40).grid(row=0, column=1, padx=5)
        ttk.Button(storage_group, text="Browse", command=self.browse_dir).grid(row=0, column=2)

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
        except ValueError:
            messagebox.showerror("Error", "Check your parameter formats (numbers needed).")
            return

        self.is_running = True
        self.stop_event.clear() # PHẢI CÓ dòng này để có thể bắt đầu lại
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # Run scheduler in a separate thread
        t = threading.Thread(target=self.logging_scheduler, args=(port, baudrate, duration, max_count, delay, interval), daemon=True)
        t.start()

    def logging_scheduler(self, port, baudrate, duration, max_count, delay, interval):
        try:
            if delay > 0:
                self.log(f"Delaying start for {delay} minutes...")
                # Sleep in chunks to check for stop_event
                start_delay = time.time()
                while time.time() - start_delay < delay * 60:
                    if self.stop_event.is_set():
                        self.log("Scheduled start cancelled.")
                        return
                    time.sleep(1)

            first_run = True
            while True:
                if not first_run and interval > 0:
                    self.log(f"Waiting for next interval: {interval} minutes...")
                    start_wait = time.time()
                    while time.time() - start_wait < interval * 60:
                        if self.stop_event.is_set():
                            self.log("Interval recording stopped.")
                            return
                        time.sleep(1)
                
                if self.stop_event.is_set():
                    break

                # Thêm log để biết đang ở bước nào
                self.log(f"DEBUG: Starting session core logic...")
                self.run_one_session(port, baudrate, duration, max_count)
                self.log(f"DEBUG: Session core logic returned.")
                
                first_run = False
                if interval <= 0:
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

    def run_one_session(self, port, baudrate, duration, max_count):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(self.dir_var.get(), f"csi_data_{timestamp}.csv")
        
        self.log(f"Starting session: {file_path}")
        
        try:
            with open(file_path, 'w', newline='') as f:
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
            self.log(f"SUCCESS: Session finished. Saved to: {file_path}")
        except Exception as e:
            self.log(f"ERROR: Session failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.log(f"DEBUG: run_one_session for {timestamp} clean exit.")

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
