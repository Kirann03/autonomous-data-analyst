import json

import pandas as pd
import pytest

from src import agent_engine as agent
from src.llm.base import LLMProviderError


class StubProvider:
    def __init__(self, plan="{\"steps\":[]}", narrative="## Answer\nStub narrative", error=None):
        self.plan, self.narrative, self.error = plan, narrative, error
        self.prompts, self.timeouts = [], []

    def generate_plan(self, prompt, *, timeout=None):
        self.prompts.append(prompt)
        self.timeouts.append(timeout)
        if self.error:
            raise self.error
        return self.plan

    def generate_narrative(self, prompt, *, timeout=None):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.narrative


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
    monkeypatch.setattr(agent, "get_llm_provider", lambda: StubProvider(plan="not JSON"))
    with pytest.raises(agent.PlanValidationError, match="failed after one retry"):
        agent.create_analysis_plan(sales_df, "Analyze profit")


def test_compact_planner_prompt_excludes_dataframe_rows(monkeypatch):
    provider = StubProvider(plan="not json")
    monkeypatch.setattr(agent, "get_llm_provider", lambda: provider)
    with pytest.raises(agent.PlanValidationError):
        agent._planner_response(
            [{"name": "region", "numeric": False}, {"name": "profit", "numeric": True}],
            "Why is South the most profitable region?",
        )
    assert "North" not in provider.prompts[0]
    assert "South =" not in provider.prompts[0]
    assert "Allowed tool: group_by" in provider.prompts[0]


def test_planner_timeout_is_capped(monkeypatch):
    provider = StubProvider(plan="not json")
    monkeypatch.setattr(agent, "get_llm_timeout", lambda: 120)
    monkeypatch.setattr(agent, "get_llm_provider", lambda: provider)
    with pytest.raises(agent.PlanValidationError):
        agent._planner_response([{"name": "region", "numeric": False}], "Why is region profitable?")
    assert provider.timeouts == [agent.PLANNER_TIMEOUT_CAP_SECONDS, agent.PLANNER_TIMEOUT_CAP_SECONDS]


def test_end_to_end_agent_execution_uses_deterministic_evidence(monkeypatch, sales_df):
    plan_json = {"question": "Which region has the highest profit and why?", "intent": "regional profitability", "required_columns": ["region", "profit"], "steps": [{"tool": "group_by", "parameters": {"group_by": "region", "metric": "profit", "aggregation": "sum"}}], "expected_output": "Profit by region", "visualization": {"needed": True, "chart_type": "bar", "x": "region", "y": "profit", "title": "Profit by region"}}
    monkeypatch.setattr(agent, "get_llm_provider", lambda: StubProvider(json.dumps(plan_json), "## Answer\nWest has the highest validated profit."))
    result = agent.run_autonomous_analysis(sales_df, "Which region has the highest profit and why?")
    assert result["mode"] == "agent"
    assert result["evidence"][0]["result"][0]["region"] == "West"
    assert result["trace"][0]["validation"] == "passed"
    assert len(result["trace"]) > 1


def test_simple_revenue_question_skips_llm(monkeypatch, sales_df):
    monkeypatch.setattr(agent, "get_llm_provider", lambda: pytest.fail("LLM should not be called"))
    result = agent.run_autonomous_analysis(sales_df, "Give me total revenue and average order value")
    assert result["mode"] == "deterministic_fast_path"


def test_simple_question_uses_deterministic_query_path(monkeypatch, sales_df):
    monkeypatch.setattr(agent, "get_llm_provider", lambda: pytest.fail("Planner should not be called"))
    result = agent.run_autonomous_analysis(sales_df, "What is total revenue?")
    assert result["mode"] == "deterministic_fast_path"
    assert "350.00" in result["answer"]
    assert result["planning_method"] == "deterministic"
    assert result["narrative_method"] == "deterministic_fallback"


