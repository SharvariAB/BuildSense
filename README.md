# BuildSense 🏗️
### AI Agent Coordination & Decision Engine for Construction Projects

BuildSense is a **multi-agent AI system** for Milestone 1 of the AI Agent Coordination & Decision Engine project. It deploys specialized AI agents orchestrated by a central Coordinator Agent to help civil engineers, architects, contractors, and builders make intelligent, explainable decisions across construction and renovation workflows.

---

## 🔁 System Flow

```
                   USER
                    │
          "Can I build this?"
                    │
                    ▼
          ┌─────────────────┐
          │ Coordinator      │
          │     Agent        │
          └──────┬──────────┘
                 │  Routes & Orchestrates
        ┌────────┼─────────────────┐
        ▼        ▼                 ▼
  ┌──────────┐ ┌──────────┐ ┌──────────────┐
  │ Blueprint│ │  Cost    │ │    Code      │
  │  Vision  │ │Estimator │ │  Compliance  │
  │  Agent   │ │  Agent   │ │    Agent     │
  └──────────┘ └──────────┘ └──────────────┘
        │        │                 │
        └────────┴─────────────────┘
                    │  Synthesizes findings
                    ▼
          ┌─────────────────┐
          │  Final Decision  │
          │  + Reasoning     │
          │    Trail         │
          └─────────────────┘
```

---

## 🤖 Agents in the System

| Agent | Responsibility |
|---|---|
| **Coordinator Agent** | Parses user query → routes tasks → resolves conflicts → synthesizes decision |
| **Blueprint Vision Agent** | Extracts rooms, corridors, exits, and dimensions from floor plan drawings |
| **Cost Estimation Agent** | Builds a Bill of Quantities (BOQ) and total estimate in INR |
| **Code Compliance Agent** | Validates layout against NBC 2016 (corridor widths, exit counts, setbacks) |
| **Scheduling Agent** | Constructs a phase-by-phase construction timeline with critical path |
| **Workforce Agent** | Matches required trades to local contractors and flags availability conflicts |

---

## 🏠 Real Example

> **Query:** *"Can we finish Phase 2 within a ₹15 lakh budget while staying compliant with fire safety norms?"*

**Step-by-step what happens:**
1. Coordinator routes to **Blueprint → Cost → Compliance** agents simultaneously
2. Blueprint Agent extracts: 2,400 sq ft, 4 rooms, 1 corridor (0.9m wide), 2 exits
3. Cost Agent estimates: **₹16.20 Lakh** total
4. Compliance Agent flags: Corridor A width **0.9m < 1.2m** (NBC Clause 4.3 — FAIL)
5. Coordinator synthesizes: *"Over budget by ₹1.2L AND Corridor A violates fire code. Do not proceed without redesign."*

---

## 📂 Project Structure

```
BuildSense/
├── agents/
│   ├── __init__.py           # Package exports
│   ├── config.py             # API key & LLM initialization
│   ├── coordinator.py        # 🧠 Coordinator + synthesis logic
│   ├── blueprint.py          # 👁️  Blueprint Vision Agent
│   ├── cost_estimation.py    # 💰 Cost Estimation Agent
│   ├── compliance.py         # ⚖️  Code Compliance Agent (NBC)
│   ├── scheduling.py         # 📅 Scheduling Agent
│   └── workforce.py          # 👷 Workforce Matching Agent
├── static/
│   ├── css/style.css         # Premium glassmorphic design
│   └── js/main.js            # Canvas, orchestration map, chat
├── templates/
│   └── index.html            # Dashboard SPA
├── app.py                    # Flask REST API server
├── requirements.txt          # Python dependencies
└── README.md
```

---

## ⚙️ Milestone 1 Task Mapping

| Milestone 1 Task | BuildSense Implementation |
|---|---|
| Configure LangChain + dependencies | `langchain-google-genai`, `google-genai` via pip; `agents/config.py` manages LLM |
| Develop foundational AI agents | Coordinator + Blueprint (highest novelty); all 6 agents implemented |
| Implement prompt templates | Drawing extraction prompt in `blueprint.py`; synthesis prompt in `coordinator.py` |
| Create basic testing interface | Full interactive Flask dashboard at `http://localhost:5000` |

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Configure Gemini API Key
Create a `.env` file:
```
GEMINI_API_KEY=your_key_here
```
Or enter it live in the dashboard UI. **Without a key, the app runs in Simulation Mode** using a high-fidelity built-in construction scenario — fully testable out of the box.

### 3. Run the Server
```bash
python app.py
```

### 4. Open the Dashboard
Navigate to **http://localhost:5000**

---

## 🧪 Testing Without an API Key (Simulation Mode)

1. Open the dashboard
2. Click **"Load Demo Renovations Blueprint"** — the schematic floor plan loads with annotated bounding boxes
3. Click the preset query chip: *"Can we finish Phase 2 within ₹15 lakh while compliant?"*
4. Watch the **Orchestration Map** light up agent-by-agent
5. Read the **Coordinator's synthesized recommendation** with the BOQ, NBC checks, timeline, and workforce matches

---

## 🧠 Key Design Decisions

- **Dual-Mode Architecture:** Live (Gemini Vision) and Simulation (rules-based) so the system is always demonstrable
- **Conflict-Aware Synthesis:** The Coordinator explicitly identifies when one finding overrides another (e.g., compliance fix raises cost above budget), rather than listing facts in isolation
- **Localized Compliance:** NBC 2016 Part 4 (fire safety) and Part 3 (setbacks) — targeting Indian construction context
- **Explainability:** Every agent's finding is surfaced individually in the UI alongside the synthesized verdict, so engineers can audit the reasoning trail

---

## 📦 Dependencies

```
flask==3.1.2
flask-cors==6.0.5
langchain==1.3.13
langchain-community==0.4.2
langchain-google-genai==4.2.7
google-genai==2.11.0
python-dotenv==1.2.2
pillow==10.4.0
pydantic==2.13.4
```

---

*BuildSense — Milestone 1: Agent Foundation Development*
