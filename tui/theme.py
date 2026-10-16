from __future__ import annotations

from typing import List, Dict, Optional, Any
from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import RenderableType
import questionary

# Navigation Tabs matching the binsider layout
TABS = [
    ("1", "General"),
    ("2", "Rooms"),
    ("3", "Requests"),
    ("4", "Allocate"),
    ("5", "Results"),
    ("6", "Dashboard"),
    ("7", "Replay"),
    ("8", "Settings"),
]

# Custom questionary style matching binsider's dark monochrome + neon green highlights
BINSIDER_QUESTIONARY_STYLE = questionary.Style([
    ("qmark", "fg:#5af78e bold"),           # Neon green question mark
    ("question", "fg:#ffffff bold"),        # Crisp white question text
    ("answer", "fg:#5af78e bold"),          # Green selected answer
    ("pointer", "fg:#5af78e bold"),         # Green selector arrow
    ("highlighted", "fg:#000000 bg:#5af78e bold"), # Highlighted row
    ("selected", "fg:#5af78e"),             # Checked items
    ("separator", "fg:#6272a4"),            # Separator lines
    ("instruction", "fg:#888888 italic"),   # Hint text
    ("text", "fg:#f8f8f2"),                 # Standard input text
])


def render_top_bar(active_tab: str = "General", context_path: str = "/data/2025-08-04") -> Panel:
    """
    Renders the binsider-style top bar:
    ┌───────────────────────────┤ campus-allocator-v2.4 ├───...────────────────────────┐
    │ General │ Rooms │ Requests │ Allocate │ Results │ Dashboard │ Replay   /data/2025-08-04 │
    └───────────────────────────────────────────────────────────────────────────────────┘
    """
    # Build tab items
    tab_parts: List[str] = []
    for num, tab_name in TABS:
        if tab_name.lower() == active_tab.lower() or num == active_tab:
            tab_parts.append(f"[bold white on #262626] {tab_name} [/]")
        else:
            tab_parts.append(f"[dim white] {tab_name} [/]")

    tabs_str = " [dim]│[/dim] ".join(tab_parts)

    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=3)
    grid.add_column(justify="right", ratio=1)
    grid.add_row(tabs_str, f"[bold #5af78e]{context_path}[/]")

    return Panel(
        grid,
        title="[bold white] campus-allocator-v2.4 [/bold white]",
        title_align="center",
        box=box.SQUARE,
        border_style="bright_black",
        padding=(0, 1),
    )


def get_hero_banner() -> str:
    """
    Returns the pixel-styled ASCII logo for 'campus-allocator.' matching the binsider aesthetic,
    with the tagline 'Allocate campus space like a boss.' and project links.
    """
    # Compact, ultra-clean pixel letterforms that fit standard 80-120 terminal widths
    ascii_logo = """[bold white]  ___ __ _ _ __  _ __  _  _ ___   __ _| | |___  __ __ _| |_ ___ _ _   
 / __/ _` | '  \\| '_ \\| || (_-<  / _` | | / _ \\/ _/ _` |  _/ _ \\ '_|  
 \\___\\__,_|_|_|_| .__/\\_,_/__/   \\__,_|_|_\\___/\\__\\__,_|\\__\\___/_| [bold #5af78e].[/bold #5af78e] 
                |_|                                                   [/bold white]"""

    tagline = "[white]Allocate campus spaces [/white][bold #f1fa8c underline]like a boss.[/bold #f1fa8c underline]"
    repo = "[cyan]https://github.com/campus-space/allocator[/cyan]"
    author = r"[dim white]\[[dim]with[/dim] [bright_red]♥[/bright_red] [dim]by[/dim] [bold #8be9fd]@vit-ap[/bold #8be9fd] / [bold #8be9fd]student-council[/bold #8be9fd]][/dim white]"

    return f"\n{ascii_logo}\n\n          {tagline}\n\n          {repo}\n          {author}\n"


def render_specs_box(
    campus_name: str = "Central University · Main Campus",
    target_week: str = "2025-08-04 to 2025-08-10",
    total_rooms: int = 120,
    room_details: str = "88 Classrooms, 24 Labs, 8 Seminar Rooms",
    indexed_slots: str = "5,000 Classes · 1,800 Events",
    pending_count: int = 12,
    engine_mode: str = "Deterministic Feasibility + Soft Scoring",
    auditor: str = "Local Gemma-2B (Ollama - Zero Telemetry)",
) -> Panel:
    """
    Renders the metadata / file specs box, directly mimicking the top inner box from binsider.
    """
    table = Table.grid(padding=(0, 2), expand=True)
    table.add_column(style="dim white", width=16)
    table.add_column(style="bold white")

    table.add_row("Campus:", campus_name)
    table.add_row("Target Week:", f"[bold cyan]{target_week}[/bold cyan]")
    table.add_row("Total Rooms:", f"[bold #5af78e]{total_rooms}[/bold #5af78e] managed [dim]({room_details})[/dim]")
    table.add_row("Indexed Slots:", f"{indexed_slots} [dim](Single Occupancy Index)[/dim]")
    table.add_row("Requests Pool:", f"[bold #f1fa8c]{pending_count}[/bold #f1fa8c] submissions [dim](Inbox synced)[/dim]")
    table.add_row("Engine Core:", f"[green]{engine_mode}[/green]")
    table.add_row("Auditor:", f"[bold #8be9fd]{auditor}[/bold #8be9fd]")

    return Panel(
        table,
        box=box.SQUARE,
        border_style="bright_black",
        padding=(0, 2),
    )


