"""Data flow and restore risk analysis."""

from typing import Any, Dict, List, Optional


class RiskAnalyzer:
    """Analyzes active replication, data flows, and restore risks."""

    def __init__(self, system_activities: List[Dict[str, str]]):
        self.activities = system_activities

    def analyze_risks_for_case(
        self,
        case_id: str,
        audit_at: str,
        case_activities: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Identify active data flows and restore risks that could recreate user data.
        """
        risks = []

        for act in case_activities:
            ev_time = act.get("event_time", "")
            if audit_at and ev_time > audit_at:
                continue

            ev_type = act.get("event_type", "")
            res_id = act.get("resource_id", "")
            details = act.get("details", "")

            # Active data flow
            if ev_type == "CHECK_DATA_FLOW" and ("remains enabled" in details or act.get("reported_result") == "SUCCESS"):
                risks.append({
                    "type": "ACTIVE_DATA_FLOW",
                    "system_id": "integration_service",
                    "resource_id": res_id,
                    "operation": "REPORT_ACTIVE_DATA_FLOW",
                    "state": "ACTIVE",
                    "remediation": "DISABLE_DATA_FLOW",
                    "verification": "VERIFY_DATA_FLOW_DISABLED",
                    "activity_id": act.get("activity_id", ""),
                })

            # Restore risk
            elif ev_type == "CHECK_RESTORE_ACCESS" and ("can still be restored" in details or act.get("reported_result") == "SUCCESS"):
                risks.append({
                    "type": "RESTORE_RISK",
                    "system_id": "backup_service",
                    "resource_id": res_id,
                    "operation": "REPORT_RESTORE_RISK",
                    "state": "ACTIVE",
                    "remediation": "BLOCK_RESTORE",
                    "verification": "VERIFY_RESTORE_BLOCKED",
                    "activity_id": act.get("activity_id", ""),
                })

        return risks

