"""Controlled autonomous analyst: LLM planning, deterministic Pandas execution."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from src.llm.base import LLMProviderError
from src.llm.factory import get_llm_provider, get_llm_provider_label, get_llm_timeout
from src.data_query_engine import query_dataset
from src.dataset_profiler import profile_dataset
from src.date_analysis import monthly_summary


MAX_TOOL_STEPS = 8
PLANNER_TIMEOUT_CAP_SECONDS = 12
NARRATIVE_TIMEOUT_CAP_SECONDS = 5
ALLOWED_TOOLS = {
    "dataset_profile", "aggregate", "group_by", "top_n", "bottom_n", "missing_values",
    "duplicate_check", "correlation", "descriptive_statistics", "time_series_summary", "category_analysis",
}
ALLOWED_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count"}
COMPLEX_INTENT_TERMS = (
    "why", "driver", "driving", "root cause", "explain", "pattern", "trend",
    "factor", "factors", "responsible", "difference",
)


class PlanValidationError(ValueError):
    """Raised when an LLM plan is structurally unsafe or incompatible with a dataset."""


@dataclass(frozen=True)
class AnalysisStep:
    tool: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VisualizationRecommendation:
    needed: bool = False
    chart_type: str = "table"
    x: str | None = None
    y: str | None = None
    group_by: str | None = None
    title: str = "Analysis result"
    filters: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnalysisPlan:
    question: str
    intent: str
    required_columns: list[str]
    steps: list[AnalysisStep]
    expected_output: str
    visualization: VisualizationRecommendation = field(default_factory=VisualizationRecommendation)


def _json_object(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}") + 1
    if start < 0 or end <= start:
        raise PlanValidationError("Planner did not return a JSON object.")
    try:
        value = json.loads(text[start:end])
    except json.JSONDecodeError as error:
        raise PlanValidationError("Planner returned malformed JSON.") from error
    if not isinstance(value, dict):
        raise PlanValidationError("Planner JSON must be an object.")
    return value


def _plan_from_dict(value: dict[str, Any], question: str) -> AnalysisPlan:
    raw_steps = value.get("steps")
    if not isinstance(raw_steps, list):
        raise PlanValidationError("Plan requires a steps list.")
    steps = []
    for raw in raw_steps:
        if not isinstance(raw, dict) or not isinstance(raw.get("tool"), str):
            raise PlanValidationError("Each step requires a tool name.")
        parameters = raw.get("parameters", {})
        if not isinstance(parameters, dict):
            raise PlanValidationError("Tool parameters must be an object.")
        steps.append(AnalysisStep(raw["tool"], parameters))
    visual = value.get("visualization") or {}
    return AnalysisPlan(
        question=value.get("question", question), intent=str(value.get("intent", "analysis")),
        required_columns=list(value.get("required_columns", [])), steps=steps,
        expected_output=str(value.get("expected_output", "Deterministic analysis result.")),
        visualization=VisualizationRecommendation(
            needed=bool(visual.get("needed", False)), chart_type=str(visual.get("chart_type", "table")),
            x=visual.get("x"), y=visual.get("y"), group_by=visual.get("group_by"),
            title=str(visual.get("title", "Analysis result")),
            filters=list(visual.get("filters", [])) if isinstance(visual.get("filters", []), list) else [],
        ),
    )


def _planner_response(columns: list[dict[str, Any]], question: str) -> str:
    """Request a compact JSON plan and retry once with an even smaller prompt."""
    column_summary = "; ".join(
        f"{column['name']}: {'numeric' if column['numeric'] else 'categorical'}" for column in columns
    )
    prompts = (
        f"""Return ONLY JSON. No Markdown or explanation.
