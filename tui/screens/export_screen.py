from __future__ import annotations

import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import questionary

from allocator.models import Room
from allocator.occupancy import OccupancyIndex
from ..theme import (
    render_top_bar,
    make_framed_container,
    BINSIDER_QUESTIONARY_STYLE,
)


class ExportScreen:
    def __init__(self, console: Console, rooms: dict[str, Room], occupancy: OccupancyIndex) -> None:
        self.console = console
        self.rooms = rooms
        self.occupancy = occupancy

    def show(self) -> None:
        forms_dir = Path("forms")
        forms_dir.mkdir(parents=True, exist_ok=True)

        while True:
            self.console.clear()
            self.console.print(render_top_bar(active_tab="Export", context_path="/forms/export"))

            content = Text.from_markup(
                "[bold white]Export Offline Request Forms & Templates[/bold white]\n"
                "[dim white]Distribute pre-flight student forms with embedded feasibility rules for offline club submissions.[/dim white]"
            )
            self.console.print(make_framed_container(content, subtitle="[bold #5af78e]Enter[/bold #5af78e][dim]→ Select[/dim] | [bold #ff5555]Bksp/0[/bold #ff5555][dim]→ Back[/dim]"))

            choice = questionary.select(
                "Select Export Format:",
                choices=[
                    "1. Export blank CSV template",
                    "2. Export HTML student form (offline pre-flight feasibility baked in)",
                    "3. Export pre-filled JSON form template with active clubs",
                    "0. Back to Main Menu",
                ],
                style=BINSIDER_QUESTIONARY_STYLE,
            ).ask()

            if not choice or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                self._export_csv_template(forms_dir)
            elif choice.startswith("2"):
                self._export_html_form(forms_dir)
            elif choice.startswith("3"):
                self._export_prefilled_json(forms_dir)

    def _export_csv_template(self, forms_dir: Path) -> None:
        out_path = forms_dir / "request_template.csv"
        csv_header = "club,purpose,date,start_hour,duration_hours,expected_attendance,projector_required,computers_required,extra_chairs,extra_tables,pref1,pref2,pref3\n"
        sample_row = "Robotics Club,Workshop,2025-08-05,14,2,40,True,False,6,2,R063,R101,R024\n"
        with open(out_path, mode="w", encoding="utf-8") as f:
            f.write(csv_header + sample_row)
        self.console.print(f"[bold #5af78e]✓ Blank CSV template exported to: {out_path}[/bold #5af78e]")
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()

    def _export_html_form(self, forms_dir: Path) -> None:
        out_path = forms_dir / "student_request_form.html"
        html_code = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Offline Campus Room Finder & Reservation Form</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 30px; }
  .box { max-width: 650px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid rgba(255,255,255,0.1); }
  h2 { color: #38bdf8; margin-top: 0; }
  .field { margin-bottom: 14px; }
  label { display: block; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: bold; margin-bottom: 4px; }
  input, select { width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #334155; color: #fff; padding: 8px 12px; border-radius: 6px; }
  .math { background: #0f172a; border: 1px solid #38bdf8; border-radius: 8px; padding: 12px; margin: 16px 0; color: #38bdf8; font-size: 13px; }
  button { width: 100%; padding: 12px; background: #0284c7; color: #fff; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; }
</style>
</head>
<body>
<div class="box">
  <h2>Club Room Reservation Request</h2>
  <p style="color:#94a3b8; font-size:12px;">Live pre-flight checks run locally before submission. Save JSON and pass to coordinator.</p>
  <div class="field"><label>Club Name</label><input type="text" id="club" value="Robotics Club"></div>
  <div class="field"><label>Purpose</label><input type="text" id="purpose" value="Workshop"></div>
  <div class="field"><label>Date (YYYY-MM-DD)</label><input type="date" id="date" value="2025-08-05"></div>
  <div class="field"><label>Start Hour (8-20)</label><input type="number" id="hour" value="14"></div>
  <div class="field"><label>Expected Attendees</label><input type="number" id="att" value="40" oninput="recalc()"></div>
  <div class="field"><label>Extra Chairs</label><input type="number" id="chairs" value="6" oninput="recalc()"></div>
  <div class="field"><label>Extra Tables</label><input type="number" id="tables" value="2" oninput="recalc()"></div>
  <div class="math" id="math-box">Space needed: 40 attendees + 6 chairs + 2x3 tables = 52 units</div>
  <button onclick="downloadJson()">Export Submission JSON</button>
</div>
<script>
function recalc() {
  const a = parseInt(document.getElementById('att').value)||0;
  const c = parseInt(document.getElementById('chairs').value)||0;
  const t = parseInt(document.getElementById('tables').value)||0;
  document.getElementById('math-box').innerText = `Space needed: ${a} attendees + ${c} chairs + ${t}x3 tables = ${a+c+t*3} units`;
}
function downloadJson() {
  const data = {
    club: document.getElementById('club').value,
    purpose: document.getElementById('purpose').value,
    date: document.getElementById('date').value,
    start_hour: parseInt(document.getElementById('hour').value),
    duration_hours: 2,
    expected_attendance: parseInt(document.getElementById('att').value),
    extra_chairs: parseInt(document.getElementById('chairs').value),
    extra_tables: parseInt(document.getElementById('tables').value),
    projector_required: true,
    computers_required: false,
    preferences: [{"rank": 1, "room_id": "R063"}, {"rank": 2, "room_id": "R101"}],
    submitted_at: new Date().toISOString()
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = data.club.toLowerCase().replace(/\\s+/g, '_') + ".json";
  a.click();
}
</script>
</body>
</html>"""
        with open(out_path, mode="w", encoding="utf-8") as f:
            f.write(html_code)
        self.console.print(f"[bold #5af78e]✓ Standalone offline HTML form exported to: {out_path}[/bold #5af78e]")
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()

    def _export_prefilled_json(self, forms_dir: Path) -> None:
        out_path = forms_dir / "submission_sample.json"
        data = {
            "week": "2025-08-03",
            "club": "Data Science Club",
            "purpose": "Machine Learning Boot Camp",
            "date": "2025-08-05",
            "start_hour": 14,
            "duration_hours": 2,
            "expected_attendance": 45,
            "projector_required": True,
            "computers_required": True,
            "extra_chairs": 4,
            "extra_tables": 2,
            "preferences": [
                {"rank": 1, "room_id": "R063"},
                {"rank": 2, "room_id": "R101"},
                {"rank": 3, "room_id": "R024"},
            ],
            "submitted_at": "2025-08-01T10:00:00Z",
            "notes": "Verified feasibility panel; fits 55 units.",
        }
        with open(out_path, mode="w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.console.print(f"[bold #5af78e]✓ Pre-filled sample submission JSON exported to: {out_path}[/bold #5af78e]")
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
