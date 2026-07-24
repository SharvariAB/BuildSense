"""
BuildSense — Coordinator & Decision Agent
Milestone 2 Upgrade: Tool Trace Aggregation

Upgrades from Milestone 1:
- After all specialist agents complete, collects every nested `tool_calls` list
  from their outputs and merges them into a single `tool_execution_trace`.
- Clears the shared ToolRegistry audit log at the start of each pipeline run
  so traces never bleed between requests.
- Passes tool trace as a first-class field in the returned pipeline result,
  making it available to the Flask API, UI, and JSON report generator.
"""

import json
from agents.config import get_llm, is_live_mode
from agents.blueprint import analyze_blueprint
from agents.cost_estimation import estimate_costs
from agents.compliance import check_compliance
from agents.scheduling import generate_schedule
from agents.workforce import match_workforce


def run_coordination_pipeline(image_path, user_query, budget_limit=None, site_city="Pune", region="Pune"):
    """
    Executes the multi-agent orchestration pipeline:
    1. Clears the shared tool registry audit log.
    2. Runs Blueprint Analysis on the image.
    3. Routes the query to relevant specialists.
    4. Aggregates outputs, identifies conflicts, and collects tool_execution_trace.
    5. Synthesises a final, explainable decision trail.

    Args:
        image_path   (str): Path to the uploaded floor plan image.
        user_query   (str): Free-text question from the user.
        budget_limit (int): Optional budget cap in INR for conflict detection.

    Returns:
        dict: Full pipeline result including:
            - routing_plan           (list[str])
            - spatial_data           (dict)
            - specialist_outputs     (dict)
            - conflicts_detected     (list[str])
            - tool_execution_trace   (list[dict])  ← NEW in Milestone 2
            - synthesized_recommendation (str)
    """
    from agents.tools import tool_registry

    # ── Reset tool registry audit log for a clean per-request trace ────────────
    # Without this, traces from previous requests would accumulate, making the
    # per-query tool_execution_trace inaccurate.
    tool_registry.clear_audit_log()

    # ── Step 1: Spatial extraction ──────────────────────────────────────────────
    spatial_data = analyze_blueprint(image_path)

    # ── Step 2: Specialist Routing ──────────────────────────────────────────────
    # Determine which specialists to invoke based on keywords in the user query.
    invoked_agents = ["Blueprint Analysis Agent"]
    query_lower = user_query.lower()

    run_cost       = any(x in query_lower for x in ["cost", "budget", "lakh", "price", "rupee", "money", "boq", "finish"])
    run_compliance = any(x in query_lower for x in ["compliant", "compliance", "norm", "byelaw", "code", "nbc", "safety", "fire", "exit", "width", "corridor"])
    run_schedule   = any(x in query_lower for x in ["schedule", "time", "date", "duration", "phase", "timeline", "milestone", "days"])
    run_workforce  = any(x in query_lower for x in ["labor", "worker", "contractor", "thekedar", "majdoor", "workforce", "team", "crew"])

    # General query → run all agents to demonstrate the full engine value
    if not (run_cost or run_compliance or run_schedule or run_workforce):
        run_cost = run_compliance = run_schedule = run_workforce = True

    specialist_outputs = {}

    # ── Step 3: Execute specialist agents ──────────────────────────────────────
    if run_cost:
        invoked_agents.append("Cost Estimation Agent")
        specialist_outputs["cost_estimation"] = estimate_costs(spatial_data, user_query, region=region)

    if run_compliance:
        invoked_agents.append("Code Compliance Agent")
        specialist_outputs["code_compliance"] = check_compliance(spatial_data, user_query)

    if run_schedule:
        invoked_agents.append("Scheduling Agent")
        specialist_outputs["scheduling"] = generate_schedule(spatial_data, user_query, city=site_city)

    if run_workforce:
        invoked_agents.append("Workforce Agent")
        required_trades = [
            "Masonry & Brickwork",
            "Electrical & Plumbing",
            "Tiling & Flooring Work",
            "Painting, Fixtures & Clean-up"
        ]
        specialist_outputs["workforce"] = match_workforce(required_trades, user_query)

    # ── Step 4: Aggregate tool_execution_trace from all specialist outputs ─────
    # Each agent that uses the ToolRegistry embeds a `tool_calls` list in its
    # return dict.  We also pull from the shared registry's session trace for
    # completeness (covers any calls not surfaced in individual `tool_calls`).
    tool_execution_trace = []
    seen_timestamps = set()

    # Collect from each specialist's embedded tool_calls list
    for agent_key, output in specialist_outputs.items():
        for call in output.get("tool_calls", []):
            ts = call.get("timestamp", "")
            if ts not in seen_timestamps:
                tool_execution_trace.append(call)
                seen_timestamps.add(ts)

    # Supplement with the full registry session trace (deduplication by timestamp)
    for entry in tool_registry.get_session_trace():
        ts = entry.get("timestamp", "")
        if ts not in seen_timestamps:
            tool_execution_trace.append(entry)
            seen_timestamps.add(ts)

    # Sort chronologically for the UI log view
    tool_execution_trace.sort(key=lambda e: e.get("timestamp", ""))

    # ── Step 5: Conflict Detection ─────────────────────────────────────────────
    conflicts = []

    if run_cost and budget_limit:
        est_cost = specialist_outputs["cost_estimation"]["total_cost_inr"]
        if est_cost > budget_limit:
            overrun = est_cost - budget_limit
            conflicts.append(
                f"Budget Overrun: Estimated project cost (₹{est_cost/100000:.2f}L) "
                f"exceeds limit (₹{budget_limit/100000:.2f}L) by ₹{overrun/100000:.2f}L."
            )

    if run_compliance:
        for check in specialist_outputs["code_compliance"]["compliance_checks"]:
            if check["status"] == "FAIL":
                conflicts.append(
                    f"NBC Code Violation: {check['rule']} is {check['found_value']} "
                    f"(Required: {check['required_value']}). Reference: {check['nbc_citation']}"
                )

    if run_workforce:
        for match in specialist_outputs["workforce"]["matches"]:
            if match["status"] == "Conflicted":
                conflicts.append(
                    f"Workforce Bottleneck: Matched team '{match['matched_contractor']}' "
                    f"is {match['status']} ({match['conflict_details']})"
                )

    # ── Step 6: Synthesised Decision Trail ─────────────────────────────────────
    if is_live_mode():
        llm = get_llm(temperature=0.3)
        prompt = f"""
You are the Coordinator & Decision Agent for BuildSense, a multi-agent AI system for construction and renovation.
Your task is to synthesize the findings of the specialist agents and provide a single, cohesive, explainable recommendation.
Resolve conflicts between the agents (e.g., if code violations require widening a corridor, explain how that adds to the cost and impacts the budget).

User Query: "{user_query}"
Budget Limit: {f"₹{budget_limit/100000:.2f} Lakh" if budget_limit else "Not specified"}

Specialist Outputs:
- Spatial Blueprint: {json.dumps(spatial_data, indent=2)}
- Cost Analysis: {json.dumps(specialist_outputs.get("cost_estimation", {}), indent=2)}
- Compliance Audit: {json.dumps(specialist_outputs.get("code_compliance", {}), indent=2)}
- Timeline Schedule: {json.dumps(specialist_outputs.get("scheduling", {}), indent=2)}
- Workforce Matches: {json.dumps(specialist_outputs.get("workforce", {}), indent=2)}

Detected Conflicts:
{json.dumps(conflicts, indent=2)}

Tool Execution Trace ({len(tool_execution_trace)} calls):
{json.dumps([{"tool": t.get("tool_name", t.get("tool")), "status": t.get("status")} for t in tool_execution_trace[:10]], indent=2)}

Write your final response in clear markdown format.
Structure your recommendation to include:
1. **Executive Summary & Verdict** (Direct answer: Can we proceed? Yes/No, why?)
2. **Specialist Insights Breakdown** (What each agent discovered)
3. **Conflict Resolution & Trade-offs** (Explain the interaction, e.g. how fixing the corridor width compliance violation affects the budget and partition sizing)
4. **Actionable Recommendations** (Step-by-step instructions on what changes the user should make to drawings or specifications)
"""
        try:
            response = llm.invoke(prompt)
            synthesis = response.content.strip()
        except Exception as e:
            print(f"Error in Coordinator synthesis: {str(e)}. Falling back to simulation.")
            synthesis = get_simulated_synthesis(user_query, budget_limit, spatial_data, specialist_outputs, conflicts)
    else:
        synthesis = get_simulated_synthesis(user_query, budget_limit, spatial_data, specialist_outputs, conflicts)

    return {
        "routing_plan": invoked_agents,
        "spatial_data": spatial_data,
        "specialist_outputs": specialist_outputs,
        "conflicts_detected": conflicts,
        "tool_execution_trace": tool_execution_trace,   # ← Milestone 2 addition
        "synthesized_recommendation": synthesis
    }


