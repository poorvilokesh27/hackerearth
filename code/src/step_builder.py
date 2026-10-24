"""Step builder with exact phase, operation, and resource sorting."""

from typing import Any, Dict, List

PHASE_ORDER: Dict[str, int] = {
    "FINDING": 1,
    "REMEDIATION": 2,
    "VERIFICATION": 3,
}

OPERATION_ORDER: Dict[str, int] = {
    # FINDING
    "REPORT_REMAINING_RECORD": 1,
    "REPORT_EXPOSED_PII": 2,
    "REPORT_ACTIVE_DATA_FLOW": 3,
    "REPORT_RESTORE_RISK": 4,
    # REMEDIATION
    "DISABLE_DATA_FLOW": 1,
    "BLOCK_RESTORE": 2,
    "DELETE_RECORD": 3,
    "REDACT_RECORD": 4,
    "ANONYMIZE_RECORD": 5,
    # VERIFICATION
    "VERIFY_RECORD_ABSENT": 1,
    "VERIFY_RECORD_PRESENT": 2,
    "VERIFY_RECORD_REDACTED": 3,
    "VERIFY_RECORD_ANONYMIZED": 4,
    "VERIFY_DATA_FLOW_DISABLED": 5,
    "VERIFY_RESTORE_BLOCKED": 6,
}


def sort_and_number_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort steps strictly according to challenge ordering rules:
    1. Phase order (FINDING -> REMEDIATION -> VERIFICATION)
    2. Operation order within phase
    3. system_id ascending
    4. resource_id ascending
    5. Consecutive 1-based step_no assignment
    """
    sorted_steps = sorted(
        steps,
        key=lambda s: (
            PHASE_ORDER.get(s["phase"], 99),
            OPERATION_ORDER.get(s["operation"], 99),
            s["system_id"],
            s["resource_id"],
        ),
    )

    final_steps: List[Dict[str, Any]] = []
    for idx, s in enumerate(sorted_steps, 1):
        step_dict = {
            "step_no": idx,
            "phase": s["phase"],
            "system_id": s["system_id"],
            "resource_id": s["resource_id"],
            "operation": s["operation"],
            "state": s["state"],
            "evidence_id": s.get("evidence_id", ""),
        }
        final_steps.append(step_dict)

    return final_steps

