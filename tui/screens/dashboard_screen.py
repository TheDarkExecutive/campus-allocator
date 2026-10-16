from __future__ import annotations

from typing import Dict, List, Tuple
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import questionary

from allocator.models import Room
from allocator.occupancy import OccupancyIndex
from ..theme import (
    render_top_bar,
    make_framed_container,
    BINSIDER_QUESTIONARY_STYLE,
)


class DashboardScreen:
    def __init__(self, console: Console, rooms: Dict[str, Room], occupancy: OccupancyIndex) -> None:
        self.console = console
        self.rooms = rooms
        self.occupancy = occupancy

    def show(self) -> None:
        self.console.clear()
        self.console.print(render_top_bar(active_tab="Dashboard", context_path="/analytics/utilization"))

        ref_week = "2025-08-04"

        # Calculate weekly utilization for all rooms
        room_utils: List[Tuple[str, float]] = []
        for rid in self.rooms.keys():
            u = self.occupancy.get_room_weekly_utilization(rid, ref_week)
            room_utils.append((rid, u))

        room_utils.sort(key=lambda x: x[1], reverse=True)
        top_used = room_utils[:5]
        underused = [x for x in reversed(room_utils) if x[1] >= 0.0][:5]

        # 1. Top 5 Most Used Rooms
        t1 = Table(
            title="Top 5 Heavily Utilized Rooms (Potential Campus Bottlenecks)",
            box=box.SQUARE,
            border_style="bright_black",
            header_style="bold white",
            expand=True,
        )
        t1.add_column("Room ID", style="bold #ff5555")
        t1.add_column("Building", style="bold white")
        t1.add_column("Type", style="yellow")
        t1.add_column("Cap", justify="right")
        t1.add_column("Utilization", justify="right", style="bold white")
        t1.add_column("ASCII Load Bar (8:00 - 20:00 Window)", style="bold #ff5555")

        for rid, util in top_used:
            r = self.rooms[rid]
            bar_len = int(util * 25)
            bar_ascii = "█" * bar_len + "░" * (25 - bar_len)
            t1.add_row(
                rid,
                r.building,
                r.room_type,
                str(r.capacity),
                f"{util*100.0:.1f}%",
                f"[{bar_ascii}]",
            )

        # 2. Top 5 Underused Rooms
        t2 = Table(
            title="Top 5 Underused Rooms (Expansion Candidates for Student Activities)",
            box=box.SQUARE,
            border_style="bright_black",
            header_style="bold white",
            expand=True,
        )
        t2.add_column("Room ID", style="bold #5af78e")
        t2.add_column("Building", style="bold white")
        t2.add_column("Type", style="yellow")
        t2.add_column("Cap", justify="right")
        t2.add_column("Utilization", justify="right", style="bold white")
        t2.add_column("ASCII Load Bar", style="bold #5af78e")

        for rid, util in underused:
            r = self.rooms[rid]
            bar_len = int(util * 25)
            bar_ascii = "█" * bar_len + "░" * (25 - bar_len)
            t2.add_row(
                rid,
                r.building,
                r.room_type,
                str(r.capacity),
                f"{util*100.0:.1f}%",
                f"[{bar_ascii}]",
            )

        # 3. Peak Hours Across Campus
        peak_hours = self.occupancy.get_peak_hours(ref_week)
        max_hour_slots = max([cnt for _, cnt in peak_hours]) if peak_hours else 1

        t3 = Table(
            title="Campus Peak Scheduling Hours Distribution",
            box=box.SQUARE,
            border_style="bright_black",
            header_style="bold white",
            expand=True,
        )
        t3.add_column("Hour Slot", style="bold white")
        t3.add_column("Occupied Room Slots", justify="right", style="cyan")
        t3.add_column("Demand Density Bar", style="bold #bd93f9")

        for h, count in sorted(peak_hours[:8], key=lambda x: x[0]):
            bar_len = int((count / max_hour_slots) * 30)
            bar_ascii = "■" * bar_len + "·" * (30 - bar_len)
            t3.add_row(
                f"{h:02d}:00 - {h+1:02d}:00",
                str(count),
                f"[{bar_ascii}]",
            )

        dashboard_group = Group(
            t1,
            Text(""),
            t2,
            Text(""),
            t3,
        )

        self.console.print(make_framed_container(dashboard_group, subtitle="[dim]Press Enter to return to main menu[/dim]"))
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()
