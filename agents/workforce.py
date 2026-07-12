import json
from agents.config import get_llm, is_live_mode

# Mock database of enrolled workers and local contractors (Thekedars) in the area
ENROLLED_THEKEDARS = [
    {
        "name": "Ramesh Sharma & Crew",
        "trade": "Masonry & Brickwork",
        "rating": 4.8,
        "location": "Sector 15 (Local)",
        "capacity_workers": 12,
        "daily_rate_per_worker_inr": 850,
        "status": "Available",
        "phone": "+91 98765 43210"
    },
    {
        "name": "Verma Electricals & Plumbing",
        "trade": "Electrical & Plumbing",
        "rating": 4.5,
        "location": "Central Hub",
        "capacity_workers": 6,
        "daily_rate_per_worker_inr": 750,
        "status": "Available",
        "phone": "+91 91234 56789"
    },
    {
        "name": "Sardar Drywall Specialists",
        "trade": "Drywall & Ceiling Work",
        "rating": 4.7,
        "location": "Industrial Area Phase 1",
        "capacity_workers": 8,
        "daily_rate_per_worker_inr": 900,
        "status": "Available",
        "phone": "+91 98123 45670"
    },
    {
        "name": "Om Tiles & Granite Crew",
        "trade": "Tiling & Flooring Work",
        "rating": 4.6,
        "location": "South Zone",
        "capacity_workers": 5,
        "daily_rate_per_worker_inr": 800,
        "status": "Available",
        "phone": "+91 97654 32109"
    },
    {
        "name": "Express Painting Services",
        "trade": "Painting, Fixtures & Clean-up",
        "rating": 4.9,
        "location": "Local East",
        "capacity_workers": 10,
        "daily_rate_per_worker_inr": 700,
        "status": "Busy",
        "notes": "Booked on a large retail project. Available from next week. Pre-booking required.",
        "phone": "+91 99887 76655"
    }
]

def match_workforce(required_trades, query=None):
    """
    Matches required trades to available workers or contractors from the enrolled database.
    """
    if is_live_mode():
        llm = get_llm()
        prompt = f"""
You are an expert Construction Labor Coordinator and Resource Manager.
Analyze the following required trades and match them against the database of enrolled regional contractors.

Required Trades:
{json.dumps(required_trades, indent=2)}

Enrolled Contractor Database:
{json.dumps(ENROLLED_THEKEDARS, indent=2)}

Match each required trade category to the best candidate from the database, ranking them.
Flag any scheduling availability conflicts.

Provide your response as a JSON object matching this schema:
{{
  "matches": [
    {{
      "trade_category": "Trade Name",
      "matched_contractor": "Contractor Name",
      "rating": rating_float,
      "daily_rate_inr": rate_integer,
      "status": "Available or Conflicted",
      "conflict_details": "Explanation of conflict if any, else empty",
      "match_justification": "Why this candidate fits this task"
    }}
  ],
  "workforce_summary": "Summary assessment of labor availability, costs, and key risks (like booking delays)."
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
            return json.loads(text.strip())
        except Exception as e:
            print(f"Error in Gemini Workforce matching: {str(e)}. Falling back to simulation.")

    # Simulation / Rule-Based Mode
    matches = []
    for trade in required_trades:
        # Match by finding a contractor whose trade matches or overlaps
        matched_crew = None
        for crew in ENROLLED_THEKEDARS:
            if trade.lower() in crew["trade"].lower():
                matched_crew = crew
                break
        
        if matched_crew:
            status = "Available"
            conflict_details = ""
            if matched_crew["status"] == "Busy":
                status = "Conflicted"
                conflict_details = f"Express Painters is currently busy on a retail site. Availability overlaps with our painting phase."
            
            matches.append({
                "trade_category": trade,
                "matched_contractor": matched_crew["name"],
                "rating": matched_crew["rating"],
                "daily_rate_inr": matched_crew["daily_rate_per_worker_inr"],
                "status": status,
                "conflict_details": conflict_details,
                "match_justification": f"Primary trade crew with rating {matched_crew['rating']} located in {matched_crew['location']}. Capacity of {matched_crew['capacity_workers']} workers."
            })
        else:
            matches.append({
                "trade_category": trade,
                "matched_contractor": "Generic Local Thekedar",
                "rating": 4.0,
                "daily_rate_inr": 800,
                "status": "Available",
                "conflict_details": "",
                "match_justification": "Fallback matching to local trade market list due to no enrolled database match."
            })
            
    summary = (
        "Labor matches completed. We have matched 5 primary contractors. "
        "A critical warning: Express Painting Services has an availability conflict. We must book them 1 week in advance, or source an alternative painter."
    )
    
    return {
        "matches": matches,
        "workforce_summary": summary
    }
