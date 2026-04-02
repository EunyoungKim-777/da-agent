"""StateGraph 구성 모듈.

반도체 TEST 데이터 분석 자동화 Agent의 전체 그래프를 정의한다.

노드 흐름:
    START
      → plan_node                   (Planning 플랜 생성)
      → hitl_node                   (Planning HITL)
        ├─ approve  → preprocessing_plan_node
        ├─ revise   → plan_node
        └─ cancel   → END
      → preprocessing_plan_node     (전처리 플랜 생성)
      → hitl_node                   (전처리 HITL)
        ├─ approve  → preprocessing_exec_node
        ├─ revise   → preprocessing_plan_node
        └─ cancel   → END
      → preprocessing_exec_node     (전처리 실행)
      → eda_plan_node               (EDA 플랜 생성)
      → hitl_node                   (EDA HITL)
        ├─ approve  → eda_exec_node
        ├─ revise   → eda_plan_node
        └─ cancel   → END
      → eda_exec_node               (EDA 실행)
      → modeling_plan_node          (모델링 플랜 생성)
      → hitl_node                   (모델링 HITL)
        ├─ approve        → modeling_exec_node
        ├─ revise         → modeling_plan_node
        ├─ cancel         → END
        └─ skip_modeling  → save_assets
      → modeling_exec_node          (모델링 실행)
      → evaluation_plan_node        (평가 플랜 생성)
      → hitl_node                   (평가 HITL)
        ├─ approve  → evaluation_exec_node
        ├─ revise   → evaluation_plan_node
        └─ cancel   → END
      → evaluation_exec_node        (평가 실행)
      → save_assets                 (결과 저장)
      → END
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.agent.nodes.asset import save_assets
from src.agent.nodes.eda import eda_exec_node, eda_plan_node
from src.agent.nodes.evaluation import evaluation_exec_node, evaluation_plan_node
from src.agent.nodes.hitl import hitl_node
from src.agent.nodes.modeling import modeling_exec_node, modeling_plan_node
from src.agent.nodes.planning import plan_node
from src.agent.nodes.preprocessing import preprocessing_exec_node, preprocessing_plan_node
from src.agent.state import AgentState


# ---------------------------------------------------------------------------
# HITL 라우터: 현재 단계(current_step)에 따라 분기 대상이 달라진다.
# ---------------------------------------------------------------------------

def _route_planning_hitl(state: AgentState) -> str:
    """Planning HITL 이후 분기."""
    action = state.get("hitl_action", "approve")
    if action == "cancel":
        return END
    if action == "revise":
        return "plan_node"
    return "preprocessing_plan_node"


def _route_preprocessing_hitl(state: AgentState) -> str:
    """전처리 HITL 이후 분기."""
    action = state.get("hitl_action", "approve")
    if action == "cancel":
        return END
    if action == "revise":
        return "preprocessing_plan_node"
    return "preprocessing_exec_node"


def _route_eda_hitl(state: AgentState) -> str:
    """EDA HITL 이후 분기."""
    action = state.get("hitl_action", "approve")
    if action == "cancel":
        return END
    if action == "revise":
        return "eda_plan_node"
    return "eda_exec_node"


def _route_modeling_hitl(state: AgentState) -> str:
    """모델링 HITL 이후 분기. skip_modeling 지원."""
    action = state.get("hitl_action", "approve")
    if action == "cancel":
        return END
    if action == "skip_modeling":
        return "save_assets"
    if action == "revise":
        return "modeling_plan_node"
    return "modeling_exec_node"


def _route_after_eda(state: AgentState) -> str:
    """EDA 실행 완료 후 모델링 필요 여부에 따라 분기.

    plan["modeling"]이 null/빈값이면 모델링을 건너뛰고 결과 저장으로 직행한다.
    """
    plan = state.get("plan", {})
    if not plan.get("modeling"):
        return "save_assets"
    return "modeling_plan_node"


def _route_evaluation_hitl(state: AgentState) -> str:
    """평가 HITL 이후 분기."""
    action = state.get("hitl_action", "approve")
    if action == "cancel":
        return END
    if action == "revise":
        return "evaluation_plan_node"
    return "evaluation_exec_node"


# ---------------------------------------------------------------------------
# 각 HITL 노드는 동일한 함수(hitl_node)를 사용하지만
# LangGraph에서는 노드명이 고유해야 하므로 래퍼로 분리한다.
# ---------------------------------------------------------------------------

async def planning_hitl_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Planning 단계 HITL 노드."""
    return await hitl_node(state, config)


