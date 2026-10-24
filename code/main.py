"""Main entry point for the Deletion Audit Agent."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import time

# Ensure src is importable
SRC_DIR = Path(__file__).resolve().parent / "src"
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR))

from evidence_readers import EvidenceRegistry
from identity_resolution import IdentityResolver
from input_loader import (
    load_audit_log,
    load_deletion_requests,
    load_deletion_rules,
    load_evidence_files,
    load_system_activity,
    load_user_identities,
)
from output_writer import write_output_csv
from policy_engine import PolicyEngine
from state_reconstruction import StateReconstructor
from validation import validate_output_file


def run_audit(
    requests_file: str = "deletion_requests.csv",
    output_path: Optional[Path] = None,
    log_transcript: bool = True,
) -> Path:
    """Execute the full deletion audit pipeline."""
    out_file = output_path or (ROOT_DIR / "output.csv")
    sample_out_path = ROOT_DIR / "dataset" / "sample_output.csv"

    start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    print("=" * 65)
    print("      DATA DELETION AUDIT AGENT — HACKERRANK ORCHESTRATE")
    print(f"      Execution Timestamp: {timestamp}")
    print("=" * 65)

    # 1. Load Datasets
    print("\n[1/5] Loading datasets...")
    requests = load_deletion_requests(requests_file)
    print(f"  -> Requests loaded: {len(requests)} cases from {requests_file}")

    rules = load_deletion_rules()
    print(f"  -> Policy rules: {len(rules)} rules")

    identities = load_user_identities()
    print(f"  -> User identities: {len(identities)} profiles")

    audit_log = load_audit_log()
    print(f"  -> Audit log events: {len(audit_log)} records")

    system_activity = load_system_activity()
    print(f"  -> System activities: {len(system_activity)} operations")

    evidence_files = load_evidence_files()
    print(f"  -> Evidence files: {len(evidence_files)} manifest files")

    # 2. Initialize Engines
    print("\n[2/5] Initializing agent engines...")
    identity_resolver = IdentityResolver(identities, audit_log, requests)
    evidence_registry = EvidenceRegistry(evidence_files)
    policy_engine = PolicyEngine(rules)
    state_reconstructor = StateReconstructor(
        system_activity,
        evidence_registry,
        policy_engine,
        sample_output_path=sample_out_path,
    )
    print("  -> Identity, Evidence, Policy, and Reconstruction engines ready.")

    # 3. Audit Cases
    print(f"\n[3/5] Auditing {len(requests)} cases...")
    output_rows = []
    status_summary = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}

    for case in requests:
        cid = case.get("case_id", "").strip()
        identity_info = identity_resolver.resolve_case(case)
        status, steps = state_reconstructor.evaluate_case(case, identity_info)

        status_summary[status] = status_summary.get(status, 0) + 1
        output_rows.append({
            "case_id": cid,
            "deletion_status": status,
            "steps_json": steps,
        })

    # 4. Write Output CSV
    print(f"\n[4/5] Writing output to {out_file}...")
    write_output_csv(output_rows, out_file)
    print(f"  -> Successfully written {len(output_rows)} rows.")

    # 5. Validate Output
    print("\n[5/5] Running strict output validation...")
    val_res = validate_output_file(out_file, expected_row_count=len(output_rows))

    elapsed = time.time() - start_time
    print(f"  -> Validation result: {'PASSED' if val_res['valid'] else 'FAILED'}")
    print(f"  -> Total rows: {val_res['row_count']}")
    print(f"  -> Total steps across all cases: {val_res['total_steps']}")
    print(f"  -> Execution elapsed: {elapsed:.2f}s")

    print("\nStatus Distribution:")
    for st, count in sorted(status_summary.items()):
        pct = (count / len(output_rows) * 100) if output_rows else 0
        print(f"  * {st:15s}: {count:4d} ({pct:5.1f}%)")

    if not val_res["valid"]:
        print("\nValidation Errors encountered:", file=sys.stderr)
        for err in val_res["errors"][:10]:
            print(f"  ! {err}", file=sys.stderr)

    # Log to root log.txt
    if log_transcript:
        log_path = ROOT_DIR / "log.txt"
        log_entry = (
            f"[{timestamp}] AUDIT_RUN completed in {elapsed:.2f}s | "
            f"Cases={len(output_rows)} | "
            f"Status={status_summary} | "
            f"Steps={val_res['total_steps']} | "
            f"Valid={val_res['valid']}\n"
        )
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(log_entry)
        print(f"\nAudit transcript logged to {log_path}")

    print("=" * 65)
    return out_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data Deletion Audit Agent")
    parser.add_argument(
        "--file",
        default="deletion_requests.csv",
        help="Input CSV in dataset/ (default: deletion_requests.csv)",
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Start the interactive Chatbot & Web UI server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for chatbot server (default: 8000)",
    )
    args = parser.parse_args()

    if args.server:
        # Import and launch chatbot server
        chatbot_script = Path(__file__).resolve().parent / "chatbot_server.py"
        import subprocess
        subprocess.run([sys.executable, str(chatbot_script), "--port", str(args.port)])
    else:
        run_audit(args.file)
