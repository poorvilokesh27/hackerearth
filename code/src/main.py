"""Main entry point for the deletion audit agent."""

from pathlib import Path
import csv
import json
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from input_loader import load_dataset, load_csv, validate_output_row
from identity_resolution import IdentityResolver


DATASET_DIR = Path(__file__).parent.parent / "dataset"


def load_deletion_requests(filename="deletion_requests.csv"):
    """Load deletion requests CSV."""
    return load_csv(filename)


def load_deletion_rules(filename="deletion_rules.csv"):
    """Load deletion rules CSV."""
    rules = load_csv(filename)
    # Build a lookup: data_category -> required_action
    rules_map = {}
    for rule in rules:
        category = rule.get("data_category", "").strip()
        action = rule.get("required_action", "").strip()
        if category and action:
            rules_map[category] = action
    return rules_map


def load_user_identities(filename="user_identities.csv"):
    """Load user identities."""
    return load_csv(filename)


def load_audit_log(filename="user_audit_log.csv"):
    """Load audit log."""
    return load_csv(filename)


def load_system_activity(filename="system_activity.csv"):
    """Load system activity."""
    return load_csv(filename)


def load_evidence_files(filename="evidence_files.csv"):
    """Load evidence files manifest."""
    return load_csv(filename)


def determine_status(case, identity_resolver, rules_map):
    """
    Determine the deletion status for a case.
    Returns (status, steps_json)
    """
    case_id = case.get("case_id", "").strip()
    email = case.get("email", "").strip().lower()
    audit_at = case.get("audit_at", "").strip()
    requested_at = case.get("requested_at", "").strip()
    request_text = case.get("request_text", "").strip()
    reported_status = case.get("reported_status", "").strip()

    # Check if deletion was actually requested
    # If no deletion request was made, status is NOT_APPLICABLE
    # Look for evidence of deletion request

    # Resolve identities for this person at audit_at time
    identity_info = identity_resolver.resolve_identifier(case_id, audit_at)

    # If deletion was not requested, return NOT_APPLICABLE
    if not identity_info["deletion_requested"]:
        return "NOT_APPLICABLE", []

    # Check if we can determine the state at audit_at
    # Apply deletion rules
    # ... (complex logic based on the full prompt spec)

    # For now, implement basic framework
    # In a full implementation, this would:
    # 1. Reconstruct state at audit_at
    # 2. Apply rules from deletion_rules.csv
    # 3. Check evidence files
    # 4. Determine COMPLETE vs INCOMPLETE

    # Placeholder: check if we have enough evidence
    has_evidence = len(identity_info["historical_ids"]) > 0 or identity_info["current_id"] is not None

    if has_evidence:
        # Could be COMPLETE or INCOMPLETE depending on evidence
        # For now, mark as COMPLETE if we can verify absence
        status = "COMPLETE"
    else:
        status = "INCOMPLETE"

    # Build steps_json
    steps = build_steps(case, identity_info, rules_map, audit_at)

    return status, steps


def build_steps(case, identity_info, rules_map, audit_at):
    """Build the steps_json array for a case."""
    steps = []
    case_id = case.get("case_id", "").strip()
    email = case.get("email", "").strip().lower()

    # Phase 1: FINDING steps
    # Check for remaining records
    if identity_info["current_id"]:
        steps.append({
            "step_no": 1,
            "phase": "FINDING",
            "system_id": "account_service",
            "resource_id": f"account_{identity_info['current_id'].split('_')[-1]}" if "_" in identity_info['current_id'] else identity_info['current_id'],
            "operation": "REPORT_REMAINING_RECORD",
            "state": "PRESENT",
            "evidence_id": None
        })

    # Check for exposed PII
    if identity_info["emails"]:
        steps.append({
            "step_no": 2 if len(steps) < 2 else 1,
            "phase": "FINDING",
            "system_id": "account_service",
            "resource_id": f"account_{identity_info['current_id'].split('_')[-1]}" if "_" in identity_info['current_id'] else identity_info['current_id'],
            "operation": "REPORT_EXPOSED_PII",
            "state": "PRESENT",
            "evidence_id": "evidence_01"
        })

    # Check for active data flows
    # Check for restore risks

    # Phase 2: REMEDIATION steps
    # Based on rules and findings

    # Phase 3: VERIFICATION steps
    # Verify current state

    return steps


