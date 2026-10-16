from __future__ import annotations

from typing import Dict, Any, Optional
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import questionary

from allocator.models import Room
from allocator.loader import DataLoader
from allocator.occupancy import OccupancyIndex
from ..theme import (
    render_top_bar,
    make_framed_container,
    BINSIDER_QUESTIONARY_STYLE,
)


class RoomsScreen:
    def __init__(self, console: Console, rooms: Dict[str, Room], loader: DataLoader, occupancy: OccupancyIndex) -> None:
        self.console = console
        self.rooms = rooms
        self.loader = loader
        self.occupancy = occupancy

    def show(self) -> None:
        while True:
            self.console.clear()
            self.console.print(render_top_bar(active_tab="Rooms", context_path="/data/rooms.csv"))

            content = Text.from_markup(
                "[bold white]Room Metadata Management[/bold white]\n"
                "[dim white]Add, inspect, edit classroom & laboratory constraints, and identify underutilized campus spaces.[/dim white]\n\n"
                f"Currently tracking [bold #5af78e]{len(self.rooms)}[/bold #5af78e] total rooms on disk."
            )
            self.console.print(make_framed_container(content, subtitle="[bold #5af78e]Enter[/bold #5af78e][dim]→ Select[/dim] | [bold #ff5555]Bksp/0[/bold #ff5555][dim]→ Back[/dim]"))

            choice = questionary.select(
                "Select Rooms Action:",
                choices=[
                    "1. List all rooms (120 entries)",
                    "2. List underused rooms (utilization < 25%)",
                    "3. Add new room",
                    "4. Edit existing room",
                    "0. Back to Main Menu",
                ],
                style=BINSIDER_QUESTIONARY_STYLE,
            ).ask()

            if not choice or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                self._list_rooms()
            elif choice.startswith("2"):
                self._list_underused_rooms()
            elif choice.startswith("3"):
                self._add_room()
            elif choice.startswith("4"):
                self._edit_room()

    def _list_rooms(self, room_filter: Optional[Dict[str, Room]] = None) -> None:
        self.console.clear()
        self.console.print(render_top_bar(active_tab="Rooms", context_path="/data/rooms.csv"))

        target_rooms = room_filter if room_filter is not None else self.rooms
        table = Table(
            title=f"Campus Rooms Directory ({len(target_rooms)} Total)",
            box=box.SQUARE,
            border_style="bright_black",
            header_style="bold white",
            expand=True,
        )
        table.add_column("Room ID", style="bold #5af78e")
        table.add_column("Building", style="bold white")
        table.add_column("Floor", justify="right", style="dim")
        table.add_column("Type", style="yellow")
        table.add_column("Capacity", justify="right", style="bold white")
        table.add_column("Projector", justify="center")
        table.add_column("Computers", justify="center")
        table.add_column("Accessible", justify="center")
        table.add_column("Outlets", justify="right", style="dim cyan")

        for r in sorted(target_rooms.values(), key=lambda x: (x.building, x.floor, x.room_id)):
            table.add_row(
                r.room_id,
                r.building,
                str(r.floor),
                r.room_type,
                str(r.capacity),
                "[green]✓[/green]" if r.projector else "[red]✗[/red]",
                "[green]✓[/green]" if r.computers else "[red]✗[/red]",
                "[green]✓[/green]" if r.accessible else "[red]✗[/red]",
                str(r.power_outlets),
            )

        self.console.print(make_framed_container(table, subtitle="[dim]Press Enter to return[/dim]"))
        questionary.press_any_key_to_continue(style=BINSIDER_QUESTIONARY_STYLE).ask()

    def _list_underused_rooms(self) -> None:
        underused: Dict[str, Room] = {}
        for r_id, r in self.rooms.items():
            util = self.occupancy.get_room_weekly_utilization(r_id, "2025-08-04")
            if util < 0.25:
                underused[r_id] = r

        self.console.print(f"[yellow]Found {len(underused)} rooms with average utilization < 25%:[/yellow]")
        self._list_rooms(underused)

    def _add_room(self) -> None:
        self.console.print("\n[bold #5af78e]Enter New Room Details:[/bold #5af78e]")
        rid = questionary.text("Room ID (e.g. R130):", style=BINSIDER_QUESTIONARY_STYLE).ask()
        if not rid or rid in self.rooms:
            self.console.print("[red]Invalid or duplicate Room ID.[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        building = questionary.text("Building name (e.g. Central):", default="Central", style=BINSIDER_QUESTIONARY_STYLE).ask()
        floor_str = questionary.text("Floor number:", default="1", style=BINSIDER_QUESTIONARY_STYLE).ask()
        room_type = questionary.select("Room Type:", choices=["Classroom", "Lecture Hall", "Seminar Room", "Computer Lab"], style=BINSIDER_QUESTIONARY_STYLE).ask()
        capacity_str = questionary.text("Seating capacity:", default="40", style=BINSIDER_QUESTIONARY_STYLE).ask()
        has_proj = questionary.confirm("Has projector?", default=True, style=BINSIDER_QUESTIONARY_STYLE).ask()
        has_comp = questionary.confirm("Has computers?", default=False, style=BINSIDER_QUESTIONARY_STYLE).ask()
        has_acc = questionary.confirm("Is wheelchair accessible?", default=True, style=BINSIDER_QUESTIONARY_STYLE).ask()
        outlets_str = questionary.text("Number of power outlets:", default="10", style=BINSIDER_QUESTIONARY_STYLE).ask()

        try:
            new_room = Room(
                room_id=rid.strip(),
                building=building.strip(),
                floor=int(floor_str),
                room_type=room_type,
                capacity=int(capacity_str),
                projector=bool(has_proj),
                computers=bool(has_comp),
                accessible=bool(has_acc),
                power_outlets=int(outlets_str),
            )
            self.rooms[new_room.room_id] = new_room
            self.loader.save_rooms(self.rooms)
            self.console.print(f"[bold #5af78e]✓ Room {new_room.room_id} added and saved to disk.[/bold #5af78e]")
        except Exception as e:
            self.console.print(f"[red]Error adding room: {e}[/red]")
        questionary.press_any_key_to_continue().ask()

    def _edit_room(self) -> None:
        if not self.rooms:
            self.console.print("[yellow]No rooms loaded.[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return

        room_choices = [f"{r.room_id} - {r.building} Floor {r.floor} ({r.room_type}, cap {r.capacity})" for r in sorted(self.rooms.values(), key=lambda x: x.room_id)]
        room_choices.append("Cancel")

        selection = questionary.select("Select room to edit:", choices=room_choices, style=BINSIDER_QUESTIONARY_STYLE).ask()
        if not selection or selection == "Cancel":
            return

        selected_id = selection.split(" ")[0].strip()
        room = self.rooms[selected_id]

        new_cap = questionary.text(f"Capacity [{room.capacity}]:", default=str(room.capacity), style=BINSIDER_QUESTIONARY_STYLE).ask()
        new_proj = questionary.confirm(f"Projector [{room.projector}]:", default=room.projector, style=BINSIDER_QUESTIONARY_STYLE).ask()
        new_comp = questionary.confirm(f"Computers [{room.computers}]:", default=room.computers, style=BINSIDER_QUESTIONARY_STYLE).ask()
        new_acc = questionary.confirm(f"Accessible [{room.accessible}]:", default=room.accessible, style=BINSIDER_QUESTIONARY_STYLE).ask()
        new_outlets = questionary.text(f"Power Outlets [{room.power_outlets}]:", default=str(room.power_outlets), style=BINSIDER_QUESTIONARY_STYLE).ask()

        try:
            room.capacity = int(new_cap)
            room.projector = bool(new_proj)
            room.computers = bool(new_comp)
            room.accessible = bool(new_acc)
            room.power_outlets = int(new_outlets)
            self.loader.save_rooms(self.rooms)
            self.console.print(f"[bold #5af78e]✓ Room {room.room_id} updated successfully.[/bold #5af78e]")
        except Exception as e:
            self.console.print(f"[red]Failed to update room: {e}[/red]")
        questionary.press_any_key_to_continue().ask()
