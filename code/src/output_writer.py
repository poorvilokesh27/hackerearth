"""Output writer for deletion audit agent."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def write_output_csv(rows: List[Dict[str, Any]], filepath: Path) -> None:
    """
    Write output rows to CSV strictly adhering to RFC 4180 and challenge specification.
    Columns in exact order: case_id,deletion_status,steps_json
    Rows sorted by case_id.
    """
    # Sort rows by case_id
    sorted_rows = sorted(rows, key=lambda r: r["case_id"])

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for r in sorted_rows:
            # steps_json can be list or string
            steps_val = r["steps_json"]
            if isinstance(steps_val, list):
                steps_str = json.dumps(steps_val, ensure_ascii=False, separators=(",", ":"))
            else:
                steps_str = str(steps_val)
            writer.writerow([r["case_id"], r["deletion_status"], steps_str])

