"""
BuildSense Tool Registry Package
Milestone 2: Tool Integration & Action Execution

Exports:
  - tool_registry: Shared ToolRegistry singleton used by all agents
  - Individual tool functions for direct import if needed
"""

from agents.tools.registry import ToolRegistry
from agents.tools.material_prices import get_material_price
from agents.tools.weather_api import get_weather_advisory
from agents.tools.nbc_lookup import lookup_nbc_rule
from agents.tools.json_report import generate_json_report

# Shared singleton registry — all agents import this instance
tool_registry = ToolRegistry()

# Register all enterprise tools
tool_registry.register(
    name="get_material_price",
    fn=get_material_price,
    description=(
        "Looks up current regional market prices for construction materials "
        "(cement, steel, aggregates, tiles, paint, AAC blocks) in INR per unit. "
        "Used by the Cost Estimation Agent to calculate accurate BOQ line items."
    ),
    input_schema={
        "material": "string — e.g. 'cement', 'steel_rebar', 'vitrified_tiles'",
        "region": "string — e.g. 'Pune', 'Mumbai', 'Delhi'",
        "quantity_units": "float — quantity in the material's standard unit"
    }
)

tool_registry.register(
    name="get_weather_advisory",
    fn=get_weather_advisory,
    description=(
        "Fetches current weather conditions for a construction site city using "
        "the OpenWeatherMap API. Returns temperature, rainfall, and a construction "
        "risk advisory (e.g. 'Do not pour concrete — heavy rain forecast')."
    ),
    input_schema={
        "city": "string — e.g. 'Pune', 'Mumbai'",
        "country_code": "string — ISO 3166-1 alpha-2, e.g. 'IN'"
    }
)

tool_registry.register(
    name="lookup_nbc_rule",
    fn=lookup_nbc_rule,
    description=(
        "Looks up the exact regulation text, minimum required values, and applicability "
        "notes for a given clause of the National Building Code of India (NBC 2016). "
        "Used by the Code Compliance Agent to provide precise, auditable citations."
    ),
    input_schema={
        "part": "string — e.g. 'Part 4', 'Part 3'",
        "clause": "string — e.g. '4.3', '4.2.1', '6.2'"
    }
)

tool_registry.register(
    name="generate_json_report",
    fn=generate_json_report,
    description=(
        "Serializes the full BuildSense pipeline result (BOQ, compliance audit, "
        "schedule, workforce matches, coordinator synthesis) into a timestamped JSON "
        "file saved in the reports/ directory. Returns a download URL."
    ),
    input_schema={
        "pipeline_result": "dict — the full result from run_coordination_pipeline()",
        "report_title": "string — descriptive title for the report"
    }
)

__all__ = [
    "tool_registry",
    "get_material_price",
    "get_weather_advisory",
    "lookup_nbc_rule",
    "generate_json_report",
]