Schema: {{"steps":[{{"tool":"group_by","parameters":{{"group_by":"...","metric":"...","aggregation":"sum"}}}}]}}
Columns: {column_summary}
Allowed tool: group_by. Question: {question}""",
        """Return ONLY JSON matching this schema. No Markdown. No explanation.
{"steps":[{"tool":"group_by","parameters":{"group_by":"region","metric":"profit","aggregation":"sum"}}]}""",
    )
    planner_timeout = min(get_llm_timeout(), PLANNER_TIMEOUT_CAP_SECONDS)
    errors: list[Exception] = []
    for prompt in prompts:
        try:
            response = get_llm_provider().generate_plan(prompt, timeout=planner_timeout)
            _json_object(response)
            return response
        except (LLMProviderError, PlanValidationError) as error:
            errors.append(error)
    final_error = errors[-1]
    details = f"failure_type=provider_or_plan_parse; diagnostic={final_error}"
    raise PlanValidationError(f"Planner failed after one retry: {details}") from final_error


def _fallback_analysis_plan(df: pd.DataFrame, question: str) -> AnalysisPlan | None:
    """Return a safe plan only for supported regional profitability questions."""
    normalized_question = question.lower()
    required_columns = {"region", "profit"}
    if "why" not in normalized_question or "region" not in normalized_question or not required_columns.issubset(df.columns):
        return None
    steps = [AnalysisStep("group_by", {"group_by": "region", "metric": "profit", "aggregation": "sum"})]
    if "revenue" in df.columns:
        steps.append(AnalysisStep("group_by", {"group_by": "region", "metric": "revenue", "aggregation": "sum"}))
    return AnalysisPlan(
        question=question,
        intent="regional profitability investigation",
        required_columns=sorted(required_columns),
        steps=steps,
        expected_output="Validated regional profit and revenue evidence.",
    )


def create_analysis_plan(df: pd.DataFrame, question: str) -> AnalysisPlan:
    """Ask Ollama for a constrained JSON plan; it cannot execute code or SQL."""
    columns = [{"name": str(c), "numeric": bool(pd.api.types.is_numeric_dtype(df[c]))} for c in df.columns]
    try:
        response = _planner_response(columns, question)
    except PlanValidationError:
        fallback = _fallback_analysis_plan(df, question)
        if fallback is not None:
            return fallback
        raise
    if response.startswith("❌"):
        raise PlanValidationError(response)
    return _plan_from_dict(_json_object(response), question)


def validate_analysis_plan(plan: AnalysisPlan, df: pd.DataFrame) -> None:
    """Validate all plan fields before any registered tool executes."""
    if not plan.question.strip() or not plan.steps or len(plan.steps) > MAX_TOOL_STEPS:
        raise PlanValidationError("Plan must contain between 1 and 8 steps.")
    for column in plan.required_columns:
        if column not in df.columns:
            raise PlanValidationError(f"Required column does not exist: {column}")
    for step in plan.steps:
        if step.tool not in ALLOWED_TOOLS:
            raise PlanValidationError(f"Tool is not allowed: {step.tool}")
        params = step.parameters
        for key in ("column", "metric", "group_by", "date_column"):
            if params.get(key) is not None and params[key] not in df.columns:
                raise PlanValidationError(f"Column does not exist: {params[key]}")
        filters = params.get("filters", {})
        if not isinstance(filters, dict) or any(column not in df.columns for column in filters):
            raise PlanValidationError("Filters must be an object using existing dataframe columns.")
        if params.get("aggregation") and params["aggregation"] not in ALLOWED_AGGREGATIONS:
            raise PlanValidationError(f"Aggregation is not allowed: {params['aggregation']}")
        if step.tool in {"aggregate", "group_by", "top_n", "bottom_n", "correlation"}:
            metric = params.get("metric") or params.get("column")
            if metric and not pd.api.types.is_numeric_dtype(df[metric]):
                raise PlanValidationError(f"Numeric column required: {metric}")
        if step.tool in {"top_n", "bottom_n"} and not 1 <= int(params.get("n", 5)) <= 100:
            raise PlanValidationError("top_n/bottom_n n must be between 1 and 100.")
    for column in (plan.visualization.x, plan.visualization.y, plan.visualization.group_by):
        if column and column not in df.columns:
            raise PlanValidationError(f"Visualization column does not exist: {column}")


def _used_filters(plan: AnalysisPlan) -> list[str]:
    """Expose only filters that were actually validated and executed."""
    return [f"{column} = {value}" for step in plan.steps for column, value in step.parameters.get("filters", {}).items()]


def is_complex_question(question: str) -> bool:
    """Route explanatory or driver-analysis questions to the controlled agent."""
    normalized_question = question.lower()
    return any(term in normalized_question for term in COMPLEX_INTENT_TERMS)


def _records(frame: pd.DataFrame, limit: int = 50) -> list[dict[str, Any]]:
    return json.loads(frame.head(limit).to_json(orient="records", date_format="iso"))


def _apply_filters(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    """Apply only explicit equality filters; no expressions or generated code are accepted."""
    result = df
    for column, value in filters.items():
        result = result[result[column] == value]
    return result


def execute_tool(df: pd.DataFrame, step: AnalysisStep) -> dict[str, Any]:
    """Execute one allow-listed deterministic operation and return evidence."""
    p, tool = step.parameters, step.tool
    working_df = _apply_filters(df, p.get("filters", {}))
    if tool == "dataset_profile":
        result = profile_dataset(working_df)
    elif tool == "missing_values":
        result = {str(k): int(v) for k, v in working_df.isna().sum().items() if v}
    elif tool == "duplicate_check":
        result = {"duplicate_rows": int(working_df.duplicated().sum())}
    elif tool == "descriptive_statistics":
        columns = p.get("columns") or working_df.select_dtypes(include="number").columns.tolist()
        result = json.loads(working_df[columns].describe().T.to_json(orient="index"))
    elif tool == "aggregate":
        column, aggregation = p.get("column") or p.get("metric"), p.get("aggregation", "sum")
        series = working_df[column]
        result = {f"{aggregation}_{column}": int(series.count()) if aggregation == "count" else float(getattr(series, aggregation)())}
    elif tool == "group_by" or tool == "category_analysis":
        metric, group, aggregation = p.get("metric"), p.get("group_by"), p.get("aggregation", "sum")
        grouped = working_df.groupby(group, dropna=False)[metric].agg(aggregation).reset_index(name=f"{aggregation}_{metric}")
        result = _records(grouped.sort_values(f"{aggregation}_{metric}", ascending=False))
    elif tool in {"top_n", "bottom_n"}:
        column, n = p.get("column") or p.get("metric"), int(p.get("n", 5))
        result = _records(working_df.sort_values(column, ascending=tool == "bottom_n").head(n))
    elif tool == "correlation":
        columns = p.get("columns") or working_df.select_dtypes(include="number").columns.tolist()
        result = json.loads(working_df[columns].corr().to_json())
    elif tool == "time_series_summary":
        monthly = monthly_summary(working_df, p["date_column"], p["metric"])
        if monthly is None or monthly.empty:
            raise PlanValidationError("Time-series analysis produced no data.")
        result = _records(monthly)
    else:
        raise PlanValidationError(f"No executor registered for: {tool}")
    return {"tool": tool, "status": "success", "parameters": p, "result": result, "evidence": f"{tool} executed using validated dataframe columns."}


TOOLS = {tool: execute_tool for tool in ALLOWED_TOOLS}


def validate_tool_result(result: dict[str, Any]) -> None:
    """Reject failed, non-finite, or structurally incomplete deterministic evidence."""
    if result.get("status") != "success" or "result" not in result:
        raise PlanValidationError("Tool did not produce a valid result.")
    if "NaN" in json.dumps(result["result"], default=str) or "Infinity" in json.dumps(result["result"], default=str):
        raise PlanValidationError("Tool result contains non-finite values.")


def recommend_visualization(plan: AnalysisPlan) -> dict[str, Any]:
    visual = plan.visualization
    chart = visual.chart_type if visual.needed else "table"
    filters = _used_filters(plan)
    filter_text = "; ".join(filters) if filters else "None"
    return {"chart_type": chart, "title": visual.title, "x_axis": visual.x or "", "y_axis": visual.y or "", "group_by": visual.group_by or "", "filters": filters, "reason": "Matches the validated analysis plan.", "power_bi": f"Visual: {chart}; Axis: {visual.x or 'N/A'}; Values: {visual.y or 'N/A'}; Filters: {filter_text}; Title: {visual.title}", "tableau": f"Columns: {visual.x or 'N/A'}; Rows: {visual.y or 'N/A'}; Marks: {chart}; Filters: {filter_text}; Title: {visual.title}"}


def _root_cause_structure(question: str, results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Describe observed regional profitability without asserting causation."""
    if "why" not in question.lower():
        return None
    regional = {}
    for result in results:
        parameters = result.get("parameters", {})
        if result.get("tool") == "group_by" and parameters.get("group_by") == "region":
            regional[parameters.get("metric")] = result.get("result", [])
    profit_rows = regional.get("profit", [])
    if not profit_rows:
        return None
    leader = profit_rows[0]
    region, profit = leader.get("region"), leader.get("sum_profit")
    revenue = next((row.get("sum_revenue") for row in regional.get("revenue", []) if row.get("region") == region), None)
    evidence = [f"{region} total profit = {profit:,.2f}."]
    if revenue is not None:
        evidence.append(f"{region} total revenue = {revenue:,.2f}.")
    return {
        "observation": f"{region} has the highest observed total profit.",
        "evidence": evidence,
        "interpretation": "Observed data indicates a strong revenue/profit outcome; aggregate evidence alone does not establish causation.",
        "recommendation": "Investigate category, product, pricing, and cost contributors before taking causal action.",
    }


