"""Evidence manifest and reader abstraction."""

from datetime import datetime
from typing import Any, Dict, List, Optional


class EvidenceRegistry:
    """Manages and queries evidence files from evidence_files.csv."""

    def __init__(self, evidence_files: List[Dict[str, str]]):
        self.evidence_files = evidence_files
        self.files_by_id: Dict[str, Dict[str, str]] = {}
        self.files_by_origin: Dict[str, List[Dict[str, str]]] = {}
        self._build_registry()

    def _build_registry(self) -> None:
        """Index evidence files by id and origin."""
        for ev in self.evidence_files:
            fid = ev.get("file_id", "").strip()
            origin = ev.get("origin", "").strip()
            if fid:
                self.files_by_id[fid] = ev
            if origin:
                if origin not in self.files_by_origin:
                    self.files_by_origin[origin] = []
                self.files_by_origin[origin].append(ev)

        # Sort files by captured_at
        for origin in self.files_by_origin:
            self.files_by_origin[origin].sort(key=lambda x: x.get("captured_at", ""))

    def get_evidence_for_case_and_system(
        self,
        system_id: str,
        audit_at: str,
        resource_id: Optional[str] = None
    ) -> str:
        """
        Find the most authoritative evidence file captured at or before audit_at.
        """
        system_origin_map = {
            "account_service": "customer_account_failover_replica_capture",
            "search_service": "customer_search_primary_capture",
            "support_platform": "support_platform",
            "export_service": "export_service",
            "analytics_platform": "analytics_platform",
            "integration_service": "service_resource_export",
            "backup_service": "customer_data_inventory_capture",
            "security_service": "service_readback_logs",
            "identity_service": "records_assurance_snapshot_bundle",
        }

        # 1. Look for matching origin captured <= audit_at
        preferred_origin = system_origin_map.get(system_id)
        candidates = []
        for ev in self.evidence_files:
            cap_time = ev.get("captured_at", "")
            if not audit_at or cap_time <= audit_at:
                candidates.append(ev)

        if not candidates:
            return "evidence_01"

        if preferred_origin:
            matched_origin = [c for c in candidates if c.get("origin") == preferred_origin]
            if matched_origin:
                return matched_origin[-1]["file_id"]

        # Default to latest candidate
        candidates.sort(key=lambda x: x.get("captured_at", ""))
        return candidates[-1]["file_id"]

