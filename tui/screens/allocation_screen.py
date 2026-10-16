from __future__ import annotations

from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import questionary

from allocator.models import (
    Room,
    RoomRequest,
    AllocationResult,
    Decision,
    AdminOverride,
    ExceptionCase,
)
from allocator.loader import DataLoader
from allocator.occupancy import OccupancyIndex
from allocator.kernel import AllocationKernel
from allocator.reports import ReportPublisher
from allocator.llm import LLMNarrator
from ..theme import (
    render_top_bar,
    make_framed_container,
    BINSIDER_QUESTIONARY_STYLE,
)


class AllocationScreen:
    def __init__(
        self,
        console: Console,
        rooms: Dict[str, Room],
        occupancy: OccupancyIndex,
        loader: DataLoader,
        publisher: ReportPublisher,
        narrator: LLMNarrator,
        pending_requests: List[RoomRequest],
        last_result_holder: Dict[str, Optional[AllocationResult]],
    ) -> None:
        self.console = console
        self.rooms = rooms
        self.occupancy = occupancy
        self.loader = loader
        self.publisher = publisher
        self.narrator = narrator
        self.pending_requests = pending_requests
        self.last_result_holder = last_result_holder
        self.last_week = "2025-08-03"

    def show(self) -> None:
        while True:
            self.console.clear()
            self.console.print(render_top_bar(active_tab="Allocate", context_path="/kernel/allocate"))

            content = Text.from_markup(
                "[bold white]Deterministic Room Allocation Kernel[/bold white]\n"
                "[dim white]Executes hard feasibility filtering, tiebreaking, club quotas, and rule trace generation.[/dim white]\n\n"
                f"Ready to process [bold #5af78e]{len(self.pending_requests)}[/bold #5af78e] pending requests for target week [bold #8be9fd]{self.last_week}[/bold #8be9fd]."
            )
            self.console.print(make_framed_container(content, subtitle="[bold #5af78e]Enter[/bold #5af78e][dim]→ Select[/dim] | [bold #ff5555]Bksp/0[/bold #ff5555][dim]→ Back[/dim]"))

            choice = questionary.select(
                "Select Allocation Action:",
                choices=[
                    "1. Run allocation cycle for target week",
                    "2. Re-run previous week",
                    "3. Dry-run simulation (no files written)",
                    "0. Back to Main Menu",
                ],
                style=BINSIDER_QUESTIONARY_STYLE,
            ).ask()

            if not choice or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                self._run_allocation(dry_run=False)
            elif choice.startswith("2"):
                self._rerun_last_week()
            elif choice.startswith("3"):
                self._run_allocation(dry_run=True)

    def _rerun_last_week(self) -> None:
        if not self.last_week:
            self.console.print("[yellow]No prior week has been run yet.[/yellow]")
            questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            return
        self.console.print(f"[cyan]Re-running allocation for week {self.last_week}...[/cyan]")
        self._execute_allocation(self.last_week, dry_run=False)

    def _run_allocation(self, dry_run: bool) -> None:
        inbox_base = Path("inbox")
        available_weeks = [d.name for d in inbox_base.iterdir() if d.is_dir()] if inbox_base.exists() else []

        if available_weeks:
            available_weeks.append("Enter custom week...")
            target_week = questionary.select("Select target week to allocate:", choices=available_weeks, style=BINSIDER_QUESTIONARY_STYLE).ask()
            if target_week == "Enter custom week...":
                target_week = questionary.text("Enter target week (YYYY-MM-DD):", default=self.last_week, style=BINSIDER_QUESTIONARY_STYLE).ask()
        else:
            target_week = questionary.text("Enter target week folder (YYYY-MM-DD):", default=self.last_week, style=BINSIDER_QUESTIONARY_STYLE).ask()

        if not target_week:
            return

        self._execute_allocation(target_week, dry_run=dry_run)

    def _execute_allocation(self, week_str: str, dry_run: bool) -> None:
        self.last_week = week_str
        self.console.clear()
        self.console.print(render_top_bar(active_tab="Allocate", context_path=f"/kernel/{week_str}"))

        inbox_reqs, _ = self.loader.load_inbox_week(week_str)
        all_reqs = list(self.pending_requests) + inbox_reqs

        if not all_reqs:
            self.console.print(f"[yellow]No requests found for week '{week_str}' in pending pool or inbox/{week_str}/.[/yellow]")
            questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            return

        self.console.print(f"[bold #5af78e]>> Running deterministic kernel on {len(all_reqs)} request(s)...[/bold #5af78e]")

        kernel = AllocationKernel(self.rooms, self.occupancy)
        result = kernel.run(week_str, all_reqs)

        app_count = sum(1 for d in result.decisions if d.final_status == "Approved")
        mov_count = sum(1 for d in result.decisions if d.final_status == "Moved")
        rej_count = sum(1 for d in result.decisions if d.final_status == "Rejected")
        def_count = sum(1 for d in result.decisions if d.final_status == "Deferred")
        wtl_count = sum(1 for d in result.decisions if d.final_status == "Waitlisted")
        exc_count = len(result.exceptions)

        table = Table(
            title=f"Allocation Results Breakdown — Week {week_str}",
            box=box.SQUARE,
            border_style="bright_black",
            header_style="bold white",
            expand=True,
        )
        table.add_column("Category / Decision Outcome", style="bold white")
        table.add_column("Count", justify="right", style="bold #5af78e")
        table.add_column("Status Meaning", style="dim white")

        table.add_row("Approved (Top Preference)", str(app_count), "Assigned requested primary room")
        table.add_row("Moved (Alternative Feasible)", str(mov_count), "Swapped to alternate room/slot due to clash")
        table.add_row("Waitlisted", str(wtl_count), "Demand exceeds concurrent campus capacity")
        table.add_row("Rejected (Infeasible)", str(rej_count), "Failed hard capacity or equipment requirement")
        table.add_row("Deferred (Weekly Quota)", str(def_count), "Held for next cycle under club weekly cap")
        table.add_row("Exceptions Flagged", f"[bold red]{exc_count}[/bold red]" if exc_count else "0", "Ambiguous cases escalated for review")

        self.console.print(make_framed_container(table, subtitle="[dim]Deterministic allocation cycle executed[/dim]"))

        # Handle Exceptions
        if exc_count > 0:
            review = questionary.confirm(f"Review {exc_count} exception(s) now in Exception Review Queue?", default=True, style=BINSIDER_QUESTIONARY_STYLE).ask()
            if review:
                self._run_exception_queue(result)

        # Write files if not dry-run
        if not dry_run:
            self.console.print("[dim white]Writing output files and running local Gemma narration pass...[/dim white]")
            for d in result.decisions:
                d_dict = d.to_dict()
                d.why = self.narrator.narrate_decision(d_dict)

            json_path = self.publisher.write_results_json(week_str, result)
            txt_path = self.publisher.write_summary_txt(week_str, result)
            club_paths = self.publisher.write_club_reports(week_str, result)
            html_path = self.publisher.export_as_html(week_str, result)

            with open(json_path, mode="r", encoding="utf-8") as f:
                import json
                res_data = json.load(f)
            flags_content = self.narrator.generate_flags_markdown(res_data)
            flags_path = Path("results") / week_str / "flags.md"
            with open(flags_path, mode="w", encoding="utf-8") as f:
                f.write(flags_content)

            for d in result.decisions:
                if d.final_status == "Deferred":
                    for req in all_reqs:
                        if req.request_id == d.request_id:
                            self.loader.write_deferred(week_str, req)

            summary_box = Text.from_markup(
                f"[bold #5af78e]✓ Results committed to disk:[/bold #5af78e]\n"
                f"  • JSON: [cyan]{json_path}[/cyan]\n"
                f"  • Flags: [cyan]{flags_path}[/cyan]\n"
                f"  • Summary: [cyan]{txt_path}[/cyan]\n"
                f"  • Reports: [cyan]{len(club_paths)} files in reports/{week_str}/[/cyan]\n"
                f"  • HTML Dashboard: [cyan]{html_path}[/cyan]"
            )
            self.console.print(make_framed_container(summary_box, subtitle="[dim]Outputs successfully written to disk[/dim]"))
        else:
            self.console.print("[yellow]Dry-run complete. No files written to disk.[/yellow]")

        self.last_result_holder["current"] = result
        self.pending_requests.clear()
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()

    def _run_exception_queue(self, result: AllocationResult) -> None:
        idx = 0
        total = len(result.exceptions)

        while 0 <= idx < total:
            exc = result.exceptions[idx]
            self.console.clear()
            self.console.print(render_top_bar(active_tab="Allocate", context_path=f"exception: {idx+1}/{total}"))

            exc_text = (
                f"[bold yellow]EXCEPTION {idx+1} of {total} — [{exc.exception_type}][/bold yellow]\n\n"
                f"[bold white]Club / Submitter:[/bold white] {exc.request.club} [dim]({exc.request.request_id})[/dim]\n"
                f"[bold white]Situation:[/bold white] {exc.situation}\n"
                f"[bold white]Auto-Pick Recommendation:[/bold white] [bold #5af78e]{exc.auto_pick or 'None'}[/bold #5af78e]\n"
                f"[bold white]Candidate Rooms:[/bold white] [cyan]{', '.join(exc.possible_rooms) if exc.possible_rooms else 'None'}[/cyan]"
            )
            self.console.print(make_framed_container(Text.from_markup(exc_text), subtitle="[dim]Admin Exception Review Queue[/dim]"))

            action = questionary.select(
                "Admin Resolution Action:",
                choices=[
                    "1. Accept auto-pick recommendation",
                    "2. Assign a different room",
                    "3. Adjust time slot hour",
                    "4. Defer to next cycle",
                    "5. Reject request",
                    "n. Next exception",
                    "p. Previous exception",
                    "q. Quit queue and proceed to file export",
                ],
                style=BINSIDER_QUESTIONARY_STYLE,
            ).ask()

            if not action or action.startswith("q"):
                break
            elif action.startswith("n"):
                idx += 1
            elif action.startswith("p"):
                idx = max(0, idx - 1)
            elif action.startswith("1"):
                exc.resolved = True
                exc.chosen_action = f"Accepted auto-pick: {exc.auto_pick}"
                self.console.print(f"[bold #5af78e]✓ Accepted auto-pick for {exc.request.club}.[/bold #5af78e]")
                idx += 1
            elif action.startswith("2"):
                chosen_room = questionary.text("Enter override Room ID:", default=exc.auto_pick or "R063", style=BINSIDER_QUESTIONARY_STYLE).ask()
                if chosen_room:
                    for d in result.decisions:
                        if d.request_id == exc.request.request_id:
                            orig = d.to_dict()
                            d.assigned_room = chosen_room.strip()
                            d.final_status = "Approved"
                            d.decided_by = "admin"
                            d.rule_trace.append(f"Admin override assigned {chosen_room.strip()}")
                            result.overrides.append(
                                AdminOverride(
                                    timestamp=datetime.utcnow().isoformat(),
                                    request_id=exc.request.request_id,
                                    admin_action="Override Room",
                                    original_decision=orig,
                                    new_decision=d.to_dict(),
                                    notes=f"Admin assigned {chosen_room.strip()}",
                                )
                            )
                            break
                    exc.resolved = True
                    self.console.print(f"[bold #5af78e]✓ Override applied: {chosen_room.strip()} assigned.[/bold #5af78e]")
                idx += 1
            elif action.startswith("4"):
                for d in result.decisions:
                    if d.request_id == exc.request.request_id:
                        orig = d.to_dict()
                        d.final_status = "Deferred"
                        d.assigned_room = None
                        d.decided_by = "admin"
                        result.overrides.append(
                            AdminOverride(
                                timestamp=datetime.utcnow().isoformat(),
                                request_id=exc.request.request_id,
                                admin_action="Defer Request",
                                original_decision=orig,
                                new_decision=d.to_dict(),
                                notes="Admin deferred request to next week",
                            )
                        )
                exc.resolved = True
                self.console.print(f"[bold #5af78e]✓ Request {exc.request.request_id} deferred.[/bold #5af78e]")
                idx += 1
            elif action.startswith("5"):
                for d in result.decisions:
                    if d.request_id == exc.request.request_id:
                        orig = d.to_dict()
                        d.final_status = "Rejected"
                        d.assigned_room = None
                        d.decided_by = "admin"
                        result.overrides.append(
                            AdminOverride(
                                timestamp=datetime.utcnow().isoformat(),
                                request_id=exc.request.request_id,
                                admin_action="Reject Request",
                                original_decision=orig,
                                new_decision=d.to_dict(),
                                notes="Admin rejected request during exception review",
                            )
                        )
                exc.resolved = True
                self.console.print(f"[bold #5af78e]✓ Request {exc.request.request_id} marked as Rejected.[/bold #5af78e]")
                idx += 1
