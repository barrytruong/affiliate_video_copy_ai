"""Manual end-to-end smoke check. Run the server first (`python run.py`), then:
    python tests/smoke_test.py [path/to/local/video.mp4]
If no path is given, only /api/health is checked.
"""

import sys
import time
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8000"


def check_health() -> None:
    resp = requests.get(f"{BASE_URL}/api/health", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print("health:", data)
    assert "ollama_ok" in data


def run_job_with_file(path: Path) -> None:
    with open(path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/api/jobs", files={"file": (path.name, f)}, timeout=60
        )
    resp.raise_for_status()
    job_id = resp.json()["job_id"]
    print("job_id:", job_id)

    for _ in range(180):
        resp = requests.get(f"{BASE_URL}/api/jobs/{job_id}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print("status:", data["status"], "-", data["stage_message"])
        if data["status"] in ("done", "error"):
            break
        time.sleep(2)

    assert data["status"] == "done", f"Job did not finish successfully: {data}"
    assert data["script"], "Script is empty"
    print("\n--- SCRIPT ---\n")
    print(data["script"])


if __name__ == "__main__":
    check_health()
    if len(sys.argv) > 1:
        run_job_with_file(Path(sys.argv[1]))
    else:
        print("No file path given — skipping the job flow. Pass a local video path to test it.")
