from __future__ import annotations

import sys
from typing import Dict, List, Optional, Any
from pathlib import Path
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich import box
import questionary

from allocator.models import Room, RoomRequest, AllocationResult, Settings
from allocator.loader import DataLoader
from allocator.occupancy import OccupancyIndex
from allocator.reports import ReportPublisher
from allocator.llm import LLMNarrator

from .theme import (
    render_top_bar,
    get_hero_banner,
    render_specs_box,
    render_submissions_queue_box,
    make_framed_container,
    render_footer_hotkeys,
    BINSIDER_QUESTIONARY_STYLE,
)

from .screens.rooms_screen import RoomsScreen
from .screens.requests_screen import RequestsScreen
from .screens.allocation_screen import AllocationScreen
from .screens.results_screen import ResultsScreen
from .screens.reports_screen import ReportsScreen
from .screens.dashboard_screen import DashboardScreen
from .screens.replay_screen import ReplayScreen
from .screens.export_screen import ExportScreen
from .screens.settings_screen import SettingsScreen


class CampusAllocatorApp:
    def __init__(self, data_dir: str = "data") -> None:
        self.console = Console()
        self.loader = DataLoader(data_dir=data_dir)
        self.settings = Settings()
        self.publisher = ReportPublisher(results_base="results", reports_base=self.settings.shared_folder)
        self.narrator = LLMNarrator(
            model_name=self.settings.llm_model,
            ollama_url=self.settings.ollama_url,
            enabled=self.settings.enable_llm,
        )

        # In-memory session state
        self.rooms: Dict[str, Room] = {}
        self.occupancy = OccupancyIndex()
        self.pending_requests: List[RoomRequest] = []
        self.last_result_holder: Dict[str, Optional[AllocationResult]] = {"current": None}
        self.target_week: str = "2025-08-04"

        # Initialize data
        self._bootstrap_data()

    def _bootstrap_data(self) -> None:
        self.rooms = self.loader.load_rooms()
        schedules = self.loader.load_class_schedule()
        events = self.loader.load_events()

        # Build initial occupancy index for baseline week
        self.occupancy.build_from_data(self.target_week, schedules, events)

        # Preload inbox requests if available
        inbox_reqs, _ = self.loader.load_inbox_week("2025-08-03")
        if inbox_reqs:
            self.pending_requests.extend(inbox_reqs)

    def run(self) -> None:
        while True:
            self._render_binsider_dashboard()

            choices = [
                "1. General (Refresh System Specs)",
                "2. Rooms (Metadata, Capacity & Facilities)",
                "3. Requests (Submit & Import Inbox JSON)",
                "4. Allocate (Run Deterministic Kernel)",
                "5. Results (Why-Traces & Conflict Analysis)",
                "6. Dashboard (Utilization & Bottlenecks)",
                "7. Replay (Validate Historical Ground Truth)",
                "8. Export (Offline Form HTML / CSV)",
                "9. Settings (Gemma LLM & Offline Paths)",
                "0. Exit",
            ]

            choice = questionary.select(
                "Navigate Tab / Screen:",
                choices=choices,
                style=BINSIDER_QUESTIONARY_STYLE,
                use_indicator=True,
            ).ask()

            if not choice or choice.startswith("0"):
                self.console.print("\n[bold #5af78e]Goodbye. Allocation session safely stored to disk.[/bold #5af78e]\n")
                break
            elif choice.startswith("1"):
                continue
            elif choice.startswith("2"):
                RoomsScreen(self.console, self.rooms, self.loader, self.occupancy).show()
            elif choice.startswith("3"):
                RequestsScreen(self.console, self.loader, self.pending_requests).show()
            elif choice.startswith("4"):
                AllocationScreen(
                    self.console,
                    self.rooms,
                    self.occupancy,
                    self.loader,
                    self.publisher,
                    self.narrator,
                    self.pending_requests,
                    self.last_result_holder,
                ).show()
            elif choice.startswith("5"):
                ResultsScreen(self.console, self.last_result_holder).show()
            elif choice.startswith("6"):
                DashboardScreen(self.console, self.rooms, self.occupancy).show()
            elif choice.startswith("7"):
                ReplayScreen(self.console, self.rooms, self.occupancy, self.loader).show()
            elif choice.startswith("8"):
                ExportScreen(self.console, self.rooms, self.occupancy).show()
            elif choice.startswith("9"):
                SettingsScreen(self.console, self.settings, self.narrator).show()

    def _render_binsider_dashboard(self) -> None:
        self.console.clear()

        # 1. Top Bar
        top_bar = render_top_bar(
            active_tab="General",
            context_path=f"week: {self.target_week} | OFFLINE",
        )
        self.console.print(top_bar)

        # 2. Main Framed Body
        hero_text = Text.from_markup(get_hero_banner())
        
        # System Specs
        room_types = {}
        for r in self.rooms.values():
            room_types[r.room_type] = room_types.get(r.room_type, 0) + 1
        room_desc = ", ".join([f"{v} {k}s" for k, v in sorted(room_types.items())]) or "120 Classrooms/Labs"

        specs_box = render_specs_box(
            campus_name="Central University · Main Campus",
            target_week=f"{self.target_week} to 2025-08-10",
            total_rooms=len(self.rooms),
            room_details=room_desc,
            indexed_slots="5,000 Classes · 1,800 Events",
            pending_count=len(self.pending_requests),
            engine_mode="Deterministic Hard Feasibility + Soft Scoring",
            auditor="Local Gemma-2B (Ollama - Zero Telemetry)",
        )

        # Submissions Queue
        queue_items = []
        if self.pending_requests:
            for req in self.pending_requests[:6]:
                pref_first = req.preferences[0].room_id if req.preferences else "Auto"
                queue_items.append({
                    "club": req.club,
                    "slot": f"{req.date[5:]} {req.start_hour:02d}:00 (+{req.duration_hours}h)",
                    "cap": f"{req.space_needed} units",
                    "assigned": pref_first,
                    "status": "[bold #5af78e]✓ QUEUED[/]",
                })
        else:
            queue_items = None

        queue_box = render_submissions_queue_box(queue_items)

        # Combine into master framed layout
        body_group = Group(
            hero_text,
            specs_box,
            Text(""),
            queue_box,
        )

        main_panel = make_framed_container(
            body_group,
            subtitle=render_footer_hotkeys("General"),
        )
        self.console.print(main_panel)
