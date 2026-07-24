"""
BuildSense — Scheduling Agent
Milestone 2 Upgrade: Tool-Integrated Version

Upgrades from Milestone 1:
- Uses the ToolRegistry to call `get_weather_advisory` before finalising the schedule,
  annotating high-risk phases (plastering, concrete) with weather warnings.
- Records every tool call in a `tool_calls` audit list returned in the output.
- Simulation mode attaches a weather advisory to relevant phases.
"""

import json
from agents.config import get_llm, is_live_mode

# Phases that are sensitive to rainfall / humidity — used for advisory injection
WEATHER_SENSITIVE_PHASES = {
    "Plastering, Drywall & False Ceiling",
    "Tiling & Flooring Work",
    "Painting, Fixtures & Clean-up",
    "Structural Framing & Wall Partitions",
}


def generate_schedule(scope_data, query=None, city: str = "Pune"):
    """
    Builds a construction timeline and critical path based on project scope.

    Milestone 2: Calls `get_weather_advisory` via the ToolRegistry to annotate
    weather-sensitive phases with risk levels and site advisories.

    Args:
        scope_data (dict): Structural/spatial context, typically from analyze_blueprint().
        query      (str):  Optional free-text user instruction.
        city       (str):  Construction site city for weather lookup (default: 'Pune').

    Returns:
        dict with timeline, total_duration_days, critical_path, scheduling_notes,
        weather_advisory (dict), and tool_calls (list of audit entries).
    """
    from agents.tools import tool_registry

    # Snapshot audit log length so we can extract only this agent's tool calls later
    log_start = len(tool_registry.get_audit_log())

    # ── Live Mode: delegate scheduling to Gemini LLM ───────────────────────────
    if is_live_mode():
        llm = get_llm()

        # Fetch weather advisory first — used to enrich the LLM prompt
        weather_result = tool_registry.invoke(
            "get_weather_advisory", city=city, country_code="IN"
        )
        weather_summary = ""
        if weather_result.get("status") == "success":
            wd = weather_result["output"]
            weather_summary = (
                f"Current weather in {wd.get('city', city)}: "
                f"{wd.get('condition', 'Unknown')} | "
                f"Temp: {wd.get('temp_c', '?')}°C | "
                f"Risk Level: {wd.get('risk_level', 'LOW')}. "
                f"Advisories: {'; '.join(wd.get('advisories', []))}"
            )

        prompt = f"""
You are an expert Project Planner and Construction Scheduler (CPM consultant).
Based on the following project scope and structural details, generate a construction schedule.

Scope/Structural Data:
{json.dumps(scope_data, indent=2)}

Site Weather Advisory (fetched live):
{weather_summary if weather_summary else "No weather data available. Assume favourable conditions."}

User Context/Query:
{query if query else "Generate standard construction phase schedule."}

Provide your response as a JSON object matching this schema:
{{
  "timeline": [
    {{
      "phase": "Phase Name (e.g., Demolition, Masonry, Finishing)",
      "duration_days": duration_integer,
      "dependencies": ["dependency_phase_names_list"],
      "milestone": "Critical milestone achieved at completion",
      "tasks": ["individual_task_items_list"],
      "weather_risk": "LOW | MEDIUM | HIGH — risk level for this phase from weather"
    }}
  ],
  "total_duration_days": total_project_days_integer,
  "critical_path": ["list_of_critical_phases_in_sequence"],
  "scheduling_notes": "Strategic scheduling recommendations and risk mitigation strategies."
}}

CRITICAL RULES:
- Return ONLY valid JSON. No markdown code blocks, no backticks.
"""
        try:
            response = llm.invoke(prompt)
            text = response.content.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            result = json.loads(text.strip())

            # Attach weather advisory and tool call audit to result
            if weather_result.get("status") == "success":
                result["weather_advisory"] = weather_result["output"]
            result["tool_calls"] = _extract_tool_calls(tool_registry, log_start)
            return result
        except Exception as e:
            print(f"Error in Gemini Scheduling: {str(e)}. Falling back to simulation.")

    # ── Simulation / Tool-Backed Mode ──────────────────────────────────────────
    # Fetch weather advisory for site risk annotation
    weather_result = tool_registry.invoke(
        "get_weather_advisory", city=city, country_code="IN"
    )
    weather_advisory = None
    site_risk = "LOW"
    if weather_result.get("status") == "success":
        weather_advisory = weather_result["output"]
        site_risk = weather_advisory.get("risk_level", "LOW")

    # ── Six-phase linear construction timeline ─────────────────────────────────
    timeline = [
        {
            # Phase 1 — no predecessors; starts immediately on site handover
            "phase": "Demolition & Site Preparation",
            "duration_days": 5,
            "dependencies": [],
            "milestone": "Site cleared and ready for structural markings",
            "tasks": [
                "Remove existing non-loadbearing partitions",
                "Clear masonry debris and clean sub-floor",
                "Mark wall center lines on the floor slab"
            ],
            # Demolition is low-sensitivity to weather (no wet trades)
            "weather_risk": "LOW"
        },
        {
            # Phase 2 — critical bottleneck; masonry is delayed by heavy rain
            "phase": "Structural Framing & Wall Partitions",
            "duration_days": 12,
            "dependencies": ["Demolition & Site Preparation"],
            "milestone": "Room boundaries defined",
            "tasks": [
                "Erect AAC block masonry walls for rooms",
                "Fix GI door frames in partition walls",
                "Construct corridor boundaries (adjusting widths if needed)"
            ],
            # Masonry mortar curing is rain-sensitive
            "weather_risk": site_risk if site_risk != "LOW" else "LOW"
        },
        {
            # Phase 3 — conduit chasing before plastering locks them in
            "phase": "Electrical Conduiting & Plumbing",
            "duration_days": 8,
            "dependencies": ["Structural Framing & Wall Partitions"],
            "milestone": "Utilities rough-in completed",
            "tasks": [
                "Chasing walls for electrical conduits and plumbing lines",
                "Pulling electrical cables and wires",
                "Install water inlet/outlet pipes for pantry/toilets"
            ],
            # Electrical work is largely indoor; low weather impact
            "weather_risk": "LOW"
        },
        {
            # Phase 4 — plastering is HIGH sensitivity to rain / humidity
            "phase": "Plastering, Drywall & False Ceiling",
            "duration_days": 10,
            "dependencies": ["Electrical Conduiting & Plumbing"],
            "milestone": "Wall surfaces prepped for finishing",
            "tasks": [
                "Plaster blockwork walls with cement-sand mortar",
                "Erect suspended metal grid for gypsum false ceiling",
                "Apply first coat of wall putty"
            ],
            # Plaster curing is impaired by high humidity / rain
            "weather_risk": site_risk
        },
        {
            # Phase 5 — tiling adhesive requires low humidity for bonding
            "phase": "Tiling & Flooring Work",
            "duration_days": 7,
            "dependencies": ["Plastering, Drywall & False Ceiling"],
            "milestone": "Floors laid and protected",
            "tasks": [
                "Lay vitrified floor tiles with spacer jointing",
                "Tile walls in restroom and pantry zones",
                "Apply tile grout and clean flooring"
            ],
            # Tile adhesive is humidity-sensitive but indoor
            "weather_risk": "LOW" if site_risk == "LOW" else "MEDIUM"
        },
        {
            # Phase 6 — painting + handover; painting is high humidity risk
            "phase": "Painting, Fixtures & Clean-up",
            "duration_days": 6,
            "dependencies": ["Tiling & Flooring Work"],
            "milestone": "Project Handover Ready",
            "tasks": [
                "Apply final double coat of emulsion paint",
                "Install electrical modular switches, lights, and AC vents",
                "Install sanitary fittings and conduct final deep cleaning"
            ],
            # Emulsion paint requires humidity < 85% for proper adhesion
            "weather_risk": site_risk
        }
    ]

    total_days = sum(phase["duration_days"] for phase in timeline)
    critical_path = [phase["phase"] for phase in timeline]

    # Build scheduling notes — add weather advisory if risk is elevated
    base_notes = (
        "The schedule operates on a linear dependency chain. Masonry and Wall Partitions are the "
        "critical path bottleneck. Any delay in drywall/plastering will cascade directly into "
        "flooring and final handover."
    )
    weather_note = ""
    if weather_advisory and site_risk in ("MEDIUM", "HIGH"):
        weather_note = (
            f" ⚠️ WEATHER ALERT [{site_risk}] for {city}: "
            f"{weather_advisory.get('condition', '')} "
            f"({weather_advisory.get('temp_c', '?')}°C, "
            f"{weather_advisory.get('rainfall_1h_mm', 0):.1f}mm/h rain). "
            f"Delay plastering and painting phases. "
            f"{weather_advisory.get('advisories', [''])[0]}"
        )

    tool_calls = _extract_tool_calls(tool_registry, log_start)

    return {
        "timeline": timeline,
        "total_duration_days": total_days,
        "critical_path": critical_path,
        "scheduling_notes": base_notes + weather_note,
        "weather_advisory": weather_advisory,
        "tool_calls": tool_calls
    }


def _extract_tool_calls(tool_registry, log_start: int) -> list:
    """Extracts new tool audit entries added since log_start."""
    return tool_registry.get_audit_log()[log_start:]