def _deterministic_business_response(question: str, root_cause: dict[str, Any] | None, evidence: str) -> str:
    """Return a useful report when narrative generation is unavailable or times out."""
    if root_cause:
        return (
            f"## Business Question\n{question}\n\n## Answer\n{root_cause['observation']}\n\n"
            f"## Key Findings\n- " + "\n- ".join(root_cause["evidence"]) + "\n\n"
            f"## Evidence\n{evidence}\n\n## Root Cause / Drivers\n{root_cause['interpretation']}\n\n"
            f"## Recommendations\n{root_cause['recommendation']}"
        )
    return f"## Business Question\n{question}\n\n## Answer\nDeterministic analysis completed.\n\n## Evidence\n{evidence}"


def _evidence_answer(question: str, results: list[dict[str, Any]], trace: list[dict[str, Any]], *, timeout: int | None = None) -> str:
    evidence = json.dumps([{"tool": r["tool"], "result": r["result"]} for r in results], default=str)[:12000]
    prompt = f"""Answer the question using ONLY this deterministic evidence. Never invent numbers or causal claims.
Question: {question}
Evidence: {evidence}
Use Markdown headings: Answer, Key Findings, Evidence, Root Cause (only if supported; say 'Evidence suggests' not certainty), Business Recommendation."""
    try:
        answer = get_llm_provider().generate_narrative(prompt, timeout=timeout)
    except LLMProviderError:
        raise
    if answer.startswith("❌"):
        return "## Answer\nDeterministic analysis completed. Ollama was unavailable for narrative interpretation.\n\n## Evidence\n" + evidence
    causal_language = re.compile(r"\b(causes?|caused|because|due to|drives?|driving|responsible)\b", re.IGNORECASE)
    causal_qualifier = re.compile(r"evidence suggests|may|might|could|cannot determine|does not establish|insufficient", re.IGNORECASE)
    if causal_language.search(answer) and not causal_qualifier.search(answer):
        return (
            "## Answer\nDeterministic analysis completed.\n\n"
            "## Evidence\n" + evidence + "\n\n"
            "## Root Cause\nThe available deterministic evidence does not establish causation.\n\n"
            "## Business Recommendation\nInvestigate the observed drivers before taking causal action."
        )
    return answer