async def preprocessing_hitl_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """전처리 단계 HITL 노드."""
    return await hitl_node(state, config)


async def eda_hitl_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """EDA 단계 HITL 노드."""
    return await hitl_node(state, config)


async def modeling_hitl_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """모델링 단계 HITL 노드 (skip_modeling 선택지 포함)."""
    return await hitl_node(state, config)


async def evaluation_hitl_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """평가 단계 HITL 노드."""
    return await hitl_node(state, config)


# ---------------------------------------------------------------------------
# 그래프 빌드
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """전체 분석 파이프라인 StateGraph를 구성하고 반환한다.

    Returns:
        컴파일되지 않은 StateGraph (compile()은 호출자가 checkpointer와 함께 수행)
    """
    builder = StateGraph(AgentState)  # type: ignore

    # ── 노드 등록 ──────────────────────────────────────────────────────────
    builder.add_node("plan_node", plan_node)

    builder.add_node("planning_hitl", planning_hitl_node)

    builder.add_node("preprocessing_plan_node", preprocessing_plan_node)
    builder.add_node("preprocessing_hitl", preprocessing_hitl_node)
    builder.add_node("preprocessing_exec_node", preprocessing_exec_node)

    builder.add_node("eda_plan_node", eda_plan_node)
    builder.add_node("eda_hitl", eda_hitl_node)
    builder.add_node("eda_exec_node", eda_exec_node)

    builder.add_node("modeling_plan_node", modeling_plan_node)
    builder.add_node("modeling_hitl", modeling_hitl_node)
    builder.add_node("modeling_exec_node", modeling_exec_node)

    builder.add_node("evaluation_plan_node", evaluation_plan_node)
    builder.add_node("evaluation_hitl", evaluation_hitl_node)
    builder.add_node("evaluation_exec_node", evaluation_exec_node)

    builder.add_node("save_assets", save_assets)

    # ── 엣지 연결 ──────────────────────────────────────────────────────────
    # START → Planning
    builder.add_edge(START, "plan_node")
    builder.add_edge("plan_node", "planning_hitl")
    builder.add_conditional_edges(
        "planning_hitl",
        _route_planning_hitl,
        {
            "plan_node": "plan_node",
            "preprocessing_plan_node": "preprocessing_plan_node",
            END: END,
        },
    )

    # Preprocessing
    builder.add_edge("preprocessing_plan_node", "preprocessing_hitl")
    builder.add_conditional_edges(
        "preprocessing_hitl",
        _route_preprocessing_hitl,
        {
            "preprocessing_plan_node": "preprocessing_plan_node",
            "preprocessing_exec_node": "preprocessing_exec_node",
            END: END,
        },
    )
    builder.add_edge("preprocessing_exec_node", "eda_plan_node")

    # EDA
    builder.add_edge("eda_plan_node", "eda_hitl")
    builder.add_conditional_edges(
        "eda_hitl",
        _route_eda_hitl,
        {
            "eda_plan_node": "eda_plan_node",
            "eda_exec_node": "eda_exec_node",
            END: END,
        },
    )
    builder.add_conditional_edges(
        "eda_exec_node",
        _route_after_eda,
        {
            "modeling_plan_node": "modeling_plan_node",
            "save_assets": "save_assets",
        },
    )

    # Modeling
    builder.add_edge("modeling_plan_node", "modeling_hitl")
    builder.add_conditional_edges(
        "modeling_hitl",
        _route_modeling_hitl,
        {
            "modeling_plan_node": "modeling_plan_node",
            "modeling_exec_node": "modeling_exec_node",
            "save_assets": "save_assets",
            END: END,
        },
    )
    builder.add_edge("modeling_exec_node", "evaluation_plan_node")

    # Evaluation
    builder.add_edge("evaluation_plan_node", "evaluation_hitl")
    builder.add_conditional_edges(
        "evaluation_hitl",
        _route_evaluation_hitl,
        {
            "evaluation_plan_node": "evaluation_plan_node",
            "evaluation_exec_node": "evaluation_exec_node",
            END: END,
        },
    )
    builder.add_edge("evaluation_exec_node", "save_assets")

    # Save → END
    builder.add_edge("save_assets", END)

    return builder


async def create_compiled_graph(checkpointer: Any = None):
    """checkpointer를 주입해 컴파일된 그래프를 반환한다.

    Args:
        checkpointer: AsyncPostgresSaver 인스턴스 (None이면 메모리 체크포인터 사용)

    Returns:
        CompiledGraph: 실행 가능한 LangGraph 그래프
    """
    builder = build_graph()

    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)