def test_forecasting_request_is_explicitly_unsupported(sales_df):
    result = agent.run_autonomous_analysis(sales_df, "Predict next year's revenue.")
    assert result["status"] == "unsupported"
    assert result["answer"] == "ML analysis for this question is not currently supported."


def test_complex_question_uses_agent_and_passes_evidence_to_narrative(monkeypatch, sales_df):
    plan_json = {"question": "Why is West the most profitable region?", "steps": [{"tool": "group_by", "parameters": {"group_by": "region", "metric": "profit", "aggregation": "sum"}}]}
    provider = StubProvider(json.dumps(plan_json), "## Answer\nEvidence suggests West has the highest profit.")
    monkeypatch.setattr(agent, "query_dataset", lambda *args, **kwargs: pytest.fail("Legacy query engine should not be called"))
    monkeypatch.setattr(agent, "get_llm_provider", lambda: provider)
    result = agent.run_autonomous_analysis(sales_df, "Why is West the most profitable region?")
    assert result["mode"] == "agent"
    assert len(result["trace"]) > 1
    assert "sum_profit" in provider.prompts[-1]
    assert "causal claims" in provider.prompts[-1]


def test_complex_planner_failure_is_controlled(monkeypatch, sales_df):
    monkeypatch.setattr(agent, "get_llm_provider", lambda: StubProvider(error=LLMProviderError("unavailable")))
    with pytest.raises(agent.PlanValidationError, match="failed after one retry"):
        agent.run_autonomous_analysis(sales_df, "Why is profit important?")


def test_supported_planner_failure_uses_validated_fallback(monkeypatch):
    df = pd.DataFrame({"region": ["North", "South"], "profit": [300, 450], "revenue": [1000, 1500]})
    monkeypatch.setattr(agent, "get_llm_provider", lambda: StubProvider(error=LLMProviderError("unavailable")))
    plan = agent.create_analysis_plan(df, "Why is South the most profitable region?")
    agent.validate_analysis_plan(plan, df)
    results = [agent.execute_tool(df, step) for step in plan.steps]
    for result in results:
        agent.validate_tool_result(result)
    assert [step.parameters["metric"] for step in plan.steps] == ["profit", "revenue"]
    assert results[0]["result"][0] == {"region": "South", "sum_profit": 450}


def test_narrative_failure_preserves_evidence_and_structured_root_cause(monkeypatch):
    df = pd.DataFrame({"region": ["North", "South", "East", "West"], "profit": [300, 450, 100, 360], "revenue": [1000, 1500, 700, 1200]})
    provider = StubProvider(error=LLMProviderError("unavailable"))
    monkeypatch.setattr(agent, "get_llm_provider", lambda: provider)
    result = agent.run_autonomous_analysis(df, "Why is South the most profitable region?")
    assert result["status"] == "success_with_fallback"
    assert result["narrative_method"] == "deterministic_fallback"
    assert result["root_cause"]["observation"].startswith("South")
    assert "South total profit = 450.00." in result["root_cause"]["evidence"]
    assert result["evidence"][0]["result"][0]["region"] == "South"


def test_visualization_exposes_only_used_filters(sales_df):
    plan = agent.AnalysisPlan(
        "q", "x", [], [agent.AnalysisStep("group_by", {"group_by": "region", "metric": "profit", "filters": {"region": "West"}})], "x"
    )
    visualization = agent.recommend_visualization(plan)
    assert visualization["filters"] == ["region = West"]


def test_unqualified_causal_narrative_is_replaced_with_safe_response(monkeypatch):
    monkeypatch.setattr(agent, "get_llm_provider", lambda: StubProvider(narrative="## Root Cause\nRevenue causes profit to be higher."))
    answer = agent._evidence_answer("Why?", [{"tool": "aggregate", "result": {"sum_profit": 450}}], [])
    assert "does not establish causation" in answer
    assert "Revenue causes" not in answer