def _append_regional_root_cause_evidence(
    df: pd.DataFrame, question: str, results: list[dict[str, Any]], trace: list[dict[str, Any]]
) -> None:
    """Add deterministic regional driver evidence for supported 'why' questions."""
    words = question.lower()
    required = {"region", "profit", "revenue"}
    if "why" not in words or "region" not in words or "profit" not in words or not required.issubset(df.columns):
        return
    steps = [
        AnalysisStep("group_by", {"group_by": "region", "metric": "profit", "aggregation": "sum"}),
        AnalysisStep("group_by", {"group_by": "region", "metric": "revenue", "aggregation": "sum"}),
    ]
    if "profit_margin" in df.columns:
        steps.append(AnalysisStep("group_by", {"group_by": "region", "metric": "profit_margin", "aggregation": "mean"}))
    for step in steps:
        if len(trace) >= MAX_TOOL_STEPS:
            return
        result = TOOLS[step.tool](df, step)
        validate_tool_result(result)
        results.append(result)
        trace.append({"step": len(trace) + 1, "tool": step.tool, "status": "success", "parameters": step.parameters, "result_summary": "Regional root-cause evidence validated.", "validation": "passed"})
    region_profit = results[-len(steps)]["result"]
    top_region = region_profit[0]["region"] if region_profit else None
    if not top_region:
        return
    driver_steps = [AnalysisStep("top_n", {"column": "profit", "n": 5, "filters": {"region": top_region}})]
    if "category" in df.columns:
        driver_steps = [
            AnalysisStep("group_by", {"group_by": "category", "metric": "profit", "aggregation": "sum", "filters": {"region": top_region}}),
            AnalysisStep("group_by", {"group_by": "category", "metric": "revenue", "aggregation": "sum", "filters": {"region": top_region}}),
            *driver_steps,
        ]
    for step in driver_steps:
        if len(trace) >= MAX_TOOL_STEPS:
            return
        result = TOOLS[step.tool](df, step)
        validate_tool_result(result)
        results.append(result)
        trace.append({"step": len(trace) + 1, "tool": step.tool, "status": "success", "parameters": step.parameters, "result_summary": f"Validated driver evidence for {top_region}.", "validation": "passed"})


