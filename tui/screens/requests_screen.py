from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import questionary

from allocator.models import RoomRequest, RoomPreference
from allocator.loader import DataLoader
from ..theme import (
    render_top_bar,
    make_framed_container,
    BINSIDER_QUESTIONARY_STYLE,
)


class RequestsScreen:
    def __init__(self, console: Console, loader: DataLoader, pending_requests: List[RoomRequest]) -> None:
        self.console = console
        self.loader = loader
        self.pending_requests = pending_requests

    def show(self) -> None:
        while True:
            self.console.clear()
            self.console.print(render_top_bar(active_tab="Requests", context_path="/inbox/2025-08-03"))

            content = Text.from_markup(
                "[bold white]Room Reservation Requests & Inbox Synced Pool[/bold white]\n"
                "[dim white]Import student submissions from offline JSON handoffs or enter urgent reservations manually.[/dim white]\n\n"
                f"Currently tracking [bold #5af78e]{len(self.pending_requests)}[/bold #5af78e] pending requests in memory."
            )
            self.console.print(make_framed_container(content, subtitle="[bold #5af78e]Enter[/bold #5af78e][dim]→ Select[/dim] | [bold #ff5555]Bksp/0[/bold #ff5555][dim]→ Back[/dim]"))

            choice = questionary.select(
                "Select Requests Action:",
                choices=[
                    "1. View pending request queue",
                    "2. Import JSON submissions from inbox/<week>/",
                    "3. Manual request entry",
                    "0. Back to Main Menu",
                ],
                style=BINSIDER_QUESTIONARY_STYLE,
            ).ask()

            if not choice or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                self._view_pending()
            elif choice.startswith("2"):
                self._import_inbox()
            elif choice.startswith("3"):
                self._manual_entry()

    def _view_pending(self) -> None:
        self.console.clear()
        self.console.print(render_top_bar(active_tab="Requests", context_path="/inbox/2025-08-03"))

        if not self.pending_requests:
            self.console.print("[yellow]No pending requests currently loaded in memory.[/yellow]")
            questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            return

        table = Table(
            title=f"Pending Room Requests Queue ({len(self.pending_requests)} Total)",
            box=box.SQUARE,
            border_style="bright_black",
            header_style="bold white",
            expand=True,
        )
        table.add_column("Request ID", style="bold #5af78e")
        table.add_column("Club", style="bold white")
        table.add_column("Purpose", style="yellow")
        table.add_column("Date", style="dim")
        table.add_column("Slot", justify="center")
        table.add_column("Space Needed", justify="right", style="cyan")
        table.add_column("Equip", justify="center")
        table.add_column("Preferences", style="dim white")

        for req in self.pending_requests:
            eq = []
            if req.projector_required: eq.append("Proj")
            if req.computers_required: eq.append("Comp")
            if req.accessible_required: eq.append("Acc")
            eq_str = ", ".join(eq) if eq else "None"
            pref_str = ", ".join([f"#{p.rank}:{p.room_id}" for p in req.preferences]) if req.preferences else "None"

            table.add_row(
                req.request_id,
                req.club,
                req.purpose,
                req.date,
                f"{req.start_hour}:00 (+{req.duration_hours}h)",
                f"{req.space_needed}u",
                eq_str,
                pref_str,
            )

        self.console.print(make_framed_container(table, subtitle="[dim]Press Enter to return[/dim]"))
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()

    def _import_inbox(self) -> None:
        self.console.clear()
        self.console.print(render_top_bar(active_tab="Requests", context_path="/inbox/"))

        inbox_base = Path("inbox")
        if not inbox_base.exists():
            inbox_base.mkdir(parents=True, exist_ok=True)

        week_dirs = [d.name for d in inbox_base.iterdir() if d.is_dir()]
        if not week_dirs:
            self.console.print(f"[yellow]No week subfolders found in '{inbox_base.resolve()}'.[/yellow]")
            target_week = questionary.text("Enter week folder name (e.g. 2025-08-03):", default="2025-08-03", style=BINSIDER_QUESTIONARY_STYLE).ask()
        else:
            week_dirs.append("Enter custom week...")
            target_week = questionary.select("Select inbox week folder:", choices=week_dirs, style=BINSIDER_QUESTIONARY_STYLE).ask()
            if target_week == "Enter custom week...":
                target_week = questionary.text("Enter week folder name (YYYY-MM-DD):", default="2025-08-03", style=BINSIDER_QUESTIONARY_STYLE).ask()

        if not target_week:
            return

        loaded_reqs, errors = self.loader.load_inbox_week(target_week)
        if errors:
            for err in errors:
                self.console.print(f"[red]⚠ {err}[/red]")

        if not loaded_reqs:
            self.console.print(f"[yellow]No valid .json submission files found in inbox/{target_week}/.[/yellow]")
            questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            return

        self.console.print(f"[bold #5af78e]Found {len(loaded_reqs)} submission(s) in inbox/{target_week}/.[/bold #5af78e]")
        confirm = questionary.confirm(f"Import {len(loaded_reqs)} request(s) into current pending pool?", style=BINSIDER_QUESTIONARY_STYLE).ask()
        if confirm:
            self.pending_requests.extend(loaded_reqs)
            self.console.print(f"[bold #5af78e]✓ Successfully imported {len(loaded_reqs)} request(s). Total pending: {len(self.pending_requests)}[/bold #5af78e]")
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()

    def _manual_entry(self) -> None:
        self.console.print("\n[bold #5af78e]Manual Room Reservation Request Entry:[/bold #5af78e]")
        club = questionary.text("Club Name (e.g. Robotics Club):", default="Robotics Club", style=BINSIDER_QUESTIONARY_STYLE).ask()
        purpose = questionary.text("Event Purpose:", default="Workshop", style=BINSIDER_QUESTIONARY_STYLE).ask()
        date_str = questionary.text("Event Date (YYYY-MM-DD):", default=datetime.utcnow().strftime("%Y-%m-%d"), style=BINSIDER_QUESTIONARY_STYLE).ask()
        start_hour_str = questionary.text("Start Hour (8-20):", default="14", style=BINSIDER_QUESTIONARY_STYLE).ask()
        duration_str = questionary.text("Duration in Hours (1-4):", default="2", style=BINSIDER_QUESTIONARY_STYLE).ask()
        headcount_str = questionary.text("Expected Attendees:", default="30", style=BINSIDER_QUESTIONARY_STYLE).ask()
        chairs_str = questionary.text("Extra Chairs:", default="4", style=BINSIDER_QUESTIONARY_STYLE).ask()
        tables_str = questionary.text("Extra Tables:", default="2", style=BINSIDER_QUESTIONARY_STYLE).ask()
        has_proj = questionary.confirm("Projector required?", default=True, style=BINSIDER_QUESTIONARY_STYLE).ask()
        has_comp = questionary.confirm("Lab computers required?", default=False, style=BINSIDER_QUESTIONARY_STYLE).ask()
        has_acc = questionary.confirm("Wheelchair accessibility required?", default=False, style=BINSIDER_QUESTIONARY_STYLE).ask()
        prefs_raw = questionary.text("Room Preferences (comma-separated, e.g. R063, R101):", default="R063, R101", style=BINSIDER_QUESTIONARY_STYLE).ask()

        prefs: List[RoomPreference] = []
        if prefs_raw:
            for rank, r_id in enumerate(prefs_raw.split(","), start=1):
                clean_id = r_id.strip()
                if clean_id:
                    prefs.append(RoomPreference(rank=rank, room_id=clean_id))

        req_id = f"MANUAL-{club[:4].upper()}-{datetime.utcnow().strftime('%H%M%S')}"

        try:
            req = RoomRequest(
                request_id=req_id,
                week=date_str,
                club=club.strip(),
                purpose=purpose.strip(),
                date=date_str.strip(),
                start_hour=int(start_hour_str),
                duration_hours=int(duration_str),
                expected_attendance=int(headcount_str),
                extra_chairs=int(chairs_str),
                extra_tables=int(tables_str),
                projector_required=bool(has_proj),
                computers_required=bool(has_comp),
                accessible_required=bool(has_acc),
                preferences=prefs,
                submitted_at=datetime.utcnow(),
            )
            self.pending_requests.append(req)
            self.console.print(f"[bold #5af78e]✓ Request {req.request_id} queued in pending pool. Total pending: {len(self.pending_requests)}[/bold #5af78e]")
        except Exception as e:
            self.console.print(f"[red]Error creating request: {e}[/red]")
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
