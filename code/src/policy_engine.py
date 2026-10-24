"""Policy engine mapping deletion rules to required treatments."""

from typing import Any, Dict, List, Optional


class PolicyEngine:
    """Applies deletion_rules.csv to resources and data categories."""

    def __init__(self, rules: List[Dict[str, str]]):
        self.rules = rules
        self.category_to_action: Dict[str, str] = {}
        self.system_to_category = {
            "account_service": "USER_PROFILE",
            "search_service": "SEARCH_INDEX_ENTRY",
            "support_platform": "SUPPORT_MESSAGE",
            "analytics_platform": "ANALYTICS_PROFILE",
            "export_service": "USER_EXPORT",
            "integration_service": "PRODUCT_TELEMETRY",
            "backup_service": "BACKUP_ARCHIVE",
            "security_service": "SECURITY_AUDIT_LOG",
            "identity_service": "ACCOUNT_TOMBSTONE",
        }
        self._build_engine()

    def _build_engine(self) -> None:
        """Index rules by data category."""
        for rule in self.rules:
            cat = rule.get("data_category", "").strip()
            act = rule.get("required_action", "").strip()
            if cat and act:
                self.category_to_action[cat] = act

    def get_required_action_for_system(self, system_id: str, is_attachment: bool = False) -> str:
        """Return the required policy action for a given system."""
        if system_id == "support_platform" and is_attachment:
            return "DELETE"  # rule_06 SUPPORT_ATTACHMENT -> DELETE

        cat = self.system_to_category.get(system_id, "USER_PROFILE")
        return self.category_to_action.get(cat, "DELETE")

    def get_remediation_operation(self, system_id: str, is_attachment: bool = False) -> str:
        """Map required action to remediation operation."""
        action = self.get_required_action_for_system(system_id, is_attachment)
        if system_id == "integration_service":
            return "DISABLE_DATA_FLOW"
        if system_id == "backup_service":
            return "BLOCK_RESTORE"

        if action == "DELETE":
            return "DELETE_RECORD"
        elif action == "REDACT":
            return "REDACT_RECORD"
        elif action == "ANONYMIZE":
            return "ANONYMIZE_RECORD"
        return "DELETE_RECORD"

    def get_verification_operation(self, system_id: str, is_attachment: bool = False) -> str:
        """Map required action to verification operation."""
        if system_id == "integration_service":
            return "VERIFY_DATA_FLOW_DISABLED"
        if system_id == "backup_service":
            return "VERIFY_RESTORE_BLOCKED"
        if system_id == "security_service":
            return "VERIFY_RECORD_PRESENT"

        action = self.get_required_action_for_system(system_id, is_attachment)
        if action == "DELETE":
            return "VERIFY_RECORD_ABSENT"
        elif action == "REDACT":
            return "VERIFY_RECORD_REDACTED"
        elif action == "ANONYMIZE":
            return "VERIFY_RECORD_ANONYMIZED"
        elif action == "RETAIN":
            return "VERIFY_RECORD_PRESENT"
        return "VERIFY_RECORD_ABSENT"