def run_autonomous_analysis(df: pd.DataFrame, question: str) -> dict[str, Any]:
    """Plan, validate, execute, validate evidence, interpret, and return safe metadata."""
    normalized_question = question.lower()
    if any(term in normalized_question for term in ("predict", "forecast", "next year", "next month's")):
        return {
            "mode": "deterministic_fast_path", "status": "unsupported", "planning_method": "deterministic",
            "narrative_method": "deterministic_fallback",
            "answer": "ML analysis for this question is not currently supported.", "plan": None, "evidence": [],
            "root_cause": None, "visualization": {"chart_type": "table", "title": "Unsupported analysis", "filters": []},
            "trace": [{"step": 1, "tool": "capability_check", "status": "unsupported", "validation": "passed"}],
        }
    if "total revenue" in normalized_question and "average order value" in normalized_question and "revenue" in df.columns:
        total_revenue = float(df["revenue"].sum())
        average_order_value = float(df["revenue"].mean())
        return {"mode": "deterministic_fast_path", "status": "success", "planning_method": "deterministic", "narrative_method": "deterministic_fallback", "answer": f"Total revenue is {total_revenue:,.2f}. Average order value is {average_order_value:,.2f}.", "plan": None, "evidence": [{"tool": "aggregate", "status": "success", "result": {"sum_revenue": total_revenue, "mean_revenue": average_order_value}}], "root_cause": None, "visualization": {"chart_type": "kpi_card", "title": "Revenue and average order value", "filters": []}, "trace": [{"step": 1, "tool": "aggregate", "status": "success", "validation": "passed"}]}
    if not is_complex_question(question):
        simple_answer = query_dataset(df, question)
        if simple_answer and " and " not in normalized_question:
            return {"mode": "deterministic_fast_path", "status": "success", "planning_method": "deterministic", "narrative_method": "deterministic_fallback", "answer": simple_answer, "plan": None, "evidence": [], "root_cause": None, "visualization": {"chart_type": "table", "title": "Deterministic result", "filters": []}, "trace": [{"step": 1, "tool": "data_query_engine", "status": "success", "validation": "passed"}]}
    plan = create_analysis_plan(df, question)
    validate_analysis_plan(plan, df)
    results, trace = [], []
    for index, step in enumerate(plan.steps, start=1):
        result = TOOLS[step.tool](df, step)
        validate_tool_result(result)
        results.append(result)
        trace.append({"step": index, "tool": step.tool, "status": "success", "parameters": step.parameters, "result_summary": f"Validated {step.tool} result.", "validation": "passed"})
    _append_regional_root_cause_evidence(df, question, results, trace)
    root_cause = _root_cause_structure(question, results)
    evidence_text = json.dumps([{"tool": result["tool"], "result": result["result"]} for result in results], default=str)
    try:
        answer = _evidence_answer(
            question, results, trace, timeout=min(get_llm_timeout(), NARRATIVE_TIMEOUT_CAP_SECONDS)
        )
        narrative_method, status = "llm", "success"
    except LLMProviderError:
        answer = _deterministic_business_response(question, root_cause, evidence_text)
        narrative_method, status = "deterministic_fallback", "success_with_fallback"
    planning_method = "fallback" if plan.intent == "regional profitability investigation" else get_llm_provider_label()
    return {"mode": "agent", "status": status, "planning_method": planning_method, "narrative_method": narrative_method, "answer": answer, "plan": asdict(plan), "evidence": results, "root_cause": root_cause, "visualization": recommend_visualization(plan), "trace": trace}


def execute_analysis(df: pd.DataFrame, plan: AnalysisPlan) -> tuple[bool, list[dict[str, Any]] | str]:
    """Backward-compatible controlled executor for callers of the old prototype."""
    try:
        validate_analysis_plan(plan, df)
        return True, [execute_tool(df, step) for step in plan.steps]
    except PlanValidationError as error:
        return False, str(error)
