from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
import questionary

from allocator.models import Settings
from allocator.llm import LLMNarrator
from ..theme import (
    render_top_bar,
    make_framed_container,
    BINSIDER_QUESTIONARY_STYLE,
)


class SettingsScreen:
    def __init__(self, console: Console, settings: Settings, narrator: LLMNarrator) -> None:
        self.console = console
        self.settings = settings
        self.narrator = narrator

    def show(self) -> None:
        while True:
            self.console.clear()
            self.console.print(render_top_bar(active_tab="Settings", context_path="/config/settings.env"))

            table = Table(
                title="System Configuration & Environment Variables",
                box=box.SQUARE,
                border_style="bright_black",
                header_style="bold white",
                expand=True,
            )
            table.add_column("Parameter / Setting", style="bold white")
            table.add_column("Current Runtime Value", style="bold #5af78e")

            table.add_row("Shared Reports Directory", self.settings.shared_folder)
            table.add_row("Week Start Day", self.settings.week_start_day)
            table.add_row("Local LLM Narration Layer", "[bold #5af78e]ENABLED[/]" if self.settings.enable_llm else "[bold #ff5555]DISABLED[/]")
            table.add_row("Ollama LLM Model Name", self.settings.llm_model)
            table.add_row("Local Endpoint URL", self.settings.ollama_url)

            self.console.print(make_framed_container(table, subtitle="[bold #5af78e]Enter[/bold #5af78e][dim]→ Select[/dim] | [bold #ff5555]Bksp/0[/bold #ff5555][dim]→ Back[/dim]"))

            choice = questionary.select(
                "Select Setting to Modify:",
                choices=[
                    "1. Set shared folder path for reports",
                    "2. Set week start day (Monday / Sunday)",
                    "3. Toggle local LLM narration (Gemma)",
                    "4. Set LLM model name",
                    "0. Back to Main Menu",
                ],
                style=BINSIDER_QUESTIONARY_STYLE,
            ).ask()

            if not choice or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                new_path = questionary.text("Enter shared reports directory:", default=self.settings.shared_folder, style=BINSIDER_QUESTIONARY_STYLE).ask()
                if new_path:
                    self.settings.shared_folder = new_path.strip()
                    self.console.print(f"[bold #5af78e]✓ Reports folder updated to: {self.settings.shared_folder}[/bold #5af78e]")
            elif choice.startswith("2"):
                new_day = questionary.select("Select week start day:", choices=["Monday", "Sunday"], style=BINSIDER_QUESTIONARY_STYLE).ask()
                if new_day:
                    self.settings.week_start_day = new_day
                    self.console.print(f"[bold #5af78e]✓ Week start day updated to: {self.settings.week_start_day}[/bold #5af78e]")
            elif choice.startswith("3"):
                self.settings.enable_llm = not self.settings.enable_llm
                self.narrator.enabled = self.settings.enable_llm
                self.console.print(f"[bold #5af78e]✓ LLM narration toggled {'ON' if self.settings.enable_llm else 'OFF'}.[/bold #5af78e]")
            elif choice.startswith("4"):
                new_model = questionary.text("Enter local model name:", default=self.settings.llm_model, style=BINSIDER_QUESTIONARY_STYLE).ask()
                if new_model:
                    self.settings.llm_model = new_model.strip()
                    self.narrator.model_name = self.settings.llm_model
                    self.console.print(f"[bold #5af78e]✓ Model set to: {self.settings.llm_model}[/bold #5af78e]")