def render_submissions_queue_box(sample_submissions: Optional[List[Dict[str, Any]]] = None) -> Panel:
    """
    Renders the lower box with 'Dependencies' styling from binsider,
    showing active club submissions, target slots, requested room/cap, assigned room (neon green), and status.
    """
    if sample_submissions is None:
        sample_submissions = [
            {"club": "Robotics Club", "slot": "Mon 13:00 - 15:00", "cap": "40 (6c/2t)", "assigned": "R120", "status": "[bold #5af78e]✓ APPROVED[/]"},
            {"club": "ACM Student Chapter", "slot": "Tue 15:00 - 17:00", "cap": "60 (Proj)", "assigned": "LAB-02", "status": "[bold #5af78e]✓ APPROVED[/]"},
            {"club": "Dance & Cultural Crew", "slot": "Wed 17:00 - 20:00", "cap": "80 (Aud)", "assigned": "AUD-1", "status": "[bold #5af78e]✓ APPROVED[/]"},
            {"club": "Debate Society", "slot": "Mon 14:00 - 16:00", "cap": "35 (Outlets)", "assigned": "CR204", "status": "[bold #f1fa8c]→ RELOCATED[/]"},
            {"club": "Drama & Theatre Guild", "slot": "Thu 18:00 - 21:00", "cap": "120 (Stage)", "assigned": "AUD-2", "status": "[bold #ff79c6]? EXCEPTION[/]"},
            {"club": "AI Research Group", "slot": "Fri 10:00 - 12:00", "cap": "45 (P+C)", "assigned": "LAB-01", "status": "[bold #5af78e]✓ APPROVED[/]"},
        ]

    table = Table(box=None, expand=True, padding=(0, 2), show_edge=False)
    table.add_column("Club / Submitter", style="bold white", ratio=3)
    table.add_column("Target Slot", style="dim white", ratio=2)
    table.add_column("Space", style="dim cyan", justify="right", ratio=1)
    table.add_column("Assigned", style="bold #5af78e", justify="center", ratio=1)
    table.add_column("Status", justify="right", ratio=2)

    for item in sample_submissions:
        table.add_row(
            item["club"],
            item["slot"],
            item["cap"],
            item["assigned"],
            item["status"],
        )

    return Panel(
        table,
        title="[bold white] Submissions Queue & Allocations [/bold white]",
        title_align="center",
        box=box.SQUARE,
        border_style="bright_black",
        padding=(0, 1),
    )


def render_footer_hotkeys(active_tab: str = "General") -> str:
    """
    Renders hotkey hints embedded inside the bottom border of the main outer frame.
    """
    return (
        r"[dim white]\[[/dim white]"
        "[bold #5af78e]Enter[/bold #5af78e][dim]→ Action[/dim]"
        r"[dim white]] \[[/dim white]"
        "[bold #8be9fd]1-8[/bold #8be9fd][dim]→ Jump Tab[/dim]"
        r"[dim white]] \[[/dim white]"
        "[bold #f1fa8c]a[/bold #f1fa8c][dim]→ Allocate[/dim]"
        r"[dim white]] \[[/dim white]"
        "[bold #bd93f9]v[/bold #bd93f9][dim]→ Trace[/dim]"
        r"[dim white]] \[[/dim white]"
        "[bold #50fa7b]d[/bold #50fa7b][dim]→ Dashboard[/dim]"
        r"[dim white]] \[[/dim white]"
        "[bold #ff5555]q[/bold #ff5555][dim]→ Quit[/dim]"
        r"[dim white]][/dim white]"
    )


def make_framed_container(
    content: RenderableType,
    subtitle: Optional[str] = None,
    border_style: str = "bright_black",
) -> Panel:
    """
    Wraps content inside the binsider single-line outer container with embedded bottom subtitle.
    """
    return Panel(
        content,
        subtitle=subtitle or render_footer_hotkeys(),
        subtitle_align="center",
        box=box.SQUARE,
        border_style=border_style,
        padding=(1, 2),
    )
