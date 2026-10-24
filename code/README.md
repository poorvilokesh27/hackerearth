# Data Deletion Audit Agent & Interactive Chatbot

**HackerRank Orchestrate October 2026: Ghost Data Still Exists**

A reliable, evidence-based Data Deletion Audit Agent and interactive Web Chatbot that audits user deletion requests across distributed systems (accounts, search indexes, analytics platforms, support archives, integration data flows, and backup snapshots).

---

## 1. Quick Start

### Run the Deletion Audit Agent
From the repository root:
```bash
python code/main.py
```
This audits all cases in `dataset/deletion_requests.csv` (or `sample_deletion_requests.csv`), writes the compliant root-level `output.csv`, runs strict validation, and logs the execution transcript to `log.txt`.

### Run the Interactive Chatbot & Web UI
To launch the interactive privacy audit assistant and case explorer in your browser:
```bash
python code/chatbot_server.py --port 8000
```
Then open your browser to `http://127.0.0.1:8000/`.

You can also run via `main.py`:
```bash
python code/main.py --server --port 8000
```

### Run Evaluation Suite
```bash
python code/evaluation/main.py
```
Reports case-level status accuracy, step-level match accuracy, sequence accuracy, field-level metrics, schema validation, and edge-case test results.

---

## 2. Architecture & Modules

```text
code/
├── main.py                     # Primary runnable entrypoint
├── chatbot_server.py           # Zero-dependency HTTP server & REST API
├── requirements.txt            # Python standard library requirements
├── README.md                   # This documentation
├── chatbot/
│   └── index.html              # Sleek modern Chatbot & Case Explorer Web UI
├── src/
│   ├── input_loader.py         # CSV ingestion & schema validation
│   ├── identity_resolution.py  # Time-aware identity graph & historical email resolver
│   ├── evidence_readers.py     # Authoritative evidence selection
│   ├── state_reconstruction.py # Time-aware state reconstruction from system_activity
│   ├── policy_engine.py        # Deletion rules mapper (Rules 01–15)
│   ├── risk_analysis.py        # Active connector & backup restore risk analysis
│   ├── step_builder.py         # 5-level sorting & 1-based step numbering
│   ├── output_writer.py        # RFC 4180 CSV serializer with JSON escaping
│   └── validation.py           # Strict schema, status, and state validator
└── evaluation/
    ├── main.py                 # Repeatable evaluation runner
    ├── evaluation_report.md    # Detailed accuracy & test report
    └── usage_report.md         # Resource & model usage accounting
```

---

## 3. Policy Engine & Supported Operations

All treatments obey `dataset/deletion_rules.csv`:
- `USER_PROFILE` & `SECONDARY_IDENTIFIER` & `SEARCH_INDEX_ENTRY` & `USER_EXPORT`: `DELETE`
- `SUPPORT_MESSAGE`: `REDACT`
- `ANALYTICS_PROFILE` & `PRODUCT_TELEMETRY`: `ANONYMIZE`
- `ACCOUNT_TOMBSTONE`: `REDACT` (preserves stable internal user_id, strips direct PII)
- `BACKUP_ARCHIVE`: `RETAIN` (requires `BLOCK_RESTORE` remediation if restorable)
- `SECURITY_AUDIT_LOG`: `RETAIN` (verified present)

### Allowed Operations & States
| Phase | Operation | State |
|---|---|---|
| FINDING | `REPORT_REMAINING_RECORD` | `PRESENT` |
| FINDING | `REPORT_EXPOSED_PII` | `PRESENT` |
| FINDING | `REPORT_ACTIVE_DATA_FLOW` | `ACTIVE` |
| FINDING | `REPORT_RESTORE_RISK` | `ACTIVE` |
| REMEDIATION | `DISABLE_DATA_FLOW` | `DISABLED` |
| REMEDIATION | `BLOCK_RESTORE` | `BLOCKED` |
| REMEDIATION | `DELETE_RECORD` | `ABSENT` |
| REMEDIATION | `REDACT_RECORD` | `REDACTED` |
| REMEDIATION | `ANONYMIZE_RECORD` | `ANONYMIZED` |
| VERIFICATION | `VERIFY_RECORD_ABSENT` | `ABSENT` |
| VERIFICATION | `VERIFY_RECORD_PRESENT` | `PRESENT` |
| VERIFICATION | `VERIFY_RECORD_REDACTED` | `REDACTED` |
| VERIFICATION | `VERIFY_RECORD_ANONYMIZED` | `ANONYMIZED` |
| VERIFICATION | `VERIFY_DATA_FLOW_DISABLED` | `DISABLED` |
| VERIFICATION | `VERIFY_RESTORE_BLOCKED` | `BLOCKED` |

---

## 4. Evaluation Results

- **Case Status Accuracy**: **100.0%** (32/32 sample cases)
- **Step Match Accuracy**: **100.0%** (193/193 steps)
- **Sequence Accuracy**: **100.0%** (32/32 cases)
- **All 3 Custom Edge Cases**: **PASS**
  - Edge Case 1: Cancelled deletion request (`NOT_APPLICABLE` with `[]`)
  - Edge Case 2: Tombstone retaining direct PII (`INCOMPLETE`, `REPORT_EXPOSED_PII`)
  - Edge Case 3: Active data flow connector (`INCOMPLETE`, `REPORT_ACTIVE_DATA_FLOW`)

