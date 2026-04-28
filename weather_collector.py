import argparse
import socket
import requests
import time
import csv
from datetime import datetime
import os
from typing import Optional

# ================= UDP CONFIG =================
UDP_IP = "0.0.0.0"
UDP_PORT = 12345

# ================= OPEN-METEO CONFIG =================
LAT = 21.046647   # Hà Nội
LON = 105.801453


def get_weather() -> tuple[Optional[float], Optional[float]]:
    """Lấy weather hiện tại từ Open-Meteo."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}"
        f"&current=temperature_2m,relative_humidity_2m"
    )
    try:
        res = requests.get(url, timeout=5)
        data = res.json()
        temp = data["current"]["temperature_2m"]
        humi = data["current"]["relative_humidity_2m"]
        return temp, humi
    except Exception:
        return None, None


def default_csv_filename(prefix: str = "data_log") -> str:
    """Tạo tên file CSV kèm datetime để không bị đè."""
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def ensure_csv_header(csv_file: str, scenario_count: int = 5) -> None:
    if not os.path.exists(csv_file):
        with open(csv_file, mode="w", newline="") as f:
            writer = csv.writer(f)
            header = [
                "time",
                "temp_in", "humi_in",
                "temp_out", "humi_out"
            ]
            header += [f"scenario_{i+1}" for i in range(scenario_count)]
            writer.writerow(header)


def collect_loop(
    csv_file: Optional[str] = None,
    interval: int = 60,
    stop_event=None,
    scenarios: Optional[list[str]] = None,
    udp_port: Optional[int] = None,
) -> None:
    """Vòng lặp thu thập dữ liệu UDP và weather, ghi ra CSV."""
    if csv_file is None:
        csv_file = default_csv_filename()
    
    if udp_port is None:
        udp_port = UDP_PORT

    scenarios = scenarios or []
    if len(scenarios) > 5:
        print("Chỉ hỗ trợ lên đến 5 scenario, phần dư sẽ bị bỏ qua.")
        scenarios = scenarios[:5]

    # Luôn dùng 5 cột scenario trong CSV (có thể để trống)
    while len(scenarios) < 5:
        scenarios.append("")

    ensure_csv_header(csv_file, scenario_count=5)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, udp_port))
    sock.settimeout(1.0)  # 1 second timeout so stop_event can be checked frequently
    print(f"Listening UDP at {UDP_IP}:{udp_port}...")

    last_weather_time = 0
    weather_cache = (None, None)

    while stop_event is None or not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(1024)
        except socket.timeout:
            # Timeout - check stop_event and try again
            continue
        except KeyboardInterrupt:
            print("Stopped by keyboard")
            break

        message = data.decode().strip()

        try:
            temp_in, humi_in = map(float, message.split(","))
        except ValueError:
            print("Sai định dạng:", message)
            continue

        if time.time() - last_weather_time > interval:
            weather_cache = get_weather()
            last_weather_time = time.time()

        temp_out, humi_out = weather_cache

        now = int(time.time())

        row = [
            now,
            temp_in, humi_in,
            temp_out, humi_out,
        ]
        row += scenarios[:5]

        with open(csv_file, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        print("\n===== DỮ LIỆU =====")
        print(f"Time       : {now}")
        print(f"Trong nhà  : {temp_in} °C | {humi_in} %")
        if temp_out is not None:
            print(f"Ngoài trời : {temp_out} °C | {humi_out} %")
        else:
            print("Ngoài trời : Không có dữ liệu")
        if scenarios:
            print("Scenario   :", scenarios)

    sock.close()


def run(csv_file: Optional[str] = None, interval: int = 60, scenarios: Optional[list[str]] = None, udp_port: Optional[int] = None) -> None:
    collect_loop(csv_file=csv_file, interval=interval, scenarios=scenarios, udp_port=udp_port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weather collector + UDP data logger")
    parser.add_argument("--csv-file", default=None, help="CSV output file path")
    parser.add_argument("--interval", type=int, default=60, help="Giây giữa các lần gọi API thời tiết")
    parser.add_argument("--udp-port", type=int, default=UDP_PORT, help="UDP port to listen on")
    parser.add_argument("--scenario", action="append", default=[], help="Thêm scenario (có thể gọi nhiều lần)")
    args = parser.parse_args()

    run(csv_file=args.csv_file, interval=args.interval, scenarios=args.scenario, udp_port=args.udp_port)

# === Usage example from other files ===
# from threading import Thread, Event
# from weather_collector import collect_loop, default_csv_filename
# stop_event = Event()
# t = Thread(target=collect_loop, kwargs={"csv_file": default_csv_filename(), "interval": 60, "stop_event": stop_event})
# t.start()
# ... sau này:
# stop_event.set(); t.join()

# subprocess usage (chạy tệp ít nhất):
# python3 weather_collector.py
