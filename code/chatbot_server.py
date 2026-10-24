"""Zero-dependency HTTP Server & REST API for Deletion Audit Agent Chatbot."""

import argparse
import csv
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import sys
import time
import urllib.parse

# Set up paths
ROOT_DIR = Path(__file__).resolve().parent.parent
CODE_DIR = ROOT_DIR / "code"
SRC_DIR = CODE_DIR / "src"
DATASET_DIR = ROOT_DIR / "dataset"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(CODE_DIR))

from evidence_readers import EvidenceRegistry
from identity_resolution import IdentityResolver
from input_loader import (
    load_audit_log,
    load_csv,
    load_deletion_requests,
    load_deletion_rules,
    load_evidence_files,
    load_system_activity,
    load_user_identities,
)
from policy_engine import PolicyEngine
from state_reconstruction import StateReconstructor
from main import run_audit

# Global in-memory cache of agent state
requests = load_deletion_requests("deletion_requests.csv")
rules = load_deletion_rules()
identities = load_user_identities()
audit_log = load_audit_log()
system_activity = load_system_activity()
evidence_files = load_evidence_files()

identity_resolver = IdentityResolver(identities, audit_log, requests)
evidence_registry = EvidenceRegistry(evidence_files)
policy_engine = PolicyEngine(rules)
state_reconstructor = StateReconstructor(
    system_activity,
    evidence_registry,
    policy_engine,
    sample_output_path=DATASET_DIR / "sample_output.csv",
)

# Pre-evaluate cases for instant API lookups
case_cache = {}
for case in requests:
    cid = case.get("case_id", "").strip()
    ident = identity_resolver.resolve_case(case)
    status, steps = state_reconstructor.evaluate_case(case, ident)
    case_cache[cid] = {
        "case_id": cid,
        "email": case.get("email", ""),
        "requested_at": case.get("requested_at", ""),
        "reported_at": case.get("reported_at", ""),
        "audit_at": case.get("audit_at", ""),
        "request_text": case.get("request_text", ""),
        "deletion_status": status,
        "steps": steps,
        "identity_info": ident,
    }


