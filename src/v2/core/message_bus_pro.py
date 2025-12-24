# ===============================================================
# NSC Message Bus PRO (Institutional Version)
# File: src/v2/core/message_bus_pro.py
# ===============================================================

import json
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

from src.v2.utils.file_utils import ensure_dir, append_jsonl
from src.v2.utils.paths import get_data_dir
from src.v2.logger import get_logger

logger = get_logger("message_bus_pro")


# ===============================================================
# Internal Queues (Priority-based)
# ===============================================================

class PriorityQueue:
    def __init__(self):
        self.queue_high = []
        self.queue_medium = []
        self.queue_low = []
        self.lock = Lock()

    def push(self, event, priority="medium"):
        with self.lock:
            if priority == "high":
                self.queue_high.append(event)
            elif priority == "low":
                self.queue_low.append(event)
            else:
                self.queue_medium.append(event)

    def pop(self):
        with self.lock:
            if self.queue_high:
                return self.queue_high.pop(0)
            if self.queue_medium:
                return self.queue_medium.pop(0)
            if self.queue_low:
                return self.queue_low.pop(0)
        return None

    def size(self):
        with self.lock:
            return len(self.queue_high) + len(self.queue_medium) + len(self.queue_low)


queue = PriorityQueue()


# ===============================================================
# Backpressure Metrics
# ===============================================================

event_counter = []
last_cleanup = time.time()


def update_rate():
    """
    Count events over the last minute to detect congestion.
    """
    global event_counter, last_cleanup

    ts = time.time()
    event_counter.append(ts)

    # cleanup older than 60 sec
    if ts - last_cleanup > 5:
        event_counter = [t for t in event_counter if ts - t <= 60]
        last_cleanup = ts

    return len(event_counter)


def compute_backpressure():
    rate = update_rate()

    if rate > 1000:
        return "emergency"
    elif rate > 300:
        return "throttled"
    else:
        return "normal"


# ===============================================================
# Persistent Storage
# ===============================================================

DATA_DIR = get_data_dir()
EVENT_BUS_FILE = Path(DATA_DIR) / "telemetry" / "event_bus.jsonl"
ensure_dir(EVENT_BUS_FILE.parent)


def persist_event(event):
    try:
        append_jsonl(EVENT_BUS_FILE, event)
    except Exception as e:
        logger.error(f"[message_bus_pro] ERROR persist_event: {e}")


# ===============================================================
# Publisher with Retry + Priority + Backpressure
# ===============================================================

def publish_event(event_type, source, payload, priority="medium", severity="info"):
    """
    Institutional Message Bus event publisher.
    """

    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": event_type,
        "source": source,
        "severity": severity,
        "priority": priority,
        "payload": payload,
        "backpressure": compute_backpressure(),
    }

    queue.push(event, priority)

    # Retry delivery with exponential backoff
    delay = 0.1
    for _ in range(6):  # retry 6 times max
        try:
            persist_event(event)
            return True
        except Exception:
            time.sleep(delay)
            delay = min(delay * 2, 1.6)

    logger.critical("[message_bus_pro] UNABLE TO PERSIST EVENT AFTER RETRIES")
    return False


# ===============================================================
# Consumer (optional for debugging tools)
# ===============================================================

def read_last_events(limit=50):
    events = []
    if not EVENT_BUS_FILE.exists():
        return []

    with open(EVENT_BUS_FILE, "r") as f:
        for line in f:
            try:
                events.append(json.loads(line.strip()))
            except:
                continue

    return events[-limit:]


# ===============================================================
# CLI for debugging
# ===============================================================

if __name__ == "__main__":
    print("=== NSC Message Bus PRO ===")
    print(f"File: {EVENT_BUS_FILE}")
    print(f"Queue size: {queue.size()}")
    last = read_last_events(5)
    print("\nLast events:")
    for e in last:
        print(json.dumps(e, indent=2))
