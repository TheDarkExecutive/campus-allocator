from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import Decision, AllocationResult, Room


class ReportPublisher:
    """
    Handles file output:
    - results/<week>/results.json
    - results/<week>/flags.md
    - results/<week>/summary.txt
    - reports/<week>/<club>.md
    - HTML export
    """

    def __init__(self, results_base: str = "results", reports_base: str = "reports") -> None:
        self.results_base = Path(results_base)
        self.reports_base = Path(reports_base)

    def write_results_json(self, week_str: str, allocation_result: AllocationResult) -> Path:
        out_dir = self.results_base / week_str
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / "results.json"

        data = {
            "week": week_str,
            "timestamp": datetime.utcnow().isoformat(),
            "summary_counts": {
                "total": len(allocation_result.decisions),
                "approved": sum(1 for d in allocation_result.decisions if d.final_status == "Approved"),
                "moved": sum(1 for d in allocation_result.decisions if d.final_status == "Moved"),
                "rejected": sum(1 for d in allocation_result.decisions if d.final_status == "Rejected"),
                "deferred": sum(1 for d in allocation_result.decisions if d.final_status == "Deferred"),
                "waitlisted": sum(1 for d in allocation_result.decisions if d.final_status == "Waitlisted"),
            },
            "decisions": [d.to_dict() for d in allocation_result.decisions],
            "overrides": [
                {
                    "timestamp": o.timestamp,
                    "request_id": o.request_id,
                    "admin_action": o.admin_action,
                    "original_decision": o.original_decision,
                    "new_decision": o.new_decision,
                    "notes": o.notes,
                }
                for o in allocation_result.overrides
            ],
            "flags": allocation_result.flags,
        }

        with open(file_path, mode="w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return file_path

    def write_summary_txt(self, week_str: str, allocation_result: AllocationResult) -> Path:
        out_dir = self.results_base / week_str
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / "summary.txt"

        app_count = sum(1 for d in allocation_result.decisions if d.final_status == "Approved")
        mov_count = sum(1 for d in allocation_result.decisions if d.final_status == "Moved")
        rej_count = sum(1 for d in allocation_result.decisions if d.final_status == "Rejected")
        def_count = sum(1 for d in allocation_result.decisions if d.final_status == "Deferred")
        wtl_count = sum(1 for d in allocation_result.decisions if d.final_status == "Waitlisted")
        total = len(allocation_result.decisions)

        lines = [
            "=" * 72,
            f"CAMPUS ALLOCATION SUMMARY — WEEK {week_str}",
            "=" * 72,
            f"Run Timestamp : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Total Requests: {total}",
            f"Approved      : {app_count} ({app_count/max(1,total)*100:.1f}%)",
            f"Moved         : {mov_count} ({mov_count/max(1,total)*100:.1f}%)",
            f"Waitlisted    : {wtl_count} ({wtl_count/max(1,total)*100:.1f}%)",
            f"Rejected      : {rej_count} ({rej_count/max(1,total)*100:.1f}%)",
            f"Deferred      : {def_count} ({def_count/max(1,total)*100:.1f}%)",
            "-" * 72,
            "ALLOCATION DECISIONS:",
            "-" * 72,
        ]

        for d in allocation_result.decisions:
            st = d.final_status
            room_str = f"Room {d.assigned_room}" if d.assigned_room else "None"
            hour_str = f"Hour {d.assigned_hour}:00" if d.assigned_hour is not None else "N/A"
            lines.append(f"[{st:10}] {d.club:24} -> {room_str:12} on {d.assigned_date or 'N/A'} {hour_str}")
            for trace_line in d.rule_trace:
                lines.append(f"             - {trace_line}")
            lines.append("")

        if allocation_result.overrides:
            lines.append("-" * 72)
            lines.append("ADMIN EXCEPTION OVERRIDES:")
            lines.append("-" * 72)
            for ov in allocation_result.overrides:
                lines.append(f"[{ov.timestamp}] Req {ov.request_id}: Action '{ov.admin_action}' - {ov.notes}")
            lines.append("")

        lines.append("=" * 72)
        with open(file_path, mode="w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return file_path

    def write_club_reports(self, week_str: str, allocation_result: AllocationResult) -> List[Path]:
        out_dir = self.reports_base / week_str
        out_dir.mkdir(parents=True, exist_ok=True)
        created_paths: List[Path] = []

        for d in allocation_result.decisions:
            safe_club_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in d.club.lower())
            file_path = out_dir / f"{safe_club_name}.md"

            status_badge = "✅ APPROVED" if d.final_status in ("Approved", "Moved") else ("⏳ DEFERRED" if d.final_status == "Deferred" else "❌ REJECTED")

            md_lines = [
                f"# Campus Room Allocation Notice",
                f"**Club / Organization**: {d.club}  ",
                f"**Allocation Week**: {week_str}  ",
                f"**Notice Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
                "",
                "---",
                "",
                f"## Final Status: {status_badge}",
                "",
                f"- **Request ID**: `{d.request_id}`",
                f"- **Assigned Room**: **{d.assigned_room or 'N/A'}**",
                f"- **Assigned Date**: {d.assigned_date or 'N/A'}",
                f"- **Assigned Time Slot**: {f'{d.assigned_hour}:00 - {d.assigned_hour+2}:00' if d.assigned_hour else 'N/A'}",
                f"- **Decision Engine**: `{d.decided_by}`",
                "",
                "### Decision Explanation (--why trace)",
                "```text",
                d.why,
                "```",
                "",
                "### Detailed Verification Checks",
            ]

            for t in d.rule_trace:
                md_lines.append(f"- {t}")

            md_lines.extend([
                "",
                "---",
                "",
                "> **Notice**: This decision was generated deterministically on the faculty administration laptop.",
                "> No internet or login required. Contact facilities administration for physical keycard access.",
            ])

            with open(file_path, mode="w", encoding="utf-8") as f:
                f.write("\n".join(md_lines))

            created_paths.append(file_path)

        return created_paths

    def export_as_html(self, week_str: str, allocation_result: AllocationResult) -> Path:
        out_dir = self.results_base / week_str
        out_dir.mkdir(parents=True, exist_ok=True)
        html_path = out_dir / "report.html"

        rows = []
        for d in allocation_result.decisions:
            badge_color = "#16a34a" if d.final_status == "Approved" else ("#eab308" if d.final_status == "Moved" else ("#64748b" if d.final_status == "Deferred" else "#dc2626"))
            rows.append(
                f"<tr>"
                f"<td><strong>{d.club}</strong><br><small>{d.request_id}</small></td>"
                f"<td><span style='background:{badge_color}; color:#fff; padding:3px 8px; border-radius:4px; font-weight:bold;'>{d.final_status}</span></td>"
                f"<td><strong>{d.assigned_room or 'None'}</strong></td>"
                f"<td>{d.assigned_date or 'N/A'}<br><small>{f'{d.assigned_hour}:00' if d.assigned_hour else ''}</small></td>"
                f"<td><pre style='margin:0; font-size:11px;'>{d.why}</pre></td>"
                f"</tr>"
            )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Campus Allocation Report - Week {week_str}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 18px; background: #1e293b; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 12px 14px; border-bottom: 1px solid rgba(255,255,255,0.08); text-align: left; }}
  th {{ background: #334155; color: #94a3b8; font-size: 12px; text-transform: uppercase; }}
  h1 {{ color: #38bdf8; margin-bottom: 4px; }}
</style>
</head>
<body>
  <h1>Campus Allocation Report — Week {week_str}</h1>
  <p style="color:#94a3b8;">Offline Deterministic Kernel Result Export · Generated {datetime.utcnow().isoformat()}</p>
  <table>
    <thead>
      <tr>
        <th>Club / Request</th>
        <th>Status</th>
        <th>Assigned Room</th>
        <th>Date & Time</th>
        <th>Rule Trace & Explanation</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>"""

        with open(html_path, mode="w", encoding="utf-8") as f:
            f.write(html_content)

        return html_path
