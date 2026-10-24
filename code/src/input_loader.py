"""Input loading and schema validation for deletion audit agent."""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "dataset"


def get_dataset_dir() -> Path:
    """Return dataset directory path."""
    return DATASET_DIR


def load_csv(filename: str, dataset_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """Load a CSV file and return a list of row dicts."""
    base_dir = dataset_dir or DATASET_DIR
    filepath = base_dir / filename
    if not filepath.exists():
        # Fallback for deletion_requests -> sample_deletion_requests
        if filename == "deletion_requests.csv":
            fallback = base_dir / "sample_deletion_requests.csv"
            if fallback.exists():
                filepath = fallback
            else:
                raise FileNotFoundError(f"Neither {filename} nor fallback found in {base_dir}")
        else:
            raise FileNotFoundError(f"File {filename} not found in {base_dir}")

    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_deletion_requests(filename: str = "deletion_requests.csv", dataset_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """Load deletion requests dataset."""
    return load_csv(filename, dataset_dir)


def load_deletion_rules(filename: str = "deletion_rules.csv", dataset_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """Load deletion policy rules."""
    return load_csv(filename, dataset_dir)


def load_user_identities(filename: str = "user_identities.csv", dataset_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """Load user identities dataset."""
    return load_csv(filename, dataset_dir)


def load_audit_log(filename: str = "user_audit_log.csv", dataset_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """Load user audit log events."""
    return load_csv(filename, dataset_dir)


def load_system_activity(filename: str = "system_activity.csv", dataset_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """Load system activity events."""
    return load_csv(filename, dataset_dir)


def load_evidence_files(filename: str = "evidence_files.csv", dataset_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """Load evidence files manifest."""
    return load_csv(filename, dataset_dir)
