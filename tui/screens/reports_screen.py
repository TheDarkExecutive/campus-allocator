from __future__ import annotations

from typing import Dict, Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import questionary

from allocator.models import AllocationResult
from allocator.reports import ReportPublisher
from ..theme import (
    render_top_bar,
    make_framed_container,
    BINSIDER_QUESTIONARY_STYLE,
)


class ReportsScreen:
    def __init__(
        self,
        console: Console,
        publisher: ReportPublisher,
        last_result_holder: Dict[str, Optional[AllocationResult]],
    ) -> None:
        self.console = console
        self.publisher = publisher
        self.last_result_holder = last_result_holder

    def show(self) -> None:
        result = self.last_result_holder.get("current")
        if result is None:
            self.console.clear()
            self.console.print(render_top_bar(active_tab="Results", context_path="/reports/none"))
            msg = Text.from_markup("[yellow]No active allocation result found. Run Screen 4 (Allocate) first.[/yellow]")
            self.console.print(make_framed_container(msg, subtitle="[dim]No results loaded[/dim]"))
            questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            return

        while True:
            self.console.clear()
            self.console.print(render_top_bar(active_tab="Results", context_path=f"/reports/{result.week}"))

            content = Text.from_markup(
                f"[bold white]Publish Per-Club Notices & Summaries — Week {result.week}[/bold white]\n"
                f"[dim white]Generate standalone Markdown notices and static HTML dashboard for distribution.[/dim white]"
            )
            self.console.print(make_framed_container(content, subtitle="[bold #5af78e]Enter[/bold #5af78e][dim]→ Select[/dim] | [bold #ff5555]Bksp/0[/bold #ff5555][dim]→ Back[/dim]"))

            choice = questionary.select(
                "Select Publish Action:",
                choices=[
                    "1. Publish per-club reports (Markdown notices)",
                    "2. Publish weekly summary (text file)",
                    "3. Export full interactive HTML report",
                    "0. Back to Main Menu",
                ],
                style=BINSIDER_QUESTIONARY_STYLE,
            ).ask()

            if not choice or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                paths = self.publisher.write_club_reports(result.week, result)
                self.console.print(f"[bold #5af78e]✓ Generated {len(paths)} markdown reports in 'reports/{result.week}/'.[/bold #5af78e]")
                questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            elif choice.startswith("2"):
                sum_path = self.publisher.write_summary_txt(result.week, result)
                self.console.print(f"[bold #5af78e]✓ Weekly summary published to: {sum_path}[/bold #5af78e]")
                questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
            elif choice.startswith("3"):
                html_path = self.publisher.export_as_html(result.week, result)
                self.console.print(f"[bold #5af78e]✓ Full report exported to HTML: {html_path}[/bold #5af78e]")
                questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
