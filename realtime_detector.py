#!/usr/bin/env python3
"""
Real-time CSI detection using trained RF model.

Connects to ESP32 via serial, collects CSI packets, extracts features,
and performs real-time person detection using the trained model.

Usage:
    python realtime_detector.py --port /dev/ttyUSB0 --baudrate 2000000 --window 200 --model models/rf_person_detector.joblib
"""

import argparse
import sys
import time
import threading
import queue
import serial
import csv
from datetime import datetime
from pathlib import Path
from io import StringIO
from collections import deque

import json
import numpy as np
import pandas as pd

from serial_to_csv import DATA_COLUMNS_NAMES
from src.csi_preprocessing.classifier import (
    predict_with_model_features,
    predict_from_csv_fast,
)


class RealtimeDetector:
    """Realtime person detector using CSI data and trained model."""
    
    # Expected columns from ESP32 CSI format
    EXPECTED_CSV_COLUMNS = 15
    
    @staticmethod
    def parse_csi_line(line: str):
        """Parse a single CSI line from ESP32.
        
        Returns parsed data as list or None if invalid.
        """
        try:
            if 'CSI_DATA' not in line:
                return None
            
            # Parse CSV format
            reader = csv.reader(StringIO(line.strip()))
            csi_data = next(reader)
            
            # Validate column count
            if len(csi_data) != RealtimeDetector.EXPECTED_CSV_COLUMNS:
                return None
            
            # Get CSI data length from -3 column
            try:
                csi_data_len = int(csi_data[-3])
            except (ValueError, IndexError):
                return None
            
            # Parse JSON data from last column
            try:
                csi_raw_data = json.loads(csi_data[-1])
            except json.JSONDecodeError:
                return None
            
            # Validate CSI data length
            if csi_data_len != len(csi_raw_data):
                return None
            
            # Add system timestamp at beginning
            csi_data.insert(0, time.time())
            return csi_data
            
        except Exception:
            return None
    
    def __init__(self, port, baudrate=2000000, window_size=200, model_path='models/rf_person_detector.joblib'):
        """
        Args:
            port: Serial port (e.g., '/dev/ttyUSB0')
            baudrate: Serial baudrate (default 2000000)
            window_size: Number of packets to accumulate before prediction
            model_path: Path to trained model joblib file
        """
        self.port = port
        self.baudrate = baudrate
        self.window_size = window_size
        self.model_path = model_path
        
        self.data_queue = queue.Queue(maxsize=1000)
        self.stop_event = threading.Event()
        self.prediction_queue = queue.Queue()
        
        # Packet buffer for feature extraction
        self.packet_buffer = deque(maxlen=window_size)
        self.packet_count = 0
        
        # Stats
        self.stats = {
            'total_packets': 0,
            'predictions': 0,
            'last_prediction': None,
            'last_timestamp': None,
            'errors': 0,
        }
        
        # Verify model exists
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
    
    def serial_reader_thread(self):
        """Read CSI data from serial port and queue packets."""
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"[READER] Connected to {self.port} @ {self.baudrate} baud")
        except Exception as e:
            print(f"[ERROR] Failed to open serial port: {e}")
            self.stop_event.set()
            return
        
        try:
            while not self.stop_event.is_set():
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
                except (serial.SerialException, AttributeError, TypeError):
                    break
        except KeyboardInterrupt:
            print("[READER] Interrupted")
        finally:
            if ser.is_open:
                ser.close()
            print("[READER] Serial port closed")
    
    def packet_processor_thread(self):
        """Process packets and accumulate into buffer."""
        csv_buffer = []
        
        while not self.stop_event.is_set():
            try:
                line = self.data_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            
            try:
                # Parse CSI line
                parsed = self.parse_csi_line(line)
                if parsed:
                    # Add to buffer
                    self.packet_buffer.append(parsed)
                    self.packet_count += 1
                    self.stats['total_packets'] += 1
                    
                    # Add to CSV buffer for feature extraction
                    csv_buffer.append(parsed)
                    
                    # When buffer is full, predict
                    if self.packet_count % self.window_size == 0:
                        self.predict_from_buffer(csv_buffer)
                        csv_buffer = []
                        
            except Exception as e:
                self.stats['errors'] += 1
                print(f"[ERROR] Processing packet: {e}")
                continue
    
    def predict_from_buffer(self, csv_data):
        """Extract features from buffer and predict."""
        if not csv_data or len(csv_data) < 10:
            return
        
        try:
            # Create CSV buffer in memory
            csv_str = StringIO()
            writer = csv.writer(csv_str)
            writer.writerow(DATA_COLUMNS_NAMES)
            for row in csv_data:
                writer.writerow(row)
            
            csv_content = csv_str.getvalue()
            csv_path = StringIO(csv_content)
            
            # Read as dataframe for feature extraction
            df = pd.read_csv(StringIO(csv_content))
            
            # Extract features using the same function as predict_from_csv_fast
            amp_data = []
            for _, row in df.iterrows():
                data_str = row.get('data', '[]')
                try:
                    data = eval(data_str) if isinstance(data_str, str) else data_str
                    data_array = np.array(data, dtype=np.float64)
                    if len(data_array) >= 2:
                        imag = data_array[0::2]
                        real = data_array[1::2]
                        l = min(len(real), len(imag))
                        amp = np.sqrt(real[:l]**2 + imag[:l]**2)
                        amp_data.extend(amp)
                except Exception:
                    continue
            
            if not amp_data:
                return
            
            # Compute statistics
            amp_array = np.array(amp_data)
            amp_mean = float(np.mean(amp_array))
            amp_std = float(np.std(amp_array))
            amp_cv = float(amp_std / (amp_mean + 1e-8))
            
            # Predict using model
            features = [amp_mean, amp_std, amp_cv]
            pred, details = predict_with_model_features(features, self.model_path)
            
            # Get confidence
            proba = details.get('proba', [[0, 0]])[0]
            confidence = max(proba) if proba else 0.5
            
            timestamp = datetime.now().isoformat()
            result = {
                'timestamp': timestamp,
                'prediction': 'PERSON' if pred == 1 else 'NO PERSON',
                'confidence': float(confidence),
                'packets': len(csv_data),
                'amp_mean': amp_mean,
                'amp_std': amp_std,
                'amp_cv': amp_cv,
            }
            
            self.prediction_queue.put(result)
            self.stats['predictions'] += 1
            self.stats['last_prediction'] = result
            self.stats['last_timestamp'] = timestamp
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"[ERROR] Prediction failed: {e}")
    
    def display_thread(self):
        """Display predictions in real-time."""
        print("\n" + "="*80)
        print("REAL-TIME CSI PERSON DETECTION")
        print("="*80)
        print(f"Model: {self.model_path}")
        print(f"Window Size: {self.window_size} packets")
        print("="*80 + "\n")
        
        while not self.stop_event.is_set():
            try:
                result = self.prediction_queue.get(timeout=1)
                
                pred_color = '\033[92m' if result['prediction'] == 'PERSON' else '\033[94m'
                reset_color = '\033[0m'
                
                print(f"{pred_color}[{result['timestamp']}] {result['prediction']} | "
                      f"Confidence: {result['confidence']:.2%} | "
                      f"Packets: {result['packets']} | "
                      f"Amp: μ={result['amp_mean']:.2e} σ={result['amp_std']:.2e} "
                      f"CV={result['amp_cv']:.4f}{reset_color}")
                
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                break
        
        print("\n" + "="*80)
        print("DETECTION STOPPED")
        print("="*80)
    
    def run(self):
        """Start all threads."""
        print(f"Starting realtime detection on {self.port}...")
        
        reader_t = threading.Thread(target=self.serial_reader_thread, daemon=True)
        processor_t = threading.Thread(target=self.packet_processor_thread, daemon=True)
        display_t = threading.Thread(target=self.display_thread, daemon=False)
        
        reader_t.start()
        processor_t.start()
        display_t.start()
        
        try:
            display_t.join()
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            self.stop_event.set()
            reader_t.join(timeout=2)
            processor_t.join(timeout=2)
            
            print("\n" + "-"*80)
            print("FINAL STATISTICS")
            print("-"*80)
            print(f"Total packets received: {self.stats['total_packets']}")
            print(f"Total predictions: {self.stats['predictions']}")
            print(f"Errors: {self.stats['errors']}")
            if self.stats['last_prediction']:
                print(f"Last prediction: {self.stats['last_prediction']['prediction']} "
                      f"({self.stats['last_prediction']['confidence']:.2%} confidence)")
            print("-"*80)


def main():
    parser = argparse.ArgumentParser(
        description='Real-time CSI person detection using trained model'
    )
    parser.add_argument('--port', required=True, help='Serial port (e.g., /dev/ttyUSB0)')
    parser.add_argument('--baudrate', type=int, default=2000000, help='Serial baudrate')
    parser.add_argument('--window', type=int, default=200, help='Window size (packets per prediction)')
    parser.add_argument('--model', default='models/rf_person_detector.joblib', help='Path to trained model')
    
    args = parser.parse_args()
    
    try:
        detector = RealtimeDetector(
            port=args.port,
            baudrate=args.baudrate,
            window_size=args.window,
            model_path=args.model,
        )
        detector.run()
    except Exception as e:
        print(f"[FATAL] {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
