from __future__ import annotations

from typing import Dict, Optional, List
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import questionary

from allocator.models import AllocationResult, Decision
from ..theme import (
    render_top_bar,
    make_framed_container,
    BINSIDER_QUESTIONARY_STYLE,
)


class ResultsScreen:
    def __init__(self, console: Console, last_result_holder: Dict[str, Optional[AllocationResult]]) -> None:
        self.console = console
        self.last_result_holder = last_result_holder

    def show(self) -> None:
        result = self.last_result_holder.get("current")
        if result is None:
            self.console.clear()
            self.console.print(render_top_bar(active_tab="Results", context_path="/results/none"))
            msg = Text.from_markup("[yellow]No allocation has been run yet in this session. Run Screen 4 (Allocate) first.[/yellow]")
            self.console.print(make_framed_container(msg, subtitle="[dim]No results loaded[/dim]"))
            questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            return

        while True:
            self.console.clear()
            self.console.print(render_top_bar(active_tab="Results", context_path=f"/results/{result.week}"))

            content = Text.from_markup(
                f"[bold white]Allocation Decisions & Why-Traces — Week {result.week}[/bold white]\n"
                f"[dim white]Inspect deterministic match traces, clash relocations, and hard constraint rejections.[/dim white]\n\n"
                f"Total decisions recorded: [bold #5af78e]{len(result.decisions)}[/bold #5af78e]"
            )
            self.console.print(make_framed_container(content, subtitle="[bold #5af78e]Enter[/bold #5af78e][dim]→ Select[/dim] | [bold #ff5555]Bksp/0[/bold #ff5555][dim]→ Back[/dim]"))

            choice = questionary.select(
                "Select Results View Mode:",
                choices=[
                    "1. Summary by status breakdown",
                    "2. Full list with rule trace (--why explanation)",
                    "3. Show conflicts & relocations only",
                    "4. Show rejected requests with reasons",
                    "5. Show moved requests (room swaps)",
                    "6. Show deferred requests (club cap)",
                    "0. Back to Main Menu",
                ],
                style=BINSIDER_QUESTIONARY_STYLE,
            ).ask()

            if not choice or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                self._show_summary_status(result)
            elif choice.startswith("2"):
                self._show_filtered_list(result, filter_status=None, show_why=True)
            elif choice.startswith("3"):
                self._show_conflicts(result)
            elif choice.startswith("4"):
                self._show_filtered_list(result, filter_status="Rejected", show_why=True)
            elif choice.startswith("5"):
                self._show_filtered_list(result, filter_status="Moved", show_why=True)
            elif choice.startswith("6"):
                self._show_filtered_list(result, filter_status="Deferred", show_why=True)

    def _show_summary_status(self, result: AllocationResult) -> None:
        self.console.clear()
        self.console.print(render_top_bar(active_tab="Results", context_path=f"/results/{result.week}/summary"))

        table = Table(
            title=f"Allocation Status Breakdown — Week {result.week}",
            box=box.SQUARE,
            border_style="bright_black",
            header_style="bold white",
            expand=True,
        )
        table.add_column("Decision Status", style="bold white")
        table.add_column("Count", justify="right", style="bold #5af78e")
        table.add_column("Percentage", justify="right", style="cyan")

        total = len(result.decisions)
        counts = {
            "Approved": sum(1 for d in result.decisions if d.final_status == "Approved"),
            "Moved": sum(1 for d in result.decisions if d.final_status == "Moved"),
            "Waitlisted": sum(1 for d in result.decisions if d.final_status == "Waitlisted"),
            "Rejected": sum(1 for d in result.decisions if d.final_status == "Rejected"),
            "Deferred": sum(1 for d in result.decisions if d.final_status == "Deferred"),
        }

        for st, c in counts.items():
            pct = (c / max(1, total)) * 100.0
            color = "#5af78e" if st == "Approved" else ("#f1fa8c" if st == "Moved" else ("#ff5555" if st == "Rejected" else "#8be9fd"))
            table.add_row(f"[{color}]{st}[/{color}]", str(c), f"{pct:.1f}%")

        self.console.print(make_framed_container(table, subtitle="[dim]Press Enter to return[/dim]"))
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()

    def _show_filtered_list(self, result: AllocationResult, filter_status: Optional[str], show_why: bool) -> None:
        self.console.clear()
        self.console.print(render_top_bar(active_tab="Results", context_path=f"/results/{result.week}/trace"))

        decisions = [d for d in result.decisions if filter_status is None or d.final_status == filter_status]
        if not decisions:
            self.console.print(f"[yellow]No requests found with status '{filter_status}'.[/yellow]")
            questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            return

        table = Table(
            title=f"Decisions Trace ({len(decisions)} items)",
            box=box.SQUARE,
            border_style="bright_black",
            header_style="bold white",
            expand=True,
        )
        table.add_column("Club / ID", style="bold white", ratio=2)
        table.add_column("Status", justify="center", ratio=1)
        table.add_column("Assigned", style="bold #5af78e", justify="center", ratio=1)
        table.add_column("Date / Time", style="yellow", justify="center", ratio=1)
        if show_why:
            table.add_column("Deterministic Rule Trace & Why Narration", style="dim white", ratio=4)

        for d in decisions:
            badge_color = "#5af78e" if d.final_status == "Approved" else ("#f1fa8c" if d.final_status == "Moved" else ("#ff5555" if d.final_status == "Rejected" else "#8be9fd"))
            dt_str = f"{d.assigned_date or 'N/A'} {d.assigned_hour}:00" if d.assigned_hour else "N/A"

            row_data = [
                f"{d.club}\n[dim]{d.request_id}[/dim]",
                f"[bold {badge_color}]{d.final_status}[/]",
                d.assigned_room or "None",
                dt_str,
            ]
            if show_why:
                row_data.append(d.why)

            table.add_row(*row_data)

        self.console.print(make_framed_container(table, subtitle="[dim]Press Enter to return[/dim]"))
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()

    def _show_conflicts(self, result: AllocationResult) -> None:
        conflicts = [d for d in result.decisions if d.final_status in ("Moved", "Waitlisted", "Rejected")]
        if not conflicts:
            self.console.print("[green]No room schedule conflicts occurred this cycle.[/green]")
            questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            return
        self._show_filtered_list(result, filter_status=None, show_why=True)
