import json

import pandas as pd
import pytest

from src import agent_engine as agent


@pytest.fixture
def sales_df():
    return pd.DataFrame({
        "region": ["East", "West", "East"], "category": ["A", "A", "B"],
        "revenue": [100.0, 200.0, 50.0], "profit": [20.0, 80.0, 5.0],
        "quantity": [1, 2, 1], "order_date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-02-01"]),
    })


def valid_plan():
    return agent.AnalysisPlan(
        question="Which region has the highest profit?", intent="regional profitability",
        required_columns=["region", "profit"],
        steps=[agent.AnalysisStep("group_by", {"group_by": "region", "metric": "profit", "aggregation": "sum"})],
        expected_output="Profit by region",
        visualization=agent.VisualizationRecommendation(True, "bar", "region", "profit", None, "Profit by region"),
    )


def test_valid_analysis_plan(sales_df):
    agent.validate_analysis_plan(valid_plan(), sales_df)


def test_invalid_tool_is_rejected(sales_df):
    plan = agent.AnalysisPlan("q", "x", [], [agent.AnalysisStep("python", {})], "x")
    with pytest.raises(agent.PlanValidationError, match="not allowed"):
        agent.validate_analysis_plan(plan, sales_df)


def test_invalid_column_and_aggregation_are_rejected(sales_df):
    plan = agent.AnalysisPlan("q", "x", [], [agent.AnalysisStep("aggregate", {"column": "missing", "aggregation": "eval"})], "x")
    with pytest.raises(agent.PlanValidationError):
        agent.validate_analysis_plan(plan, sales_df)


def test_top_n_group_by_missing_values_and_correlation(sales_df):
    top = agent.execute_tool(sales_df, agent.AnalysisStep("top_n", {"column": "profit", "n": 2}))
    grouped = agent.execute_tool(sales_df, agent.AnalysisStep("group_by", {"group_by": "region", "metric": "profit", "aggregation": "sum"}))
    missing = agent.execute_tool(sales_df, agent.AnalysisStep("missing_values", {}))
    correlation = agent.execute_tool(sales_df, agent.AnalysisStep("correlation", {"columns": ["revenue", "profit"]}))
    assert top["result"][0]["profit"] == 80.0
    assert grouped["result"][0]["region"] == "West"
    assert missing["result"] == {}
    assert "revenue" in correlation["result"]


def test_result_validation_rejects_non_finite_evidence():
    with pytest.raises(agent.PlanValidationError, match="non-finite"):
        agent.validate_tool_result({"status": "success", "result": {"metric": float("nan")}})


def test_malformed_llm_response_is_rejected(monkeypatch, sales_df):
    monkeypatch.setattr(agent, "ask_llama", lambda prompt: "not JSON")
    with pytest.raises(agent.PlanValidationError, match="JSON"):
        agent.create_analysis_plan(sales_df, "Analyze profit")


def test_end_to_end_agent_execution_uses_deterministic_evidence(monkeypatch, sales_df):
    plan_json = {"question": "Which region has the highest profit and why?", "intent": "regional profitability", "required_columns": ["region", "profit"], "steps": [{"tool": "group_by", "parameters": {"group_by": "region", "metric": "profit", "aggregation": "sum"}}], "expected_output": "Profit by region", "visualization": {"needed": True, "chart_type": "bar", "x": "region", "y": "profit", "title": "Profit by region"}}
    monkeypatch.setattr(agent, "ask_llama", lambda prompt: json.dumps(plan_json) if "Return ONLY JSON" in prompt else "## Answer\nWest has the highest validated profit.")
    result = agent.run_autonomous_analysis(sales_df, "Which region has the highest profit and why?")
    assert result["mode"] == "agent"
    assert result["evidence"][0]["result"][0]["region"] == "West"
    assert result["trace"][0]["validation"] == "passed"
    assert len(result["trace"]) > 1


def test_simple_revenue_question_skips_llm(monkeypatch, sales_df):
    monkeypatch.setattr(agent, "ask_llama", lambda prompt: pytest.fail("LLM should not be called"))
    result = agent.run_autonomous_analysis(sales_df, "Give me total revenue and average order value")
    assert result["mode"] == "deterministic_fast_path"
