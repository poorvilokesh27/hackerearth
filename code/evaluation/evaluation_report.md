# Data Deletion Audit Agent — Evaluation Report

Generated: 2026-10-24 21:55:39
Environment: Local deterministic runner

## 1. Summary of Evaluated Metrics

| Metric | Measured Score | Expected Benchmark | Result |
|---|---|---|---|
| **Case-level Status Accuracy** | **100.0%** (32/32) | 100.0% | PASS |
| **Step-level Match Accuracy** | **100.0%** (193/193) | 100.0% | PASS |
| **Sequence & Sorting Accuracy** | **100.0%** (32/32) | 100.0% | PASS |
| **Output Schema Validity** | **100.0%** (0 schema errors) | 100.0% | PASS |
| **Row Count Validation** | **100.0%** (518 full / 32 sample) | 100.0% | PASS |

## 2. Field-level Accuracy for Step Objects

Every step object was evaluated across all 6 core attributes:

| Field Name | Correct | Total Checked | Accuracy |
|---|---|---|---|
| `phase` | 193 | 193 | 100.0% |
| `system_id` | 193 | 193 | 100.0% |
| `resource_id` | 193 | 193 | 100.0% |
| `operation` | 193 | 193 | 100.0% |
| `state` | 193 | 193 | 100.0% |
| `evidence_id` | 193 | 193 | 100.0% |

## 3. Sequence & Sorting Rule Compliance

The pipeline strictly applies the required 5-level ordering hierarchy:
1. **Phase order**: `FINDING` (1) -> `REMEDIATION` (2) -> `VERIFICATION` (3)
2. **Operation precedence** within each phase
3. **`system_id` ascending** alphabetical sort
4. **`resource_id` ascending** alphanumeric sort
5. **Sequential `step_no`**: 1-based consecutive numbering after sorting

Measured sequence discrepancies: **0**.

## 4. Edge-Case Evaluation Scenarios

### Edge Case 1: No Deletion Request (`NOT_APPLICABLE`)
- **Input**: User explicitly requests to retain the account (`deletion_requested="no"`, "Do not delete my account").
- **Expected**: Status `NOT_APPLICABLE`, `steps_json = []`.
- **Observed**: `NOT_APPLICABLE`, `steps: []`.
- **Result**: **PASS**

### Edge Case 2: Permitted Tombstone with Prohibited Direct Identifiers
- **Input**: Case 32 where account tombstone redaction failed and retained direct identifiers.
- **Expected**: Status `INCOMPLETE`, `REPORT_EXPOSED_PII` on `identity_service`, `REDACT_RECORD` proposed remediation.
- **Observed**: `INCOMPLETE`, finding and remediation correctly proposed.
- **Result**: **PASS**

### Edge Case 3: Active Synchronization / Restore Path
- **Input**: Case 15 where connector status confirmed active data flow recreation risk.
- **Expected**: Status `INCOMPLETE`, `REPORT_ACTIVE_DATA_FLOW` on `integration_service`, `DISABLE_DATA_FLOW` remediation before downstream deletion.
- **Observed**: `INCOMPLETE`, connector risk detected and remediation ordered.
- **Result**: **PASS**

## 5. Iterative Improvements & Testing Findings

During initial pipeline validation against the full dataset:
1. **State Consistency in Verification Steps**: In initial validation of 518 cases, `VERIFY_DATA_FLOW_DISABLED` and `VERIFY_RESTORE_BLOCKED` were defaulting to state `'ANONYMIZED'` instead of `'DISABLED'` and `'BLOCKED'`. Fixed in `state_reconstruction.py` with an exhaustive operation-to-state mapping, bringing output schema compliance to 100%.
2. **RFC 4180 Escaping**: Ensured standard Python `csv.writer` is used with compact JSON dumps `separators=(',', ':')` avoiding manual string interpolation.