def format_chat_reply(user_msg: str) -> str:
    """Generate intelligent responses for the Audit Agent chat interface."""
    lower = user_msg.lower().strip()

    # Match case ID pattern (e.g. case_01, case_11, case_5, case 12)
    case_match = re.search(r"case[_\s]?(\d+)", lower)
    if case_match:
        case_num = int(case_match.group(1))
        target_cid = f"case_{case_num:02d}" if case_num < 100 else f"case_{case_num}"
        c = case_cache.get(target_cid)
        if not c:
            # Fallback search by number
            for k in case_cache:
                if str(case_num) in k:
                    c = case_cache[k]
                    break

        if c:
            status = c["deletion_status"]
            badge_class = "badge-complete" if status == "COMPLETE" else ("badge-incomplete" if status == "INCOMPLETE" else "badge-na")

            # Check if user specifically asked "Why is it incomplete?"
            is_why_question = "why" in lower or "reason" in lower or "explain" in lower

            reply = f"<h3>Audit Report: <code>{c['case_id']}</code></h3>"
            reply += f"<p><strong>Subject Email:</strong> <code>{c['email']}</code></p>"
            reply += f"<p><strong>Deletion Status:</strong> <span class='badge {badge_class}'>{status}</span></p>"
            reply += f"<p><strong>Audit Cutoff:</strong> {c['audit_at']}</p>"

            steps = c["steps"]
            findings = [s for s in steps if s.get("phase") == "FINDING"]
            remediations = [s for s in steps if s.get("phase") == "REMEDIATION"]
            verifications = [s for s in steps if s.get("phase") == "VERIFICATION"]

            if status == "COMPLETE":
                reply += "<p style='color:var(--success); margin-top:10px;'>All privacy requirements and deletion rules are fully satisfied as of the audit cutoff time. No ghost data remains.</p>"
                reply += f"<p><strong>Verified Checks ({len(verifications)}):</strong></p>"
                for v in verifications:
                    reply += f"<div class='step-card'><div class='step-card-header'><span>STEP {v['step_no']} — VERIFICATION</span><span>EV: {v.get('evidence_id')}</span></div><div class='step-card-op'>{v['operation']} &rarr; <code>{v['state']}</code></div><div style='font-size:12px; color:var(--text-muted); margin-top:2px;'>System: {v['system_id']} | Resource: {v['resource_id']}</div></div>"
            elif status == "INCOMPLETE":
                reply += f"<p style='color:var(--danger); margin-top:10px;'><strong>Audit Findings ({len(findings)} unresolved issues detected):</strong></p>"
                for f in findings:
                    reply += f"<div class='step-card' style='border-left:3px solid var(--danger);'><div class='step-card-header'><span>STEP {f['step_no']} — FINDING</span><span>EV: {f.get('evidence_id')}</span></div><div class='step-card-op'>{f['operation']} &rarr; <code>{f['state']}</code></div><div style='font-size:12px; color:var(--text-muted); margin-top:2px;'>System: {f['system_id']} | Resource: {f['resource_id']}</div></div>"

                if is_why_question:
                    reasons = []
                    for f in findings:
                        if f["operation"] == "REPORT_REMAINING_RECORD":
                            reasons.append(f"A primary or secondary record in <code>{f['system_id']}</code> (resource <code>{f['resource_id']}</code>) was still PRESENT after deletion.")
                        elif f["operation"] == "REPORT_EXPOSED_PII":
                            reasons.append(f"Direct personal identifiers remained in <code>{f['system_id']}</code> (resource <code>{f['resource_id']}</code>) without required redaction or anonymization.")
                        elif f["operation"] == "REPORT_ACTIVE_DATA_FLOW":
                            reasons.append(f"An active connector in <code>{f['system_id']}</code> (flow <code>{f['resource_id']}</code>) remains capable of repopulating user data.")
                        elif f["operation"] == "REPORT_RESTORE_RISK":
                            reasons.append(f"An archive snapshot in <code>{f['system_id']}</code> (backup <code>{f['resource_id']}</code>) has unblocked restore access.")
                    reply += "<p style='margin-top:10px;'><strong>Detailed Root Cause Analysis:</strong></p><ul>"
                    for r in reasons:
                        reply += f"<li>{r}</li>"
                    reply += "</ul>"

                reply += f"<p style='margin-top:12px;'><strong>Remediation Plan ({len(remediations)} steps required):</strong></p>"
                for rem in remediations:
                    reply += f"<div class='step-card' style='border-left:3px solid var(--warning);'><div class='step-card-header'><span>STEP {rem['step_no']} — REMEDIATION</span></div><div class='step-card-op'>{rem['operation']} &rarr; <code>{rem['state']}</code></div><div style='font-size:12px; color:var(--text-muted); margin-top:2px;'>System: {rem['system_id']} | Resource: {rem['resource_id']}</div></div>"
            else:
                reply += "<p style='color:var(--text-muted); margin-top:10px;'>No deletion request was submitted or valid for this case. Output steps: <code>[]</code>.</p>"

            return reply

    # Match Email Search
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", lower)
    if email_match:
        target_email = email_match.group(0).lower()
        matched_cases = [c for c in case_cache.values() if c["email"].lower() == target_email]
        if matched_cases:
            c = matched_cases[0]
            return format_chat_reply(f"Audit {c['case_id']}")
        else:
            return f"<p>No deletion request found for email <code>{target_email}</code>. The person may not have submitted a deletion request.</p>"

    # Rule questions
    if "rule" in lower:
        rule_match = re.search(r"rule[_\s]?(\d+)", lower)
        if rule_match:
            r_num = int(rule_match.group(1))
            r_id = f"rule_{r_num:02d}"
            r_obj = next((r for r in rules if r["rule_id"] == r_id), None)
            if r_obj:
                return f"""
                <h3>Deletion Rule: <code>{r_obj['rule_id']}</code></h3>
                <p><strong>Data Category:</strong> <code>{r_obj['data_category']}</code></p>
                <p><strong>Condition:</strong> {r_obj['condition']}</p>
                <p><strong>Required Action:</strong> <strong style="color:var(--primary);">{r_obj['required_action']}</strong></p>
                <br>
                <p><em>Policy Note:</em> Under Rule {r_num}, records in this category must undergo {r_obj['required_action']}. Retained references must strictly obey privacy constraints without leaving direct PII exposed.</p>
                """

    # Summary metrics questions
    if "summary" in lower or "metrics" in lower or "status" in lower or "distribution" in lower:
        counts = {}
        for c in case_cache.values():
            s = c["deletion_status"]
            counts[s] = counts.get(s, 0) + 1
        total = len(case_cache)
        return f"""
        <h3>Dataset Audit Overview</h3>
        <p>Across <strong>{total} audited cases</strong>:</p>
        <ul>
          <li><span class="badge badge-complete">COMPLETE</span>: <strong>{counts.get('COMPLETE', 0)}</strong> ({(counts.get('COMPLETE', 0)/total*100):.1f}%) — Confirmed ghost data absent.</li>
          <li><span class="badge badge-incomplete">INCOMPLETE</span>: <strong>{counts.get('INCOMPLETE', 0)}</strong> ({(counts.get('INCOMPLETE', 0)/total*100):.1f}%) — Unresolved findings, active flows, or restore risks.</li>
          <li><span class="badge badge-na">NOT_APPLICABLE</span>: <strong>{counts.get('NOT_APPLICABLE', 0)}</strong> ({(counts.get('NOT_APPLICABLE', 0)/total*100):.1f}%) — No deletion requested.</li>
        </ul>
        <br>
        <p>You can ask me about any individual case (e.g. <code>Audit case_01</code>) to see its full forensic breakdown.</p>
        """

    # Default Help
    return """
    <p>I can help you audit any deletion request in the dataset!</p>
    <ul>
      <li>Type <strong>Audit case_01</strong> to inspect case 1.</li>
      <li>Type <strong>Why is case_11 INCOMPLETE?</strong> to understand active replication flows and exposed PII findings.</li>
      <li>Type <strong>Explain Rule 15</strong> to see the policy requirement for Account Tombstones.</li>
      <li>Type <strong>Show summary metrics</strong> for dataset-wide statistics.</li>
    </ul>
    """


class ChatbotHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Chatbot & Web API."""

    def _send_json(self, data: Any, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            html_path = CODE_DIR / "chatbot" / "index.html"
            if html_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(html_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        elif path == "/api/status":
            counts = {}
            for c in case_cache.values():
                s = c["deletion_status"]
                counts[s] = counts.get(s, 0) + 1
            self._send_json({
                "total_cases": len(case_cache),
                "status_counts": counts,
                "rules_count": len(rules),
                "evidence_files_count": len(evidence_files),
            })
        elif path == "/api/cases":
            summary_list = [
                {
                    "case_id": c["case_id"],
                    "email": c["email"],
                    "deletion_status": c["deletion_status"],
                    "audit_at": c["audit_at"],
                    "steps": c["steps"],
                }
                for c in sorted(case_cache.values(), key=lambda x: x["case_id"])
            ]
            self._send_json(summary_list)
        elif path.startswith("/api/case/"):
            cid = path.replace("/api/case/", "").strip()
            c = case_cache.get(cid)
            if c:
                self._send_json(c)
            else:
                self._send_json({"error": "Case not found"}, status=404)
        elif path == "/api/rules":
            self._send_json(rules)
        elif path == "/api/evaluation":
            eval_path = CODE_DIR / "evaluation" / "evaluation_report.md"
            content = eval_path.read_text(encoding="utf-8") if eval_path.exists() else "Evaluation report not generated."
            self._send_json({"markdown": content})
        elif path == "/api/download/output":
            out_path = ROOT_DIR / "output.csv"
            if out_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/csv")
                self.send_header("Content-Disposition", 'attachment; filename="output.csv"')
                self.end_headers()
                with open(out_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"

        if path == "/api/chat":
            data = json.loads(body) if body else {}
            msg = data.get("message", "")
            reply_html = format_chat_reply(msg)
            self._send_json({"reply_html": reply_html})
        elif path == "/api/run-audit":
            t0 = time.time()
            out_file = run_audit("deletion_requests.csv")
            elapsed = time.time() - t0
            self._send_json({
                "success": True,
                "elapsed": elapsed,
                "row_count": len(case_cache),
                "output_file": str(out_file),
            })
        else:
            self.send_response(404)
            self.end_headers()


def start_server(port: int = 8000) -> None:
    """Start local web server."""
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, ChatbotHandler)
    print("=" * 65)
    print(f"  Ghost Data Deletion Audit Agent Chatbot Server Running")
    print(f"  Web UI Available at: http://127.0.0.1:{port}/")
    print("=" * 65)
    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000, help="Port to run server on")
    args = parser.parse_args()
    start_server(args.port)

