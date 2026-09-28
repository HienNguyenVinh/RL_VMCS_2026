"""Experiment Logger for recording metrics, sweeps, and convergence statistics."""
import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ExperimentLogger:
    """Logs experimental results to CSV and JSON formats."""

    def __init__(self, log_dir: str = "experiments/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_run(self, run_id: str, metadata: Dict[str, Any], metrics: Dict[str, Any]) -> None:
        """Log a complete experiment run."""
        record = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            **metadata,
            **metrics,
        }

        # Append to CSV
        csv_file = self.log_dir / "experiment_records.csv"
        file_exists = csv_file.exists()

        with open(csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(record.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)

        # Write detailed JSON
        json_file = self.log_dir / f"{run_id}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
