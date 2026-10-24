"""Identity resolution engine for deletion audit agent."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set


class IdentityResolver:
    """
    Evidence-based identity resolution graph.
    Resolves current and historical identifiers valid at or before audit_at.
    """

    def __init__(
        self,
        user_identities: List[Dict[str, str]],
        audit_log: List[Dict[str, str]],
        deletion_requests: Optional[List[Dict[str, str]]] = None,
    ):
        self.user_identities = user_identities
        self.audit_log = audit_log
        self.deletion_requests = deletion_requests or []

        # Index user identities by user_id and email
        self.users_by_id: Dict[str, Dict[str, str]] = {}
        self.users_by_email: Dict[str, Dict[str, str]] = {}
        self.email_to_userid: Dict[str, str] = {}
        self.phone_to_userid: Dict[str, str] = {}
        self.hash_to_userid: Dict[str, str] = {}

        # Audit history index: user_id -> list of audit events
        self.user_audit_history: Dict[str, List[Dict[str, str]]] = {}
        self.historical_email_to_userid: Dict[str, List[Dict[str, str]]] = {}

        self._build_indexes()

    def _build_indexes(self) -> None:
        """Build identity resolution graphs and lookup structures."""
        for u in self.user_identities:
            uid = u.get("user_id", "").strip()
            email = u.get("email", "").strip().lower()
            phone = u.get("phone", "").strip()
            e_hash = u.get("email_hash", "").strip().lower()

            if uid:
                self.users_by_id[uid] = u
            if email:
                self.users_by_email[email] = u
                self.email_to_userid[email] = uid
            if phone:
                self.phone_to_userid[phone] = uid
            if e_hash:
                self.hash_to_userid[e_hash] = uid

        for entry in self.audit_log:
            uid = entry.get("user_id", "").strip()
            field = entry.get("field_name", "").strip()
            old_val = entry.get("old_value", "").strip()
            new_val = entry.get("new_value", "").strip()
            ev_time = entry.get("event_time", "").strip()

            if uid not in self.user_audit_history:
                self.user_audit_history[uid] = []
            self.user_audit_history[uid].append(entry)

            if field == "email":
                if old_val:
                    norm_old = old_val.lower()
                    if norm_old not in self.historical_email_to_userid:
                        self.historical_email_to_userid[norm_old] = []
                    self.historical_email_to_userid[norm_old].append({
                        "user_id": uid,
                        "event_time": ev_time,
                        "type": "old_email",
                    })
                if new_val:
                    norm_new = new_val.lower()
                    if norm_new not in self.historical_email_to_userid:
                        self.historical_email_to_userid[norm_new] = []
                    self.historical_email_to_userid[norm_new].append({
                        "user_id": uid,
                        "event_time": ev_time,
                        "type": "new_email",
                    })

        # Sort audit histories chronologically
        for uid in self.user_audit_history:
            self.user_audit_history[uid].sort(key=lambda x: x.get("event_time", ""))

    def resolve_case(self, case: Dict[str, str]) -> Dict[str, Any]:
        """
        Resolve person identities and verify deletion request validity at audit_at.
        """
        case_id = case.get("case_id", "").strip()
        email = case.get("email", "").strip().lower()
        audit_at = case.get("audit_at", "").strip()
        request_text = case.get("request_text", "").strip()

        # Check if deletion was actually requested
        # Explicit NOT_APPLICABLE conditions:
        # 1. request_text explicitly negates deletion or is an inquiry without request
        # 2. deletion_requested flag is explicitly "no" or "false"
        flag = case.get("deletion_requested", "").strip().lower()
        if flag in {"no", "false"}:
            return {
                "case_id": case_id,
                "deletion_requested": False,
                "reason": "Explicit deletion_requested=False flag",
            }

        # Analyze request text for intent
        lower_text = request_text.lower()
        if "do not delete" in lower_text or "cancel deletion" in lower_text or "retain my account" in lower_text:
            return {
                "case_id": case_id,
                "deletion_requested": False,
                "reason": "Request text cancels or opposes deletion",
            }

        deletion_requested = True

        # Match user ID:
        # 1. Direct match in current user identities
        user_id = self.email_to_userid.get(email)

        # 2. Historical audit log lookup valid at or before audit_at
        if not user_id and email in self.historical_email_to_userid:
            valid_hist = [
                h for h in self.historical_email_to_userid[email]
                if not audit_at or h["event_time"] <= audit_at
            ]
            if valid_hist:
                user_id = valid_hist[-1]["user_id"]

        # Collect all associated identifiers
        user_record = self.users_by_id.get(user_id) if user_id else None
        emails: Set[str] = {email}
        phones: Set[str] = set()
        hashes: Set[str] = set()

        if user_record:
            if user_record.get("email"):
                emails.add(user_record["email"].strip().lower())
            if user_record.get("phone"):
                phones.add(user_record["phone"].strip())
            if user_record.get("email_hash"):
                hashes.add(user_record["email_hash"].strip().lower())

        # Check historical audit log for old values
        if user_id and user_id in self.user_audit_history:
            for ev in self.user_audit_history[user_id]:
                if audit_at and ev.get("event_time", "") > audit_at:
                    continue
                field = ev.get("field_name", "")
                old_v = ev.get("old_value", "")
                new_v = ev.get("new_value", "")
                if field == "email":
                    if old_v:
                        emails.add(old_v.strip().lower())
                    if new_v:
                        emails.add(new_v.strip().lower())
                elif field == "phone":
                    if old_v:
                        phones.add(old_v.strip())
                    if new_v:
                        phones.add(new_v.strip())
                elif field == "email_hash":
                    if old_v:
                        hashes.add(old_v.strip().lower())
                    if new_v:
                        hashes.add(new_v.strip().lower())

        return {
            "case_id": case_id,
            "user_id": user_id,
            "deletion_requested": deletion_requested,
            "primary_email": email,
            "all_emails": sorted(list(emails)),
            "all_phones": sorted(list(phones)),
            "all_hashes": sorted(list(hashes)),
            "user_record": user_record,
        }
