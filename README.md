# Campus Allocator (`campus-allocator`)

A production-grade, fully offline campus room allocation system designed for university faculty administrators and club coordinators.

> **Offline-First Guarantee**: Runs 100% locally on a laptop without internet, cloud databases, external APIs, websockets, or email dependencies. Connected strictly via JSON handoff files.

---

## 1. System Architecture

```
                       STUDENT SIDE (Online at Submit)
                    ┌───────────────────────────────────┐
                    │ Custom HTML Reservation Form       │
                    │ - Live pre-flight feasibility math│
                    │ - Space = Attendees + Ch + 3*Tbl  │
                    └─────────────────┬─────────────────┘
                                      │ Exports JSON
                                      ▼
                        HANDOFF FILE (inbox/<week>/*.json)
                                      │
                                      ▼
                       ADMIN SIDE (Offline Laptop Kernel)
 ┌────────────────────────────────────────────────────────────────────────┐
 │ campus-allocator (TUI)                                                 │
 │                                                                        │
 │ 1. Occupancy Normalizer  ──> Keyed by (room_id, ISO_date, hour)        │
 │ 2. Club Cap Enforcer     ──> 1 active request/club/week; rest deferred │
 │ 3. Feasibility Filter    ──> Capacity, Projector, Computers, Clashes   │
 │ 4. Soft Scorer           ──> Fit penalty, Facilities, Utilization, Pref│
 │ 5. Deterministic Kernel  ──> Phase 1 Auto-Resolve                      │
 │ 6. Exception Queue       ──> Phase 2 Admin Escalation Review           │
 │ 7. Local Gemma LLM Pass  ──> Audits results.json & generates flags.md  │
 └────────────────────────────────────┬───────────────────────────────────┘
                                      │ Writes Output Files
                                      ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ results/<week>/results.json  ──> Structured audit trace for every match│
 │ results/<week>/flags.md      ──> Tight fits & contested slot warnings  │
 │ results/<week>/summary.txt   ──> Human-readable status breakdown       │
 │ reports/<week>/<club>.md     ──> Per-club Markdown allocation notice   │
 │ deferred/<week>/<req_id>.json──> Rolled forward to next cycle          │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Mathematical Scoring Model

For every feasible room candidate meeting all hard constraints:

$$\text{score} = -0.45 \cdot \left(\frac{|\text{capacity} - \text{space\_needed}|}{200}\right) + 0.25 \cdot \text{facility\_match\_ratio} + 0.20 \cdot (1 - \text{utilization}) + 0.10 \cdot \text{preference\_bonus}$$

- **Space Needed**: $\text{expected\_attendance} + \text{extra\_chairs} + 3 \cdot \text{extra\_tables}$
- **Utilization**: $\frac{\text{busy\_hours}(\text{room}, \text{date})}{12.0}$ clamped to $[0, 1]$ in the 8:00–20:00 window.
- **Preference Bonus**:
  - Rank 1 preference: `1.0`
  - Rank 2 preference: `0.6`
  - Rank 3 preference: `0.3`
  - No preference / fallback: `0.0`

### Deterministic Tie-Break Order:
1. **Purpose Priority**: `Exam` (4) > `Faculty` (3) > `Club` (2) > `Study` (1)
2. **Submission Timestamp**: Earlier submission timestamp wins.
3. **Request ID**: Lexical tie-break fallback.

---

## 3. Directory Layout

```
campus-allocator/
├── allocator/
│   ├── __init__.py
│   ├── models.py        # Dataclasses: Room, Class, Event, Request, Decision
│   ├── loader.py        # CSV and JSON robust data loaders
│   ├── occupancy.py     # Multi-source time normalizer & occupancy index
│   ├── feasibility.py   # Hard constraints feasibility filter
│   ├── scoring.py       # Soft scoring & tiebreaker ranking engine
│   ├── kernel.py        # Deterministic multi-stage allocation pass
│   ├── exceptions.py    # Anomaly detection & escalation triggers
│   ├── explain.py       # Human-readable rule trace (--why) builder
│   ├── llm.py           # Local Gemma/Ollama narration layer & fallback
│   ├── reports.py       # Markdown, JSON, summary, and HTML writers
│   └── replay.py        # Historical ground-truth outcome validator
├── tui/
│   ├── __init__.py
│   ├── app.py           # Rich + Questionary interactive TUI application
│   └── screens/         # Screens 1 through 9
├── data/
│   ├── rooms.csv            # 120 campus rooms across 5 buildings
│   ├── class_schedule.csv   # 5,000 course slots
│   ├── events.csv           # 1,800 university events
│   └── room_requests.csv    # 5,000 historical labeled requests
├── inbox/
│   └── 2025-08-03/          # JSON submission files from student clubs
├── results/                 # results.json, flags.md, summary.txt
├── reports/                 # Per-club markdown notices
├── deferred/                # Roll-forward JSON requests exceeding club cap
├── forms/                   # Exported HTML forms and CSV templates
├── tests/                   # Complete unit test suite
├── main.py                  # CLI Entry point
├── requirements.txt         # Dependencies: rich, questionary, pandas, python-dateutil
└── README.md
```

---

## 4. Setup & Execution

### Prerequisites
- Python 3.11+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Running the Terminal Application
```bash
python main.py
```

### Running Unit Tests
```bash
python -m unittest discover tests
```
All unit tests execute offline without network dependencies.
