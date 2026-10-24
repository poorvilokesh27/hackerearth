"""Validation suite for output.csv and step schemas."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ALLOWED_STATUSES: Set[str] = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}

ALLOWED_OPERATION_STATES: Dict[Tuple[str, str], str] = {
    # Phase, Operation -> State
    ("FINDING", "REPORT_REMAINING_RECORD"): "PRESENT",
    ("FINDING", "REPORT_EXPOSED_PII"): "PRESENT",
    ("FINDING", "REPORT_ACTIVE_DATA_FLOW"): "ACTIVE",
    ("FINDING", "REPORT_RESTORE_RISK"): "ACTIVE",
    ("REMEDIATION", "DISABLE_DATA_FLOW"): "DISABLED",
    ("REMEDIATION", "BLOCK_RESTORE"): "BLOCKED",
    ("REMEDIATION", "DELETE_RECORD"): "ABSENT",
    ("REMEDIATION", "REDACT_RECORD"): "REDACTED",
    ("REMEDIATION", "ANONYMIZE_RECORD"): "ANONYMIZED",
    ("VERIFICATION", "VERIFY_RECORD_ABSENT"): "ABSENT",
    ("VERIFICATION", "VERIFY_RECORD_PRESENT"): "PRESENT",
    ("VERIFICATION", "VERIFY_RECORD_REDACTED"): "REDACTED",
    ("VERIFICATION", "VERIFY_RECORD_ANONYMIZED"): "ANONYMIZED",
    ("VERIFICATION", "VERIFY_DATA_FLOW_DISABLED"): "DISABLED",
    ("VERIFICATION", "VERIFY_RESTORE_BLOCKED"): "BLOCKED",
}

REQUIRED_STEP_FIELDS: Set[str] = {
    "step_no",
    "phase",
    "system_id",
    "resource_id",
    "operation",
    "state",
    "evidence_id",
}


def validate_output_file(
    filepath: Path, expected_row_count: int = 518
) -> Dict[str, Any]:
    """
    Validate output.csv against all specification requirements.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not filepath.exists():
        return {
            "valid": False,
            "row_count": 0,
            "errors": [f"File {filepath} does not exist"],
        }

    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return {"valid": False, "row_count": 0, "errors": ["File is empty"]}

        # 1. Header validation
        expected_header = ["case_id", "deletion_status", "steps_json"]
        if header != expected_header:
            errors.append(f"Invalid header: got {header}, expected {expected_header}")

        rows = list(reader)

    # 2. Row count validation
    data_rows_count = len(rows)
    if data_rows_count != expected_row_count:
        warnings.append(
            f"Row count mismatch: got {data_rows_count} rows, expected {expected_row_count}"
        )

    # 3. Sorting check
    case_ids = [r[0] for r in rows if len(r) > 0]
    if case_ids != sorted(case_ids):
        errors.append("Rows are not sorted by case_id ascending")

    # 4. Row-level validation
    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}
    total_steps = 0

    for idx, row in enumerate(rows, 1):
        if len(row) != 3:
            errors.append(f"Row {idx} has {len(row)} columns, expected 3")
            continue

        cid, status, steps_str = row[0], row[1], row[2]

        if status not in ALLOWED_STATUSES:
            errors.append(f"Row {idx} ({cid}): invalid status '{status}'")
            continue

        status_counts[status] = status_counts.get(status, 0) + 1

        try:
            steps = json.loads(steps_str)
        except json.JSONDecodeError as e:
            errors.append(f"Row {idx} ({cid}): steps_json decode error: {e}")
            continue

        if not isinstance(steps, list):
            errors.append(f"Row {idx} ({cid}): steps_json is not an array")
            continue

        total_steps += len(steps)

        # Status specific rules
        if status == "NOT_APPLICABLE":
            if steps != []:
                errors.append(f"Row {idx} ({cid}): NOT_APPLICABLE must have empty array '[]'")
            continue

        if status == "COMPLETE":
            for s in steps:
                if s.get("phase") != "VERIFICATION":
                    errors.append(
                        f"Row {idx} ({cid}): COMPLETE case contains non-verification step ({s.get('phase')})"
                    )

        if status == "INCOMPLETE":
            has_finding = any(s.get("phase") == "FINDING" for s in steps)
            has_rem = any(s.get("phase") == "REMEDIATION" for s in steps)
            has_ver = any(s.get("phase") == "VERIFICATION" for s in steps)
            if not has_finding:
                errors.append(f"Row {idx} ({cid}): INCOMPLETE case missing FINDING steps")
            if not has_rem:
                errors.append(f"Row {idx} ({cid}): INCOMPLETE case missing REMEDIATION steps")
            if not has_ver:
                errors.append(f"Row {idx} ({cid}): INCOMPLETE case missing VERIFICATION steps")

            # In incomplete cases, remediation and future verification must have empty evidence_id
            for s in steps:
                if s.get("phase") in {"REMEDIATION", "VERIFICATION"} and s.get("evidence_id") != "":
                    errors.append(
                        f"Row {idx} ({cid}): {s.get('phase')} step in INCOMPLETE case must have empty evidence_id"
                    )

        # Step object schema validation
        for s_idx, s in enumerate(steps, 1):
            if not isinstance(s, dict):
                errors.append(f"Row {idx} ({cid}) step {s_idx}: not a dict object")
                continue

            missing_fields = REQUIRED_STEP_FIELDS - set(s.keys())
            if missing_fields:
                errors.append(f"Row {idx} ({cid}) step {s_idx}: missing fields {missing_fields}")

            if s.get("step_no") != s_idx:
                errors.append(
                    f"Row {idx} ({cid}) step {s_idx}: invalid step_no {s.get('step_no')}, expected {s_idx}"
                )

            pair = (s.get("phase", ""), s.get("operation", ""))
            expected_state = ALLOWED_OPERATION_STATES.get(pair)
            if expected_state is None:
                errors.append(f"Row {idx} ({cid}) step {s_idx}: invalid phase/operation pair {pair}")
            elif s.get("state") != expected_state:
                errors.append(
                    f"Row {idx} ({cid}) step {s_idx}: state '{s.get('state')}' does not match expected '{expected_state}' for {pair}"
                )

    is_valid = len(errors) == 0

    return {
        "valid": is_valid,
        "row_count": data_rows_count,
        "total_steps": total_steps,
        "status_counts": status_counts,
        "errors": errors[:50],  # cap to top 50
        "warnings": warnings,
    }

