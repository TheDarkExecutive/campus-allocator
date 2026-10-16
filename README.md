# 🏛️ Campus Allocator (`campus-allocator`)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Offline-First](https://img.shields.io/badge/offline--first-100%25-brightgreen.svg?style=flat-square)](#-offline-first-guarantee)
[![Zero External APIs](https://img.shields.io/badge/external--apis-none-red.svg?style=flat-square)](#)
[![TUI Engine: Rich](https://img.shields.io/badge/TUI-Rich%20%2B%20Questionary-purple.svg?style=flat-square)](#)
[![Local Audit: Gemma LLM](https://img.shields.io/badge/Local%20Audit-Gemma--2B-cyan.svg?style=flat-square)](#)

```text
  ___ __ _ _ __  _ __  _  _ ___   __ _| | |___  __ __ _| |_ ___ _ _   
 / __/ _` | '  \| '_ \| || (_-<  / _` | | / _ \/ _/ _` |  _/ _ \ '_|  
 \___\__,_|_|_|_| .__/\_,_/__/   \__,_|_|_/\___/\__\__,_|\__\___/_| . 
                |_|  Allocate campus spaces like a boss.
```

> **"The campus has space. Students don't."**  
> A production-grade, deterministic, fully offline university room allocation engine featuring a retro `binsider`-style terminal UI, multi-source schedule normalizer, hard constraint feasibility filtering, mathematical soft scoring, human exception review queues, and local Gemma LLM verification.

---

## ⚡ Quickstart (Running in Under 60 Seconds)

### 📦 Pre-bundled Virtual Environment (`venv.zip`)

> [!IMPORTANT]
> **No Internet or Pip Needed!**  
> To guarantee **100% offline deployment** on air-gapped university laptops, the complete pre-configured virtual environment with all required packages (`rich`, `questionary`, `pandas`, `python-dateutil`) is zipped in the repository as **`venv.zip`**.

#### 1. Unzip `venv.zip`
Open PowerShell in the project directory and extract:
```powershell
Expand-Archive -Path venv.zip -DestinationPath .
```
*(Or right-click `venv.zip` in Windows Explorer and select **Extract All...** directly into this folder).*

#### 2. Run the Application Directly
You don't even need to activate the environment — run with the bundled Python binary:
```powershell
.\venv\Scripts\python main.py
```

---

### 🔧 Alternative: Fresh Setup from Scratch (Without `venv.zip`)

If you prefer to build your own clean environment using `requirements.txt`:

```powershell
# 1. Create a fresh virtual environment
python -m venv venv

# 2. Allow script execution in PowerShell (if disabled)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 3. Activate the environment
.\venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
python main.py
```

> [!TIP]
> **PowerShell Script Execution Error?**  
> If Windows displays `Activate.ps1 cannot be loaded because running scripts is disabled on this system`, either run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once, or bypass activation entirely by executing `.\venv\Scripts\python main.py`.

---

## 🔒 Offline-First Guarantee

The system is decoupled into two halves that **never share a network, server, database, or socket**:

```
                 STUDENT SIDE (Online at Submit Time)
              ┌─────────────────────────────────────────┐
              │      Custom HTML Reservation Form       │
              │  - Live pre-flight feasibility math     │
              │  - Space = Attendees + Ch + 3 * Tbl     │
              │  - Clubs self-correct before submit     │
              └────────────────────┬────────────────────┘
                                   │ Exports JSON
                                   ▼
                 HANDOFF FILE (`inbox/<week>/*.json`)
                                   │
                                   ▼
                ADMIN SIDE (Offline Laptop Terminal Kernel)
┌────────────────────────────────────────────────────────────────────────┐
│ campus-allocator (Binsider Retro TUI)                                   │
│                                                                        │
│ 1. Occupancy Matrix     ──> Single index keyed by (room_id, date, hour)│
│ 2. Club Quota Enforcer  ──> 1 active slot/club/week; excess deferred   │
│ 3. Feasibility Filter   ──> Capacity, Projector, Computers, Clashes    │
│ 4. Soft Scorer          ──> Fit penalty, Facilities, Utilization, Pref │
│ 5. Deterministic Kernel ──> Phase 1 Auto-Resolve                       │
│ 6. Exception Queue      ──> Phase 2 Admin Escalation Review            │
│ 7. Local Gemma LLM Pass ──> Audits results.json & generates flags.md   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Writes Output Files
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ results/<week>/results.json   ──> Verifiable rule trace for every match│
│ results/<week>/flags.md       ──> Tight fits & contested slot warnings │
│ results/<week>/summary.txt    ──> Human-readable status breakdown      │
│ reports/<week>/<club>.md      ──> Per-club Markdown allocation notices │
│ deferred/<week>/<req_id>.json ──> Rolled forward to next cycle         │
└────────────────────────────────────────────────────────────────────────┘
```

- **Zero Cloud / Zero External APIs**: No reliance on third-party servers, SaaS platforms, or fragile websockets.
- **No Lost Emails**: Official per-club allocation notices are written directly to markdown files on disk.
- **Explainable Decisions**: Every single assignment carries a complete rule trace (`--why`) explaining capacity fit, equipment match, schedule clash avoidance, and score breakdown.

---

## 🖥️ Binsider-Inspired Terminal UI

The TUI is built on a responsive multi-tab container modeled after the Unix `binsider` utility:

```text
┌───────────────────────────┤ campus-allocator-v2.4 ├───────────────────────────┐
│ [ General ] │ Rooms │ Requests │ Allocate │ Results │ Dashboard │ Replay   /data/2025-08-04 │
└───────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────┐
│   Campus:        Central University · Main Campus                             │
│   Target Week:   2025-08-04 to 2025-08-10                                     │
│   Total Rooms:   120 managed (88 Classrooms, 24 Labs, 8 Seminar Rooms)        │
│   Indexed Slots: 5,000 Classes · 1,800 Events (Single Occupancy Index)        │
│   Requests Pool: 12 submissions (Inbox synced)                                │
│   Engine Core:   Deterministic Hard Feasibility + Soft Scoring                │
│   Auditor:       Local Gemma-2B (Ollama - Zero Telemetry)                     │
└───────────────────────────────────────────────────────────────────────────────┘

┌──────────────── Submissions Queue & Allocations ──────────────────────────────┐
│ Club                   Slot              Space   Assigned   Status            │
│ Robotics Club          Mon 13:00 - 15:00 40 (6c) R120       ✓ APPROVED        │
│ ACM Student Chapter    Tue 15:00 - 17:00 60 (P)  LAB-02     ✓ APPROVED        │
│ Dance & Cultural Crew  Wed 17:00 - 20:00 80 (Aud)AUD-1      ✓ APPROVED        │
│ Debate Society         Mon 14:00 - 16:00 35 (Out)CR204      → RELOCATED       │
│ Drama & Theatre Guild  Thu 18:00 - 21:00 120(Aud)AUD-2      ? EXCEPTION       │
│ AI Research Group      Fri 10:00 - 12:00 45 (Lab)LAB-01     ✓ APPROVED        │
└───────────────────────────────────────────────────────────────────────────────┘
└── [Enter→ Action] [1-8→ Jump Tab] [a→ Allocate] [v→ Trace] [d→ Dashboard] [q→ Quit] ──┘
```

### Navigation Map

| Key / Number | Screen / Tab | Purpose |
| :---: | :--- | :--- |
| **`1`** | **General** | Live system specs, room counts, and active inbox queue overview |
| **`2`** | **Rooms** | Search 120 rooms, inspect capacity/projector/wheelchair specs, find underutilized rooms (<25%) |
| **`3`** | **Requests** | Import weekly club requests from `inbox/<week>/*.json` or enter urgent requests |
| **`4`** | **Allocate** | Run deterministic kernel, handle tiebreakers, and resolve edge cases in Exception Queue |
| **`5`** | **Results** | Inspect why-traces (`--why`), rule audit trails, and relocation explanations |
| **`6`** | **Dashboard** | View ASCII utilization bars, room bottlenecks, and peak scheduling hours |
| **`7`** | **Replay** | Validate the kernel against 5,000 historical ground-truth university outcomes |
| **`8`** | **Export** | Generate offline HTML student request forms and blank CSV templates |
| **`9`** | **Settings** | Configure Ollama local endpoint, Gemma model name, and reports folder |
| **`0`** | **Exit** | Gracefully save runtime state and exit |

---

## 📐 Mathematical Scoring & Allocation Model

Every room candidate that satisfies **all hard constraints** (capacity, projector, computers, accessibility, and zero schedule clash) is ranked via a multi-objective scoring function:

$$\text{score} = -0.45 \cdot \left(\frac{|\text{capacity} - \text{spaceNeeded}|}{200}\right) + 0.25 \cdot \text{facilitiesMatch} + 0.20 \cdot (1 - \text{utilization}) + 0.10 \cdot \text{preferenceBonus}$$

### Parameters Breakdown:
1. **Effective Space Needed**:
   $$\text{spaceNeeded} = \text{expectedAttendance} + \text{extraChairs} + 3 \cdot \text{extraTables}$$
2. **Weekly Occupancy Utilization**:
   $$\text{utilization} = \min\left(1.0, \frac{\text{busyHours}(\text{room}, \text{date})}{12.0}\right)$$
   *(Evaluated across the standard 08:00 to 20:00 academic window)*
3. **Preference Weight Bonus**:
   - **Rank 1 Preference**: `+1.0`
   - **Rank 2 Preference**: `+0.6`
   - **Rank 3 Preference**: `+0.3`
   - **Fallback / Alternative**: `0.0`
4. **Deterministic Tie-Breaking Cascade**:
   - **Purpose Priority**: `Exam (4)` > `Faculty (3)` > `Club Event (2)` > `Study Group (1)`
   - **Submission Timestamp**: Earlier timestamp wins contested slots.
   - **Lexical Request ID**: Final immutable tiebreaker.

---

## 🗂️ Project Directory Structure

```
campus-allocator/
├── allocator/               # Core business logic & algorithms
│   ├── models.py            # Dataclasses: Room, Schedule, Event, Request, Decision
│   ├── loader.py            # CSV & JSON resilient file parsers
│   ├── occupancy.py         # Multi-source time normalizer & occupancy matrix
│   ├── feasibility.py       # Hard constraints filtering & clash checks
│   ├── scoring.py           # Multi-factor mathematical scoring engine
│   ├── kernel.py            # Multi-stage deterministic allocation pass
│   ├── exceptions.py        # Exception review queue escalation triggers
│   ├── explain.py           # Deterministic rule trace (--why) builder
│   ├── llm.py               # Local Gemma/Ollama narration layer (zero-telemetry)
│   ├── reports.py           # Markdown, JSON, summary.txt, and HTML exporters
│   └── replay.py            # Historical benchmark replay validator
├── tui/                     # Binsider-inspired terminal interface
│   ├── theme.py             # Top tab bar, ASCII art, specs & queue widgets
│   ├── app.py               # Master TUI orchestrator & hotkey router
│   └── screens/             # Dedicated screens (Rooms, Requests, Allocate, etc.)
├── data/                    # Production campus datasets
│   ├── rooms.csv            # 120 rooms across 5 campus buildings
│   ├── class_schedule.csv   # 5,000 academic course slots
│   ├── events.csv           # 1,800 scheduled campus events
│   ├── room_requests.csv    # 5,000 historical labeled requests for replay
│   └── generate_sample_data.py # Dataset generator utility
├── inbox/                   # Weekly submission handoff directory
│   └── 2025-08-03/          # Sample club JSON request files
├── results/                 # Machine-readable output traces & flags.md
├── reports/                 # Per-club Markdown notices
├── deferred/                # Excess club requests rolled over to next cycle
├── forms/                   # Standalone offline student HTML forms
├── tests/                   # Full offline unit test suite
├── main.py                  # CLI application entrypoint
├── requirements.txt         # Package dependencies
├── venv.zip                 # Pre-bundled offline virtual environment
└── README.md                # System documentation
```

---

## 🧪 Testing & Validation

Run the complete test suite completely offline:
```powershell
.\venv\Scripts\python -m unittest discover tests
```

Tests cover:
- ✅ Normalized `(room_id, date, hour)` occupancy collision detection
- ✅ Hard constraint feasibility filters (capacity, tables, projectors, accessibility)
- ✅ Mathematical soft scoring, fit penalties, and tiebreaker consistency
- ✅ Multi-club weekly quota enforcement (1 active slot / week)
- ✅ Admin exception review queue resolution and override audit trails

---
##Some screenshots!
<img width="1917" height="1021" alt="image" src="https://github.com/user-attachments/assets/ab8cc59c-6d07-4336-b525-a4d480e034ff" />
<img width="1917" height="538" alt="image" src="https://github.com/user-attachments/assets/9064be9b-8779-4489-88bb-3465d1153f7e" />
<img width="1917" height="1022" alt="image" src="https://github.com/user-attachments/assets/44fdd32d-8727-4770-b997-b0cdf1d2864a" />
<img width="1917" height="678" alt="image" src="https://github.com/user-attachments/assets/8400e654-78d0-4a07-b8d6-fee5cfcab995" />


## 👥 Credits & Authors

Built with ♥ by **Joash Biji** ([@TheDarkExecutive](https://github.com/TheDarkExecutive))  
*VIT-AP University · Student Council & Data Science Club*  
Special thanks to the open-source community behind `ratatui` and `binsider` for the UI inspiration.
