#!/usr/bin/env python3
"""
Real-time CSI Detection GUI.
Extends CSI Logger to include real-time person detection using trained model.

Features:
- Live data collection from ESP32 via serial
- Real-time person detection using trained RF model
- Live visualization of detection results
- Configurable detection window and confidence threshold
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial.tools.list_ports
import threading
import time
import os
import csv
import json
import queue
from datetime import datetime
from pathlib import Path
from io import StringIO

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.signal import ellip, savgol_filter, sosfiltfilt

from serial_to_csv import DATA_COLUMNS_NAMES
from src.csi_preprocessing.classifier import predict_with_model_features


class RealtimeDetectorGUI:
    """GUI for real-time CSI detection with ESP32."""
    
    EXPECTED_CSV_COLUMNS = 15
    
    @staticmethod
    def parse_csi_line(line: str):
        """Parse a single CSI line from ESP32."""
        try:
            if 'CSI_DATA' not in line:
                return None
            
            reader = csv.reader(StringIO(line.strip()))
            csi_data = next(reader)
            
            if len(csi_data) != RealtimeDetectorGUI.EXPECTED_CSV_COLUMNS:
                return None
            
            try:
                csi_data_len = int(csi_data[-3])
            except (ValueError, IndexError):
                return None
            
            try:
                csi_raw_data = json.loads(csi_data[-1])
            except json.JSONDecodeError:
                return None
            
            if csi_data_len != len(csi_raw_data):
                return None
            
            csi_data.insert(0, time.time())
            return csi_data
        except Exception:
            return None

    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 CSI Real-time Detector")
        self.root.geometry("1100x950")
        
        self.stop_event = threading.Event()
        self.is_running = False
        
        self.data_queue = queue.Queue(maxsize=1000)
        self.prediction_queue = queue.Queue()
        self.waveform_queue = queue.Queue(maxsize=1)
        self.processed_queue = queue.Queue(maxsize=1)
        self.log_queue = queue.Queue()
        self.ui_refresh_job = None
        
        # CSI History buffers for time-series plot
        self.CSI_DATA_INDEX = 200  # Buffer size
        self.CSI_DATA_COLUMNS = 490  # Max subcarrier count
        self.csi_amplitude_history = np.zeros([self.CSI_DATA_INDEX, self.CSI_DATA_COLUMNS], dtype=np.float64)
        self.csi_phase_history = np.zeros([self.CSI_DATA_INDEX, self.CSI_DATA_COLUMNS], dtype=np.float64)
        self.csi_subcarrier_count = 0  # Actual number of subcarriers
        self.raw_amplitude_series = []
        self.raw_phase_series = []
        self.processed_result = None
        self.processing_in_progress = False
        
        # Stats
        self.stats = {
            'packets': 0,
            'predictions': 0,
            'last_pred': 'WAITING',
            'last_conf': 0.0,
        }
        
        self.create_widgets()
        self.refresh_ports()

    def create_widgets(self):
        """Create GUI widgets."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(main_frame, text="CSI Real-time Person Detection", 
                         font=("Helvetica", 14, "bold"))
        title.pack(pady=10)

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
        baudrate_combo = ttk.Combobox(serial_group, textvariable=self.baudrate_var, 
                                     values=["115200", "921600", "2000000"], width=30)
        baudrate_combo.grid(row=1, column=1, padx=5, pady=5)

        # Detection Configuration
        detect_group = ttk.LabelFrame(main_frame, text="Detection Configuration", padding="10")
        detect_group.pack(fill=tk.X, pady=5)

        ttk.Label(detect_group, text="Window Size (packets):").grid(row=0, column=0, sticky=tk.W)
        self.window_var = tk.StringVar(value="200")
        ttk.Entry(detect_group, textvariable=self.window_var).grid(row=0, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(detect_group, text="Model Path:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.model_var = tk.StringVar(value="models/rf_person_detector.joblib")
        model_frame = ttk.Frame(detect_group)
        model_frame.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        ttk.Entry(model_frame, textvariable=self.model_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(model_frame, text="Browse", command=self.browse_model).pack(side=tk.LEFT, padx=5)

        ttk.Label(detect_group, text="Plot Mode:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.plot_mode_var = tk.StringVar(value="raw")
        self.plot_mode_combo = ttk.Combobox(
            detect_group,
            textvariable=self.plot_mode_var,
            values=["raw", "processed"],
            state="readonly",
            width=30,
        )
        self.plot_mode_combo.grid(row=2, column=1, padx=5, sticky=tk.W, pady=5)
        self.plot_mode_combo.bind("<<ComboboxSelected>>", self.on_plot_mode_change)

        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="Start Detection", command=self.start_detection)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop Detection", command=self.stop_detection, 
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Results Display
        results_group = ttk.LabelFrame(main_frame, text="Detection Results", padding="10")
        results_group.pack(fill=tk.BOTH, expand=True, pady=5)

        # Prediction display
        pred_frame = ttk.Frame(results_group)
        pred_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(pred_frame, text="Status:").pack(side=tk.LEFT, padx=5)
        self.status_label = ttk.Label(pred_frame, text="IDLE", font=("Helvetica", 12, "bold"),
                                     foreground="blue")
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Confidence bar
        ttk.Label(pred_frame, text="Confidence:").pack(side=tk.LEFT, padx=5)
        self.confidence_var = tk.DoubleVar(value=0)
        self.conf_bar = ttk.Progressbar(pred_frame, length=200, maximum=100, 
                                       variable=self.confidence_var)
        self.conf_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.conf_label = ttk.Label(pred_frame, text="0%", width=5)
        self.conf_label.pack(side=tk.LEFT, padx=5)

        # Live waveform plot (raw realtime or processed batch)
        plot_group = ttk.LabelFrame(results_group, text="Live CSI Waveform", padding="10")
        plot_group.pack(fill=tk.BOTH, expand=True, pady=(10, 5))

        self.waveform_fig = Figure(figsize=(9, 6), dpi=100)
        self.waveform_axes = self.waveform_fig.subplots(2, 1, sharex=True)
        self.waveform_fig.tight_layout(pad=2.0)

        # Create line objects for each subcarrier or PCA component
        self.amp_lines = []
        self.phase_lines = []

        self.setup_waveform_plot("raw")

        self.waveform_canvas = FigureCanvasTkAgg(self.waveform_fig, master=plot_group)
        self.waveform_canvas.draw()
        self.waveform_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Statistics
        stats_frame = ttk.Frame(results_group)
        stats_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(stats_frame, text="Packets:").pack(side=tk.LEFT, padx=5)
        self.packets_label = ttk.Label(stats_frame, text="0", font=("Helvetica", 10))
        self.packets_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(stats_frame, text="Predictions:").pack(side=tk.LEFT, padx=20)
        self.pred_count_label = ttk.Label(stats_frame, text="0", font=("Helvetica", 10))
        self.pred_count_label.pack(side=tk.LEFT, padx=5)

        # Log area
        ttk.Label(results_group, text="Recent Detections:").pack(anchor=tk.W, pady=(10, 5))
        
        # Text widget with scrollbar
        scroll = ttk.Scrollbar(results_group)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(results_group, height=12, yscrollcommand=scroll.set, 
                               font=("Courier", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.log_text.yview)

    def setup_waveform_plot(self, mode, processed_result=None):
        """Configure the plot area for raw or processed output."""
        self.waveform_fig.clear()
        self.waveform_axes = self.waveform_fig.subplots(2, 1, sharex=True)
        self.waveform_fig.tight_layout(pad=2.0)
        self.amp_lines = []
        self.phase_lines = []

        if mode == "processed":
            self.waveform_axes[0].set_title("Processed Phase PCA Components")
            self.waveform_axes[0].set_ylabel("Component Value")
            self.waveform_axes[0].grid(True, alpha=0.25)

            self.waveform_axes[1].set_xlabel("Packet Index")
            self.waveform_axes[1].set_ylabel("Component Value")
            self.waveform_axes[1].set_title("Processed Amplitude PCA Components")
            self.waveform_axes[1].grid(True, alpha=0.25)

            if processed_result is not None:
                self.render_processed_waveform_plot(processed_result)
            else:
                self.waveform_axes[0].text(0.5, 0.5, "Waiting for batch processing...", ha="center", va="center", transform=self.waveform_axes[0].transAxes)
                self.waveform_axes[1].text(0.5, 0.5, "Waiting for batch processing...", ha="center", va="center", transform=self.waveform_axes[1].transAxes)
        else:
            self.waveform_axes[0].set_title("Subcarrier Phase Data (Time-Domain)")
            self.waveform_axes[0].set_ylabel("Phase (rad)")
            self.waveform_axes[0].grid(True, alpha=0.25)

            self.waveform_axes[1].set_xlabel("Time (Cumulative Packet Count)")
            self.waveform_axes[1].set_ylabel("Amplitude")
            self.waveform_axes[1].set_title("Subcarrier Amplitude Data (Time-Domain)")
            self.waveform_axes[1].grid(True, alpha=0.25)

        if hasattr(self, "waveform_canvas"):
            self.waveform_canvas.draw_idle()

    def on_plot_mode_change(self, _event=None):
        """Switch plot mode without altering collected data."""
        self.setup_waveform_plot(self.plot_mode_var.get(), self.processed_result)

    @staticmethod
    def hampel_filter_1d(series, window_size=7, n_sigma=3.0):
        """Replace outliers using a simple Hampel-style median filter."""
        values = np.asarray(series, dtype=np.float64)
        if values.size < 3:
            return values.copy()

        window_size = int(window_size)
        if window_size < 3:
            window_size = 3
        if window_size % 2 == 0:
            window_size += 1

        half = window_size // 2
        filtered = values.copy()
        for idx in range(values.size):
            start = max(0, idx - half)
            end = min(values.size, idx + half + 1)
            window = values[start:end]
            median = np.median(window)
            mad = np.median(np.abs(window - median))
            sigma = 1.4826 * mad
            if sigma > 0 and abs(values[idx] - median) > n_sigma * sigma:
                filtered[idx] = median
        return filtered

    @staticmethod
    def safe_savgol_filter(series, window_length, polyorder):
        """Apply Savitzky-Golay only when the window is valid."""
        values = np.asarray(series, dtype=np.float64)
        if values.size <= polyorder:
            return values.copy()

        window_length = min(int(window_length), values.size if values.size % 2 == 1 else values.size - 1)
        if window_length <= polyorder:
            return values.copy()
        if window_length % 2 == 0:
            window_length -= 1
        if window_length <= polyorder:
            return values.copy()
        return savgol_filter(values, window_length=window_length, polyorder=polyorder)

    @staticmethod
    def apply_elliptic_bandpass(series, lowcut, highcut, order, rp, rs, fs):
        """Apply elliptic bandpass filter with safe fallbacks for short series."""
        values = np.asarray(series, dtype=np.float64)
        if values.size < max(8, order * 3):
            return values.copy()

        nyquist = fs / 2.0
        if not 0 < lowcut < highcut < nyquist:
            return values.copy()

        sos = ellip(N=order, rp=rp, rs=rs, Wn=[lowcut / nyquist, highcut / nyquist], btype="bandpass", output="sos")
        padlen = min(3000, values.size - 1)
        if padlen <= 0:
            return values.copy()
        return sosfiltfilt(sos, values, padlen=padlen)

    @staticmethod
    def compute_pca(matrix, n_components=5):
        """Compute PCA scores using SVD without extra dependencies."""
        data = np.asarray(matrix, dtype=np.float64)
        if data.ndim != 2 or data.size == 0:
            return None, None

        centered = data - np.mean(data, axis=0, keepdims=True)
        n_samples, _ = centered.shape
        if n_samples < 2:
            return None, None

        u, s, _ = np.linalg.svd(centered, full_matrices=False)
        component_count = min(int(n_components), u.shape[1])
        scores = u[:, :component_count] * s[:component_count]
        variances = s ** 2
        explained = variances[:component_count] / np.sum(variances) if np.sum(variances) > 0 else np.zeros(component_count)
        return scores, explained

    def render_raw_waveform_plot(self):
        """Render the realtime raw CSI waveform."""
        if self.csi_subcarrier_count == 0:
            return

        if len(self.amp_lines) == 0:
            for idx in range(self.csi_subcarrier_count):
                line_amp, = self.waveform_axes[1].plot([], [], linewidth=0.8, alpha=0.6)
                self.amp_lines.append((idx, line_amp))

                line_phase, = self.waveform_axes[0].plot([], [], linewidth=0.8, alpha=0.6)
                self.phase_lines.append((idx, line_phase))

        x_values = np.arange(self.CSI_DATA_INDEX)
        for idx, line_amp in self.amp_lines:
            line_amp.set_data(x_values, self.csi_amplitude_history[:, idx])

        for idx, line_phase in self.phase_lines:
            line_phase.set_data(x_values, self.csi_phase_history[:, idx])

        self.waveform_axes[0].relim()
        self.waveform_axes[0].autoscale_view()
        self.waveform_axes[1].relim()
        self.waveform_axes[1].autoscale_view()
        self.waveform_canvas.draw_idle()

    def render_processed_waveform_plot(self, processed_result):
        """Render PCA output for the processed batch mode."""
        if not processed_result:
            return

        amp_pca = processed_result.get("amp_pca")
        phs_pca = processed_result.get("phs_pca")
        if amp_pca is None or phs_pca is None:
            return

        self.waveform_axes[0].clear()
        self.waveform_axes[1].clear()

        amp_components = min(amp_pca.shape[1], 5)
        phs_components = min(phs_pca.shape[1], 5)
        x_amp = np.arange(amp_pca.shape[0])
        x_phs = np.arange(phs_pca.shape[0])

        for comp_idx in range(amp_components):
            self.waveform_axes[1].plot(x_amp, amp_pca[:, comp_idx], linewidth=1.0, label=f"PC{comp_idx + 1}")
        for comp_idx in range(phs_components):
            self.waveform_axes[0].plot(x_phs, phs_pca[:, comp_idx], linewidth=1.0, label=f"PC{comp_idx + 1}")

        self.waveform_axes[0].set_title("Processed Phase PCA Components")
        self.waveform_axes[0].set_ylabel("Component Value")
        self.waveform_axes[0].grid(True, alpha=0.25)
        self.waveform_axes[0].legend(loc="upper right")

        self.waveform_axes[1].set_title("Processed Amplitude PCA Components")
        self.waveform_axes[1].set_xlabel("Packet Index")
        self.waveform_axes[1].set_ylabel("Component Value")
        self.waveform_axes[1].grid(True, alpha=0.25)
        self.waveform_axes[1].legend(loc="upper right")

        self.waveform_canvas.draw_idle()

    def process_processed_mode(self):
        """Run the batch preprocessing pipeline and publish the result."""
        if not self.raw_amplitude_series or not self.raw_phase_series:
            self.log("No raw CSI data to process")
            return

        try:
            self.log("Starting batch processing: Hampel -> SG -> Elliptic -> PCA")

            amp_lengths = [len(row) for row in self.raw_amplitude_series if len(row) > 0]
            phs_lengths = [len(row) for row in self.raw_phase_series if len(row) > 0]
            if not amp_lengths or not phs_lengths:
                self.log("Batch processing skipped: insufficient CSI length")
                return

            subcarrier_count = min(min(amp_lengths), min(phs_lengths))
            amp_matrix = np.asarray([row[:subcarrier_count] for row in self.raw_amplitude_series], dtype=np.float64)
            phs_matrix = np.asarray([row[:subcarrier_count] for row in self.raw_phase_series], dtype=np.float64)

            amp_hampel = np.column_stack([
                self.hampel_filter_1d(amp_matrix[:, idx], window_size=15, n_sigma=3.0)
                for idx in range(subcarrier_count)
            ])
            phs_hampel = np.column_stack([
                self.hampel_filter_1d(phs_matrix[:, idx], window_size=15, n_sigma=3.0)
                for idx in range(subcarrier_count)
            ])

            amp_sg = np.column_stack([
                self.safe_savgol_filter(amp_hampel[:, idx], window_length=31, polyorder=3)
                for idx in range(subcarrier_count)
            ])
            phs_sg = np.column_stack([
                self.safe_savgol_filter(phs_hampel[:, idx], window_length=41, polyorder=3)
                for idx in range(subcarrier_count)
            ])

            amp_ellip = np.column_stack([
                self.apply_elliptic_bandpass(col, 0.15, 0.5, order=4, rp=0.1, rs=40, fs=100.0)
                for col in amp_sg.T
            ])
            phs_ellip = np.column_stack([
                self.apply_elliptic_bandpass(col, 0.1, 0.6, order=2, rp=0.5, rs=50, fs=100.0)
                for col in phs_sg.T
            ])

            amp_pca, amp_explained = self.compute_pca(amp_ellip, n_components=5)
            phs_pca, phs_explained = self.compute_pca(phs_ellip, n_components=5)

            if amp_pca is None or phs_pca is None:
                self.log("Batch processing failed: PCA could not be computed")
                return

            self.processed_result = {
                "amp_pca": amp_pca,
                "phs_pca": phs_pca,
                "amp_explained": amp_explained,
                "phs_explained": phs_explained,
                "subcarrier_count": subcarrier_count,
            }
            try:
                self.processed_queue.put_nowait(self.processed_result)
            except queue.Full:
                pass
            self.log(f"Batch processing complete: {amp_pca.shape[1]} amp PCs, {phs_pca.shape[1]} phase PCs")
        except Exception as e:
            self.log(f"Batch processing error: {e}")
        finally:
            self.processing_in_progress = False

    def extract_csi_complex(self, parsed_row):
        """Extract CSI complex data as (I, Q) pairs from raw data."""
        try:
            data_str = parsed_row[-1]
            data = json.loads(data_str) if isinstance(data_str, str) else data_str
            csi_raw_data = np.asarray(data, dtype=np.float64)
            
            if csi_raw_data.size < 2:
                return None, None

            # Convert [Q0, I0, Q1, I1, ...] to complex array
            csi_len = len(csi_raw_data) // 2
            csi_complex = np.zeros(csi_len, dtype=np.complex64)
            
            for i in range(csi_len):
                csi_complex[i] = complex(csi_raw_data[i * 2 + 1], csi_raw_data[i * 2])
            
            amplitude = np.abs(csi_complex)
            phase = np.angle(csi_complex)
            return amplitude, phase
        except Exception:
            return None, None

    def update_waveform_plot(self):
        """Refresh the live CSI waveform plot with time-series data."""
        if self.csi_subcarrier_count == 0:
            return
        
        # Reduce subcarrier display for performance
        SUBCARRIER_INTERVAL = 1  # Display every Nth subcarrier
        displayed_subcarriers = list(range(0, self.csi_subcarrier_count, SUBCARRIER_INTERVAL))
        
        # Initialize lines if needed
        if len(self.amp_lines) == 0:
            for i in displayed_subcarriers:
                # Amplitude line
                line_amp, = self.waveform_axes[1].plot([], [], linewidth=0.8, alpha=0.6)
                self.amp_lines.append((i, line_amp))
                
                # Phase line
                line_phase, = self.waveform_axes[0].plot([], [], linewidth=0.8, alpha=0.6)
                self.phase_lines.append((i, line_phase))
        
        # Update all lines
        x_values = np.arange(self.CSI_DATA_INDEX)
        for idx, line_amp in self.amp_lines:
            line_amp.set_data(x_values, self.csi_amplitude_history[:, idx])
        
        for idx, line_phase in self.phase_lines:
            line_phase.set_data(x_values, self.csi_phase_history[:, idx])
        
        # Auto-scale axes
        self.waveform_axes[0].relim()
        self.waveform_axes[0].autoscale_view()
        self.waveform_axes[1].relim()
        self.waveform_axes[1].autoscale_view()
        
        self.waveform_canvas.draw_idle()

    def update_gui(self):
        """Refresh labels, logs, and waveform plot on the Tk main thread."""
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)

        self.packets_label.config(text=str(self.stats['packets']))
        self.pred_count_label.config(text=str(self.stats['predictions']))

        latest_prediction = None
        while True:
            try:
                latest_prediction = self.prediction_queue.get_nowait()
            except queue.Empty:
                break

        if latest_prediction is not None:
            pred = latest_prediction['prediction']
            conf = latest_prediction['confidence']
            color = "green" if pred == "PERSON" else "blue"
            self.status_label.config(text=pred, foreground=color)
            self.confidence_var.set(conf * 100)
            self.conf_label.config(text=f"{conf:.0%}")
            self.log(f"[{latest_prediction['time']}] {pred} ({conf:.1%})")

        current_mode = self.plot_mode_var.get()
        if current_mode == "processed":
            latest_processed = None
            while True:
                try:
                    latest_processed = self.processed_queue.get_nowait()
                except queue.Empty:
                    break
            if latest_processed is not None:
                self.setup_waveform_plot("processed", latest_processed)
                self.status_label.config(text="PROCESSED", foreground="green")
        else:
            # Check if new waveform data arrived (just consume it for now, plot will update independently)
            while True:
                try:
                    _ = self.waveform_queue.get_nowait()
                except queue.Empty:
                    break
            self.render_raw_waveform_plot()

        if self.is_running or self.processing_in_progress or not self.prediction_queue.empty() or not self.waveform_queue.empty() or not self.processed_queue.empty():
            self.ui_refresh_job = self.root.after(100, self.update_gui)
        else:
            self.ui_refresh_job = None

    def refresh_ports(self):
        """Refresh available serial ports."""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.set(ports[0])

    def browse_model(self):
        """Browse for model file."""
        file = filedialog.askopenfilename(
            initialdir="models",
            filetypes=[("Joblib files", "*.joblib"), ("All files", "*.*")]
        )
        if file:
            self.model_var.set(file)

    def start_detection(self):
        """Start real-time detection."""
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Please select a serial port")
            return
        
        baudrate = int(self.baudrate_var.get())
        window_size = int(self.window_var.get())
        model_path = self.model_var.get()
        
        if not Path(model_path).exists():
            messagebox.showerror("Error", f"Model not found: {model_path}")
            return
        
        self.is_running = True
        self.stop_event.clear()
        self.processed_result = None
        self.raw_amplitude_series = []
        self.raw_phase_series = []
        self.csi_amplitude_history.fill(0)
        self.csi_phase_history.fill(0)
        self.csi_subcarrier_count = 0
        self.amp_lines = []
        self.phase_lines = []
        self.processing_in_progress = False
        while not self.waveform_queue.empty():
            try:
                self.waveform_queue.get_nowait()
            except queue.Empty:
                break
        while not self.processed_queue.empty():
            try:
                self.processed_queue.get_nowait()
            except queue.Empty:
                break
        self.setup_waveform_plot(self.plot_mode_var.get())
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.status_label.config(text="RUNNING", foreground="blue")

        if self.ui_refresh_job is None:
            self.ui_refresh_job = self.root.after(100, self.update_gui)
        
        # Start threads
        reader_t = threading.Thread(target=self.serial_reader_thread, 
                                   args=(port, baudrate), daemon=True)
        processor_t = threading.Thread(target=self.packet_processor_thread,
                                      args=(window_size, model_path), daemon=True)
        
        reader_t.start()
        processor_t.start()

    def stop_detection(self):
        """Stop real-time detection."""
        self.is_running = False
        self.stop_event.set()
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="STOPPED", foreground="gray")
        
        self.log("Detection stopped")

        if self.plot_mode_var.get() == "processed" and self.raw_amplitude_series:
            self.status_label.config(text="PROCESSING", foreground="orange")
            self.processing_in_progress = True
            if self.ui_refresh_job is None:
                self.ui_refresh_job = self.root.after(100, self.update_gui)
            threading.Thread(target=self.process_processed_mode, daemon=True).start()

    def serial_reader_thread(self, port, baudrate):
        """Read from serial port."""
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            self.log(f"Connected to {port}")
        except Exception as e:
            self.log(f"Error: Failed to open {port}: {e}")
            self.is_running = False
            self.stop_event.set()
            return
        
        try:
            while self.is_running and not self.stop_event.is_set():
                try:
                    if ser.in_waiting == 0:
                        time.sleep(0.01)
                        continue
                    
                    raw = ser.readline()
                    if raw:
                        line = raw.decode('utf-8', errors='ignore').strip()
                        if line:
                            try:
                                self.data_queue.put(line, timeout=0.1)
                            except queue.Full:
                                continue
                except (serial.SerialException, AttributeError):
                    break
        finally:
            if ser.is_open:
                ser.close()
            self.log("Serial port closed")

    def packet_processor_thread(self, window_size, model_path):
        """Process packets and predict."""
        csv_buffer = []
        packet_count = 0
        raw_mode = self.plot_mode_var.get() == "raw"
        
        while self.is_running and not self.stop_event.is_set():
            try:
                line = self.data_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            
            try:
                parsed = self.parse_csi_line(line)
                if parsed:
                    packet_count += 1
                    self.stats['packets'] = packet_count
                    csv_buffer.append(parsed)

                    # Extract amplitude and phase from CSI data
                    amplitude, phase = self.extract_csi_complex(parsed)
                    if amplitude is not None and phase is not None:
                        self.raw_amplitude_series.append(amplitude)
                        self.raw_phase_series.append(phase)

                        # Initialize subcarrier count on first packet
                        if self.csi_subcarrier_count == 0:
                            self.csi_subcarrier_count = len(amplitude)

                        if raw_mode:
                            # Rotate history left and add new packet
                            self.csi_amplitude_history[:-1] = self.csi_amplitude_history[1:]
                            self.csi_phase_history[:-1] = self.csi_phase_history[1:]
                            
                            # Add new packet to the end
                            self.csi_amplitude_history[-1, :self.csi_subcarrier_count] = amplitude[:self.csi_subcarrier_count]
                            self.csi_phase_history[-1, :self.csi_subcarrier_count] = phase[:self.csi_subcarrier_count]
                            
                            # Signal waveform update
                            try:
                                if self.waveform_queue.full():
                                    self.waveform_queue.get_nowait()
                                self.waveform_queue.put_nowait(True)
                            except queue.Full:
                                pass
                    
                    if packet_count % window_size == 0:
                        self.predict_from_buffer(csv_buffer, model_path)
                        csv_buffer = []
                        
            except Exception as e:
                self.log(f"Error: {e}")

    def predict_from_buffer(self, csv_data, model_path):
        """Extract features and predict."""
        if not csv_data or len(csv_data) < 10:
            return
        
        try:
            # Extract amplitude features
            amp_data = []
            for row in csv_data:
                try:
                    data_str = row[-1]
                    data = json.loads(data_str) if isinstance(data_str, str) else data_str
                    data_array = np.array(data, dtype=np.float64)
                    if len(data_array) >= 2:
                        imag = data_array[0::2]
                        real = data_array[1::2]
                        l = min(len(real), len(imag))
                        amp = np.sqrt(real[:l]**2 + imag[:l]**2)
                        amp_data.extend(amp)
                except:
                    continue
            
            if not amp_data:
                return
            
            # Compute features
            amp_array = np.array(amp_data)
            amp_mean = float(np.mean(amp_array))
            amp_std = float(np.std(amp_array))
            amp_cv = float(amp_std / (amp_mean + 1e-8))
            
            # Predict
            features = [amp_mean, amp_std, amp_cv]
            pred, details = predict_with_model_features(features, model_path)
            
            proba = details.get('proba', [[0, 0]])[0]
            confidence = max(proba) if proba else 0.5
            
            # Update stats
            pred_label = "PERSON" if pred == 1 else "NO PERSON"
            self.stats['last_pred'] = pred_label
            self.stats['last_conf'] = confidence
            self.stats['predictions'] += 1
            
            # Put result in queue for display
            self.prediction_queue.put({
                'prediction': pred_label,
                'confidence': confidence,
                'time': datetime.now().strftime("%H:%M:%S"),
            })
            
        except Exception as e:
            self.log(f"Prediction error: {e}")

    def log(self, message):
        """Add message to log."""
        self.log_queue.put(message)


def main():
    root = tk.Tk()
    app = RealtimeDetectorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