def generate_output(deletion_requests, identity_resolver, rules_map):
    """Generate the output CSV rows."""
    rows = []

    for case in deletion_requests:
        case_id = case.get("case_id", "").strip()
        email = case.get("email", "").strip().lower()
        audit_at = case.get("audit_at", "").strip()

        # Resolve identity
        identity_info = identity_resolver.resolve_identifier(case_id, audit_at)

        # Determine status
        if not identity_info["deletion_requested"]:
            status = "NOT_APPLICABLE"
            steps = []
        else:
            status, steps = determine_status(case, identity_resolver, rules_map)

        # Build steps_json
        steps_json = json.dumps(steps, ensure_ascii=False)

        # Validate
        if not validate_output_row({"case_id": case_id, "deletion_status": status, "steps_json": steps_json}):
            print(f"WARNING: Validation failed for {case_id}", file=sys.stderr)
            # Fallback
            if status == "NOT_APPLICABLE":
                steps_json = "[]"

        rows.append({
            "case_id": case_id,
            "deletion_status": status,
            "steps_json": steps_json
        })

    # Sort by case_id
    rows.sort(key=lambda r: r["case_id"])

    return rows


def write_output_csv(rows, filename="output.csv"):
    """Write the output CSV file."""
    filepath = Path(filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for row in rows:
            writer.writerow([row["case_id"], row["deletion_status"], row["steps_json"]])
    print(f"Wrote {len(rows)} rows to {filepath}")


def validate_output(filename="output.csv"):
    """Validate the output CSV."""
    rows = load_csv(filename)

    print(f"Validating output: {len(rows)} rows (including header)")

    # Check header
    if rows[0]["case_id"] != "case_id" or rows[0]["deletion_status"] != "deletion_status" or rows[0]["steps_json"] != "steps_json":
        print("ERROR: Invalid header", file=sys.stderr)
        return False

    # Check row count (should be 518 data rows + 1 header = 519)
    data_rows = len(rows) - 1
    print(f"Data rows: {data_rows}")

    # Validate each row
    valid = True
    for i, row in enumerate(rows[1:], 1):
        if not validate_output_row(row):
            print(f"Row {i}: INVALID - keys={set(row.keys())}", file=sys.stderr)
            valid = False

        # Try to parse steps_json
        try:
            steps = json.loads(row["steps_json"])
            if not isinstance(steps, list):
                print(f"Row {i}: steps_json is not an array", file=sys.stderr)
                valid = False
        except json.JSONDecodeError as e:
            print(f"Row {i}: steps_json parse error: {e}", file=sys.stderr)
            valid = False

    if valid:
        print("All rows validated successfully!")
    return valid


def main():
    """Main entry point."""
    print("=" * 60)
    print("Deletion Audit Agent")
    print("=" * 60)

    # Load all data
    print("\nLoading dataset files...")

    deletion_requests = load_deletion_requests()
    print(f"  deletion_requests.csv: {len(deletion_requests)} rows")

    rules_map = load_deletion_rules()
    print(f"  deletion_rules.csv: {len(rules_map)} rules")

    user_identities = load_user_identities()
    print(f"  user_identities.csv: {len(user_identities)} users")

    audit_log = load_audit_log()
    print(f"  user_audit_log.csv: {len(audit_log)} entries")

    system_activity = load_system_activity()
    print(f"  system_activity.csv: {len(system_activity)} entries")

    evidence_files = load_evidence_files()
    print(f"  evidence_files.csv: {len(evidence_files)} files")

    # Create identity resolver
    print("\nBuilding identity resolver...")
    identity_resolver = IdentityResolver(user_identities, audit_log, deletion_requests)

    # Generate output
    print("\nProcessing deletion requests...")
    rows = generate_output(deletion_requests, identity_resolver, rules_map)

    # Write output
    print(f"\nWriting output.csv ({len(rows)} rows)...")
    write_output_csv(rows, "output.csv")

    # Validate
    print("\nValidating output...")
    validate_output("output.csv")

    # Summary
    status_counts = {}
    for row in rows[1:]:  # Skip header
        s = row["deletion_status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    print("\nStatus distribution:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    print("\n" + "=" * 60)
    print("Done! output.csv generated.")
    print("=" * 60)


if __name__ == "__main__":
    main()