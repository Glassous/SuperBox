"""Print cgroup acceptance evidence after Linux tests (not an API endpoint)."""
import json
from pathlib import Path

root = Path("/sys/fs/cgroup")
print(json.dumps({
    "memory_limit_mib": int((root / "memory.max").read_text()) // (1024 * 1024),
    "memory_peak_mib": round(int((root / "memory.peak").read_text()) / (1024 * 1024), 2),
    "memory_events": dict(line.split() for line in (root / "memory.events").read_text().splitlines()),
}))
