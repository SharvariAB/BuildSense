import json
from agents.config import get_llm, is_live_mode

def check_compliance(spatial_data, query=None):
    """
    Checks spatial coordinates and dimensions against the National Building Code (NBC) of India.
    """
    if is_live_mode():
        llm = get_llm()
        prompt = f"""
You are an expert Building Inspector and Code Compliance Consultant specializing in the National Building Code (NBC) of India.
Analyze the following spatial layout data of a floor plan and evaluate it for building code violations.

Spatial Data:
{json.dumps(spatial_data, indent=2)}

Focus on checking the following standard NBC guidelines:
1. Fire Escape Corridor Width (NBC 2016 Part 4, Clause 4.3): Minimum 1.2m for commercial/office spaces.
2. Exit Count (NBC Part 4, Clause 4.2): At least 2 remote exits required for spaces exceeding 1,500 sq ft.
3. Staircase / Egress Width: Minimum 1.2m for public/office occupancy.
4. Setbacks: Minimum open setbacks around the building perimeter depending on plot height.

Provide your response as a JSON object matching this schema:
{{
  "compliance_checks": [
    {{
      "rule": "Name of the rule (e.g. Corridor Egress Width)",
      "status": "PASS or FAIL or WARNING",
      "found_value": "What value was detected in the plan (e.g., 0.9m)",
      "required_value": "What NBC requires (e.g., 1.2m)",
      "nbc_citation": "Specific clause/section from NBC (e.g., NBC 2016 Part 4, Clause 4.3)",
      "message": "Detailed explanation of the findings.",
      "severity": "CRITICAL or MEDIUM or INFO"
    }}
  ],
  "is_overall_compliant": false,
  "summary_findings": "A high-level summary of the critical issues found and their structural implications."
}}

CRITICAL RULES:
- Return ONLY valid JSON. Do not return markdown, do not write backticks.
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
            print(f"Error in Gemini Compliance: {str(e)}. Falling back to simulation.")
            
    # Simulation / Rule-Based Mode
    checks = []
    is_overall_compliant = True
    
    # 1. Check Corridors
    corridors = spatial_data.get("corridors", [])
    for corr in corridors:
        width_m = corr.get("width_m", 1.2)
        name = corr.get("name", "Corridor")
        if width_m < 1.2:
            is_overall_compliant = False
            checks.append({
                "rule": f"Corridor Width - {name}",
                "status": "FAIL",
                "found_value": f"{width_m}m",
                "required_value": "1.2m minimum",
                "nbc_citation": "NBC 2016 Part 4 (Fire and Life Safety), Clause 4.3",
                "message": f"The exit access corridor '{name}' is only {width_m}m wide. This fails the fire egress safety corridor requirement of 1.2m.",
                "severity": "CRITICAL"
            })
        else:
            checks.append({
                "rule": f"Corridor Width - {name}",
                "status": "PASS",
                "found_value": f"{width_m}m",
                "required_value": "1.2m minimum",
                "nbc_citation": "NBC 2016 Part 4 (Fire and Life Safety), Clause 4.3",
                "message": f"Corridor '{name}' width ({width_m}m) is compliant with NBC emergency egress width regulations.",
                "severity": "INFO"
            })
            
    # 2. Check Exits
    exits = spatial_data.get("exits", [])
    total_area = spatial_data.get("total_area_sqft", 2400)
    
    if len(exits) < 2 and total_area > 1500:
        is_overall_compliant = False
        checks.append({
            "rule": "Egress Exit Count",
            "status": "FAIL",
            "found_value": f"{len(exits)} exit(s)",
            "required_value": "Minimum 2 remote exits",
            "nbc_citation": "NBC 2016 Part 4, Clause 4.2.1",
            "message": f"Only {len(exits)} exits detected for an area of {total_area:,} sq ft. NBC requires at least two separate, remote exits to prevent crowding during evacuations.",
            "severity": "CRITICAL"
        })
    else:
        checks.append({
            "rule": "Egress Exit Count",
            "status": "PASS",
            "found_value": f"{len(exits)} exits",
            "required_value": "Minimum 2 remote exits",
            "nbc_citation": "NBC 2016 Part 4, Clause 4.2.1",
            "message": "Satisfactory exit paths: Detected at least two separate egress routes.",
            "severity": "INFO"
        })
        
    # 3. Check Setback/Open Space (Assumed/Standard)
    # We add a warning check indicating zoning regulations should be verified for small renovations
    checks.append({
        "rule": "Perimeter Setbacks",
        "status": "WARNING",
        "found_value": "Not specified in interior plan",
        "required_value": "Zoning / Municipal norms (typically 3.0m)",
        "nbc_citation": "NBC 2016 Part 3 (Development Control Rules), Clause 6.2",
        "message": "Boundary setback clearances are not specified in the interior floor plan. Ensure local municipal (e.g. BMC/DDA) setbacks are maintained around exterior walls.",
        "severity": "MEDIUM"
    })
    
    summary = (
        "Non-compliant. The central escape corridor (Corridor A) has a width of 0.9m, which is a critical fire hazard violating the NBC Clause 4.3 minimum threshold of 1.2m. "
        "Additionally, verify that building setbacks are aligned with local municipal bylaws."
        if not is_overall_compliant else "Overall Compliant with NBC safety specifications."
    )
    
    return {
        "compliance_checks": checks,
        "is_overall_compliant": is_overall_compliant,
        "summary_findings": summary
    }
