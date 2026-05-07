#!/usr/bin/env python3
"""Simple Tkinter GUI to run the dedup/split → train → evaluate pipeline and show logs/results.

Buttons:
 - Dedup (dry-run)
 - Dedup & Split
 - Train
 - Evaluate
 - Run Full Pipeline (sequential)

Logs appear in the text area; JSON reports are parsed to show basic metrics after tasks complete.
"""
from __future__ import annotations
import json
import os
import queue
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText


class PipelineGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('WiVSD Pipeline')
        self.geometry('900x640')
        self.queue: queue.Queue = queue.Queue()

        # Config vars
        self.pos_src = tk.StringVar(value='Router')
        self.neg_src = tk.StringVar(value='router no person')
        self.train_tmp = tk.StringVar(value='tmp_train')
        self.holdout = tk.StringVar(value='holdout')
        self.fraction = tk.DoubleVar(value=0.2)
        self.seed = tk.IntVar(value=42)
        self.model_out = tk.StringVar(value='models/rf_person_detector_retrained.joblib')
        self.model_report = tk.StringVar(value='reports/model_train_retrained_gui.json')
        self.eval_report = tk.StringVar(value='reports/eval_retrained_fullpipeline_gui.json')
        self.jobs = tk.IntVar(value=4)
        self.threshold = tk.DoubleVar(value=0.5)
        self.dry_run = tk.BooleanVar(value=True)
        self.move_duplicates = tk.BooleanVar(value=False)
        self.duplicates_dir = tk.StringVar(value='data_duplicates')
        self.rebuild_report = tk.StringVar(value='reports/rebuild_split_gui.json')

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self):
        frm = ttk.Frame(self)
        frm.pack(fill='x', padx=8, pady=8)

        # Row 1: source directories
        ttk.Label(frm, text='Pos src:').grid(column=0, row=0, sticky='w')
        ttk.Entry(frm, textvariable=self.pos_src, width=28).grid(column=1, row=0, sticky='w')
        ttk.Label(frm, text='Neg src:').grid(column=2, row=0, sticky='w', padx=(12, 0))
        ttk.Entry(frm, textvariable=self.neg_src, width=28).grid(column=3, row=0, sticky='w')

        # Row 2: train/holdout dirs
        ttk.Label(frm, text='Train tmp:').grid(column=0, row=1, sticky='w')
        ttk.Entry(frm, textvariable=self.train_tmp, width=28).grid(column=1, row=1, sticky='w')
        ttk.Label(frm, text='Holdout:').grid(column=2, row=1, sticky='w', padx=(12, 0))
        ttk.Entry(frm, textvariable=self.holdout, width=28).grid(column=3, row=1, sticky='w')

        # Row 3: fraction/seed
        ttk.Label(frm, text='Holdout fraction:').grid(column=0, row=2, sticky='w')
        ttk.Entry(frm, textvariable=self.fraction, width=10).grid(column=1, row=2, sticky='w')
        ttk.Label(frm, text='Seed:').grid(column=2, row=2, sticky='w')
        ttk.Entry(frm, textvariable=self.seed, width=10).grid(column=3, row=2, sticky='w')

        # Row 4: model/report paths
        ttk.Label(frm, text='Model out:').grid(column=0, row=3, sticky='w')
        ttk.Entry(frm, textvariable=self.model_out, width=40).grid(column=1, row=3, columnspan=3, sticky='w')

        # Row 5: eval options
        ttk.Label(frm, text='Jobs:').grid(column=0, row=4, sticky='w')
        ttk.Entry(frm, textvariable=self.jobs, width=6).grid(column=1, row=4, sticky='w')
        ttk.Label(frm, text='Threshold:').grid(column=2, row=4, sticky='w')
        ttk.Entry(frm, textvariable=self.threshold, width=6).grid(column=3, row=4, sticky='w')

        # Row 6: checkbuttons and duplicates settings
        ttk.Checkbutton(frm, text='Dry run (dedup)', variable=self.dry_run).grid(column=0, row=5, sticky='w')
        ttk.Checkbutton(frm, text='Move duplicates', variable=self.move_duplicates).grid(column=1, row=5, sticky='w', padx=(6, 0))
        ttk.Label(frm, text='Duplicates dir:').grid(column=2, row=5, sticky='w')
        ttk.Entry(frm, textvariable=self.duplicates_dir, width=20).grid(column=3, row=5, sticky='w')

        # Buttons
        btn_frm = ttk.Frame(self)
        btn_frm.pack(fill='x', padx=8)
        ttk.Button(btn_frm, text='Dedup (dry-run)', command=self._on_dedup_dry).pack(side='left')
        ttk.Button(btn_frm, text='Dedup & Split', command=self._on_dedup).pack(side='left', padx=(6, 0))
        ttk.Button(btn_frm, text='Show duplicates', command=self._show_duplicates).pack(side='left', padx=(6, 0))
        ttk.Button(btn_frm, text='Upload & Eval', command=self._on_upload_and_eval).pack(side='left', padx=(6, 0))
        ttk.Button(btn_frm, text='Train', command=self._on_train).pack(side='left', padx=(6, 0))
        ttk.Button(btn_frm, text='Evaluate', command=self._on_evaluate).pack(side='left', padx=(6, 0))
        ttk.Button(btn_frm, text='Full pipeline', command=self._on_full_pipeline).pack(side='left', padx=(6, 0))
        ttk.Button(btn_frm, text='Clear log', command=lambda: self.log.delete('1.0', 'end')).pack(side='right')

        # Log area
        self.log = ScrolledText(self, height=18)
        self.log.pack(fill='both', expand=True, padx=8, pady=8)
        self.log.configure(state='normal')

        # Metrics area
        metrics_frm = ttk.Frame(self)
        metrics_frm.pack(fill='x', padx=8, pady=(0, 8))
        ttk.Label(metrics_frm, text='Last metrics:').pack(anchor='w')
        self.metrics_text = tk.Text(metrics_frm, height=8)
        self.metrics_text.pack(fill='x')
        self.metrics_text.configure(state='disabled')

        # Single-file result area
        single_frm = ttk.Frame(self)
        single_frm.pack(fill='x', padx=8, pady=(0, 8))
        ttk.Label(single_frm, text='Last file result:').pack(anchor='w')
        self.single_text = tk.Text(single_frm, height=6)
        self.single_text.pack(fill='x')
        self.single_text.configure(state='disabled')

    def _enqueue(self, item):
        self.queue.put(item)

    def _poll_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                if isinstance(item, tuple) and item and item[0] == 'line':
                    self.log.insert('end', item[1])
                    self.log.see('end')
                elif isinstance(item, tuple) and item and item[0] == 'done':
                    code = item[1]
                    cb = item[2]
                    self.log.insert('end', f"\n[PROCESS EXIT {code}]\n")
                    self.log.see('end')
                    if cb:
                        try:
                            cb()
                        except Exception as e:
                            self.log.insert('end', f"Callback error: {e}\n")
                else:
                    self.log.insert('end', str(item))
                    self.log.see('end')
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _run_subprocess(self, cmd, cwd=None, callback=None):
        def worker():
            env = os.environ.copy()
            # ensure package import works
            env['PYTHONPATH'] = str(Path.cwd() / 'src')
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, cwd=cwd, bufsize=1)
            except Exception as e:
                self._enqueue(('line', f'Failed to start process: {e}\n'))
                self._enqueue(('done', 1, callback))
                return
            for raw in p.stdout:
                try:
                    line = raw.decode('utf-8', errors='replace')
                except Exception:
                    line = str(raw)
                self._enqueue(('line', line))
            ret = p.wait()
            self._enqueue(('done', ret, callback))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_dedup_dry(self):
        cmd = [
            'python3', 'scripts/dedup_and_split.py',
            '--pos-src', self.pos_src.get(), '--neg-src', self.neg_src.get(),
            '--train-tmp', self.train_tmp.get(), '--holdout-dir', self.holdout.get(),
            '--fraction', str(self.fraction.get()), '--seed', str(self.seed.get()),
            '--report', self.rebuild_report.get(), '--duplicates-dir', self.duplicates_dir.get(), '--dry-run'
        ]
        self.log.insert('end', f"Running: {' '.join(cmd)}\n")
        self._run_subprocess(cmd, callback=lambda: self._on_report_generated(self.rebuild_report.get()))

    def _on_dedup(self):
        cmd = [
            'python3', 'scripts/dedup_and_split.py',
            '--pos-src', self.pos_src.get(), '--neg-src', self.neg_src.get(),
            '--train-tmp', self.train_tmp.get(), '--holdout-dir', self.holdout.get(),
            '--fraction', str(self.fraction.get()), '--seed', str(self.seed.get()),
            '--report', self.rebuild_report.get(), '--duplicates-dir', self.duplicates_dir.get()
        ]
        if self.dry_run.get():
            cmd.append('--dry-run')
        if self.move_duplicates.get():
            cmd.append('--move-duplicates')
        self.log.insert('end', f"Running: {' '.join(cmd)}\n")
        self._run_subprocess(cmd, callback=lambda: self._on_report_generated(self.rebuild_report.get()))

    def _on_train(self):
        cmd = [
            'python3', 'scripts/train_ml_classifier.py',
            '--root', '.',
            '--pos-train', str(Path(self.train_tmp.get()) / self.pos_src.get()),
            '--neg-train', str(Path(self.train_tmp.get()) / self.neg_src.get()),
            '--model', self.model_out.get(),
            '--out', self.model_report.get()
        ]
        self.log.insert('end', f"Running train: {' '.join(cmd)}\n")
        self._run_subprocess(cmd, callback=lambda: self._on_report_generated(self.model_report.get()))

    def _on_evaluate(self):
        cmd = [
            'python3', '-m', 'csi_preprocessing.evaluate',
            '--root', self.holdout.get(),
            '--model', self.model_out.get(),
            '--out', self.eval_report.get(),
            '--jobs', str(self.jobs.get()),
            '--threshold', str(self.threshold.get())
        ]
        self.log.insert('end', f"Running evaluate: {' '.join(cmd)}\n")
        self._run_subprocess(cmd, callback=lambda: self._on_report_generated(self.eval_report.get()))

    def _on_full_pipeline(self):
        # Run dedup -> train -> evaluate sequentially
        def seq():
            self._on_dedup()  # starts thread
            # Wait until dedup report appears, then train
            # Simple polling for report file
            report = Path(self.rebuild_report.get())
            for _ in range(600):
                if report.exists():
                    break
                else:
                    import time

                    time.sleep(0.5)
            self._on_train()
            # Wait for model report
            model_report = Path(self.model_report.get())
            for _ in range(1200):
                if model_report.exists():
                    break
                else:
                    import time

                    time.sleep(0.5)
            self._on_evaluate()

        t = threading.Thread(target=seq, daemon=True)
        t.start()

    def _on_upload_and_eval(self):
        path = filedialog.askopenfilename(title='Select CSV file', filetypes=[('CSV', '*.csv'), ('All', '*.*')])
        if not path:
            return
        self.log.insert('end', f'Uploading file for eval: {path}\n')
        t = threading.Thread(target=self._eval_file_worker, args=(path,), daemon=True)
        t.start()

    def _eval_file_worker(self, path: str):
        # Ensure src is importable
        try:
            import sys
            sys.path.insert(0, str(Path.cwd() / 'src'))
            from csi_preprocessing.classifier import predict_with_model_from_csv
        except Exception as e:
            self._enqueue(('line', f'Failed to import classifier: {e}\n'))
            return

        try:
            pred, details = predict_with_model_from_csv(Path(path), model_path=self.model_out.get(), threshold=self.threshold.get())
        except Exception as e:
            self._enqueue(('line', f'Error during prediction: {e}\n'))
            return

        # Prepare message
        if isinstance(details, dict) and details.get('error'):
            msg = f'Prediction error for {path}: {details}\n'
            self._enqueue(('line', msg))
            self._show_single_result({'path': path, 'error': details})
            return

        res = {'path': path, 'prediction': int(pred), 'details': details}
        # extract confidence if provided
        conf = None
        if isinstance(details, dict):
            conf = details.get('confidence')
            if conf is None and details.get('proba'):
                try:
                    p = details.get('proba')
                    # proba may be nested list e.g. [[p0, p1]]
                    if isinstance(p, list) and p and isinstance(p[0], (list, tuple)) and len(p[0]) > 1:
                        conf = float(p[0][1])
                except Exception:
                    conf = None

        if conf is not None:
            self._enqueue(('line', f'Predicted {res["prediction"]} for {path} (confidence={conf:.3f})\n'))
        else:
            self._enqueue(('line', f'Predicted {res["prediction"]} for {path}\n'))
        self._show_single_result(res)

    def _show_single_result(self, data: dict):
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        def ui_update():
            self.single_text.configure(state='normal')
            self.single_text.delete('1.0', 'end')
            self.single_text.insert('end', pretty)
            self.single_text.configure(state='disabled')
        self.after(0, ui_update)

    def _show_duplicates(self):
        rpt = Path(self.rebuild_report.get())
        if not rpt.exists():
            self._enqueue(('line', f'Report not found: {rpt}\n'))
            return
        try:
            data = json.loads(rpt.read_text(encoding='utf-8'))
        except Exception as e:
            self._enqueue(('line', f'Failed to read report {rpt}: {e}\n'))
            return

        win = tk.Toplevel(self)
        win.title('Duplicate samples')
        st = ScrolledText(win, width=120, height=30)
        st.pack(fill='both', expand=True)
        if not isinstance(data, dict):
            st.insert('end', json.dumps(data, indent=2, ensure_ascii=False))
        else:
            for cls in [k for k in data.keys() if k not in ('cross_class_overlaps', 'cross_class_sample')]:
                node = data.get(cls, {})
                dup = node.get('duplicate_sample', {}) if isinstance(node, dict) else {}
                if dup:
                    st.insert('end', f'Class: {cls}\n')
                    for h, paths in dup.items():
                        st.insert('end', f'Hash: {h}\n')
                        for p in paths:
                            st.insert('end', f'  {p}\n')
                        st.insert('end', '\n')
        st.configure(state='disabled')

    def _on_report_generated(self, path_str: str):
        p = Path(path_str)
        if not p.exists():
            self._enqueue(('line', f'Report not found: {path_str}\n'))
            return
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            self._enqueue(('line', f'Failed to read report {path_str}: {e}\n'))
            return
        # Pretty-print some keys
        pretty = json.dumps(d, indent=2, ensure_ascii=False)
        self.metrics_text.configure(state='normal')
        self.metrics_text.delete('1.0', 'end')
        self.metrics_text.insert('end', pretty)
        self.metrics_text.configure(state='disabled')
        self._enqueue(('line', f'Parsed report: {path_str}\n'))


def main():
    app = PipelineGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