def get_simulated_synthesis(query, budget, spatial_data, specialist_outputs, conflicts):
    """Returns a pre-built synthesis for the canonical demo query or a generic fallback."""
    is_target_query = "15 lakh" in query or "15L" in query or ("15" in query and "compliant" in query.lower())

    if is_target_query:
        return """### ⚠️ Executive Summary & Verdict
**Verdict: DO NOT PROCEED with the current floor plan layout and budget parameters.**

Your project **cannot** be completed within the ₹15.00 Lakh budget while staying compliant with safety regulations. The project is currently facing a dual-constraint failure:
1. **Financial Overrun:** The base cost is estimated at **₹16.20 Lakh** (a ₹1.20 Lakh overrun).
2. **Safety Code Violation:** The main exit access pathway (**Corridor A**) measures **0.9 meters**, which violates the National Building Code (NBC) requirement of **1.2 meters**.

To resolve the safety violation, Corridor A must be widened by 0.3 meters. However, doing so will require demolishing and rebuilding the partition walls of Conference Room A and the Manager Office. This civil modification will add approximately **₹75,000** in labor and masonry materials, pushing the total estimated cost to **₹16.95 Lakh** (overrun of **₹1.95 Lakh**).

---

### 🔍 Specialist Insights Breakdown
*   **Blueprint Analysis Agent:** Extracted a total area of 2,400 sq ft. Identified two egress doors (Main Exit and Stairwell Exit) and Corridor A running between rooms. Noted a narrow corridor width of 0.9m.
*   **Cost Estimation Agent:** Computed a total of ₹16.20 Lakh using standard regional rates sourced via the Material Price Tool. Major cost drivers are Civil Masonry work (₹6.48 Lakh) and Flooring/Tiling (₹3.24 Lakh).
*   **Code Compliance Agent:** Flagged **Corridor A (Central Escape Route)** as **FAIL** (0.9m vs 1.2m minimum) citing *NBC 2016 Part 4, Clause 4.3*. Regulation fetched live via NBC Lookup Tool. Identified exits as passing.
*   **Scheduling Agent:** Calculated a timeline of **48 days** across 6 linear phases, highlighting that masonry works represent the critical path bottleneck. Weather advisory attached to plastering phase.
*   **Workforce Agent:** Matched 5 local contractors. Flagged an availability conflict for **Express Painting Services** (currently busy on another site).

---

### 🤝 Conflict Resolution & Trade-offs
*   **Compliance vs. Cost:** You cannot bypass the corridor safety code; doing so risks municipal rejection and fire hazards. However, widening Corridor A to 1.2m decreases the area of Conference Room A from 480 sq ft to 408 sq ft.
*   **Labor Overlap:** The schedule expects painting to start on Day 42, which coincides with the final days of the Express Painting crew's other active site. This could result in a 5-day delay in final handover if not pre-booked.

---

### 📋 Actionable Recommendations
1.  **Modify Room Partition Layout:** Instruct your draftsman/architect to shift the Conference Room partition wall inwards by 1.0 feet (0.3m). This will expand Corridor A to the compliant 1.2m width.
2.  **Offset Civil Costs:** To bring the budget back towards ₹15.00 Lakh, downgrade the flooring specifications in the conference room from premium vitrified tiles to standard tiles, saving an estimated ₹1.10 Lakh.
3.  **Secure Labor Booking:** Place a pre-booking deposit with *Express Painting Services* immediately to lock them in for Day 42, or request *Om Tiles* crew to handle auxiliary wall finishings to prevent timeline slippage.
"""

    # Generic synthesis fallback for other queries
    conflicts_str = "\n".join([f"- {c}" for c in conflicts]) if conflicts else "- No critical conflicts detected."

    return f"""### 📋 Executive Summary & Verdict
**Verdict: Project plan reviewed. Modest adjustments recommended.**

The decision engine has evaluated your request against current blueprints and database logs.

*   **Total Cost:** {specialist_outputs.get('cost_estimation', {}).get('formatted_total_cost', 'N/A')}
*   **Compliance Status:** {'⚠️ Non-Compliant' if conflicts else '✅ Compliant'}
*   **Total Duration:** {specialist_outputs.get('scheduling', {}).get('total_duration_days', 'N/A')} days

---

### 🔍 Identified Conflicts & Bottlenecks
{conflicts_str}

---

### 💡 Suggested Action Items
1. Review the flagged conflicts above.
2. If over budget, review premium material specifications and labor daily rates.
3. If code violations are present, update the architectural drawing according to the NBC citations.
"""
