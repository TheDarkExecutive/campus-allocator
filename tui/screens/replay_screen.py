from __future__ import annotations

from typing import Dict, List, Optional
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import questionary

from allocator.models import Room, RoomRequest
from allocator.loader import DataLoader
from allocator.occupancy import OccupancyIndex
from allocator.replay import ReplayValidator, ReplayMetrics
from ..theme import (
    render_top_bar,
    make_framed_container,
    BINSIDER_QUESTIONARY_STYLE,
)


class ReplayScreen:
    def __init__(
        self,
        console: Console,
        rooms: Dict[str, Room],
        occupancy: OccupancyIndex,
        loader: DataLoader,
    ) -> None:
        self.console = console
        self.rooms = rooms
        self.occupancy = occupancy
        self.loader = loader

    def show(self) -> None:
        self.console.clear()
        self.console.print(render_top_bar(active_tab="Replay", context_path="/data/room_requests.csv"))

        content = Text.from_markup(
            "[bold white]Historical Outcome Replay Validator[/bold white]\n"
            "[dim white]Benchmarking deterministic kernel decisions against 5,000 historical ground-truth university outcomes.[/dim white]"
        )
        self.console.print(make_framed_container(content, subtitle="[dim]Select evaluation size[/dim]"))

        hist_reqs = self.loader.load_room_requests_csv("room_requests.csv")
        if not hist_reqs:
            self.console.print("[yellow]Could not find or load data/room_requests.csv. Ensure dataset is present.[/yellow]")
            questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            return

        sample_choice = questionary.select(
            "Evaluation Sample Benchmark Size:",
            choices=["Fast Benchmark (First 500 rows)", "Quick Test (First 100 rows)", "Full Dataset (All rows)", "Cancel"],
            style=BINSIDER_QUESTIONARY_STYLE,
        ).ask()

        if not sample_choice or sample_choice == "Cancel":
            return

        limit = None
        if "500" in sample_choice:
            limit = 500
        elif "100" in sample_choice:
            limit = 100

        with self.console.status("[bold #5af78e]Running deterministic kernel replay pass against historical labels..."):
            validator = ReplayValidator(self.rooms, self.occupancy)
            metrics = validator.run_replay(hist_reqs, max_samples=limit)

        table = Table(
            title="Historical Outcome Agreement Matrix",
            box=box.SQUARE,
            border_style="bright_black",
            header_style="bold white",
            expand=True,
        )
        table.add_column("Outcome Category", style="bold white")
        table.add_column("Matched / Total Evaluated", justify="right", style="cyan")
        table.add_column("Accuracy Agreement (%)", justify="right", style="bold #5af78e")

        table.add_row(
            "Approved Matches",
            f"{metrics.approved_matches} / {metrics.approved_total}",
            f"{metrics.approved_pct:.1f}%",
        )
        table.add_row(
            "Rejected Matches",
            f"{metrics.rejected_matches} / {metrics.rejected_total}",
            f"{metrics.rejected_pct:.1f}%",
        )
        table.add_row(
            "Waitlisted Matches",
            f"{metrics.waitlisted_matches} / {metrics.waitlisted_total}",
            f"{metrics.waitlisted_pct:.1f}%",
        )
        table.add_section()
        table.add_row(
            "[bold white]Overall Benchmark Agreement[/bold white]",
            f"[bold #8be9fd]{metrics.total_matches} / {metrics.total_evaluated}[/bold #8be9fd]",
            f"[bold #5af78e]{metrics.overall_agreement:.1f}%[/bold #5af78e]",
        )

        self.console.print(make_framed_container(table, subtitle="[dim]Replay benchmark completed[/dim]"))

        if metrics.mismatches:
            show_mismatches = questionary.confirm("Inspect individual mismatch samples?", default=False, style=BINSIDER_QUESTIONARY_STYLE).ask()
            if show_mismatches:
                mis_table = Table(
                    title="Sample Kernel Disagreements",
                    box=box.SQUARE,
                    border_style="bright_black",
                    header_style="bold white",
                    expand=True,
                )
                mis_table.add_column("Request ID", style="bold #5af78e")
                mis_table.add_column("Date / Hour", style="dim")
                mis_table.add_column("Cap", justify="right")
                mis_table.add_column("Ground Truth", style="bold yellow")
                mis_table.add_column("Kernel Decision", style="bold #ff5555")

                for m in metrics.mismatches[:10]:
                    mis_table.add_row(
                        m["request_id"],
                        f"{m['date']} H{m['hour']}",
                        str(m["capacity"]),
                        m["actual"],
                        m["predicted"],
                    )
                self.console.print(make_framed_container(mis_table, subtitle="[dim]Sample discrepancies[/dim]"))

        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
