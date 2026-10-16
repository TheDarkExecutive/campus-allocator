#!/usr/bin/env python3
"""
Campus Allocator — Main Terminal Application Entry Point.
Fully offline university room allocation system with numeric-menu TUI,
deterministic kernel matching, exception review queue, and per-club reports.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path for direct imports
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from tui.app import CampusAllocatorApp


def main() -> None:
    console = Console()
    try:
        app = CampusAllocatorApp(data_dir=str(PROJECT_ROOT / "data"))
        app.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Allocation session terminated by administrator.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Unexpected Application Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
