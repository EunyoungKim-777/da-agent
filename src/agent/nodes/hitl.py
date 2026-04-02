"""공통 HITL(Human-in-the-Loop) 노드 모듈.

LangGraph의 interrupt()를 사용해 각 단계 실행 전 사용자 승인을 요청한다.
HITL은 config 플래그(hitl_enabled)로 on/off 가능하다.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from src.agent.state import AgentState, HitlAction
from src.agent.tracer import traced


def _build_hitl_payload(state: AgentState) -> dict[str, Any]:
    """사용자에게 보여줄 HITL 페이로드를 구성한다."""
    return {
        "current_step": state.get("current_step"),
        "plan": state.get("plan"),
        "step_plan": state.get("step_plan"),
        "jupyter_code": state.get("jupyter_code"),
        "message": (
            f"[{state.get('current_step', '').upper()}] 단계 계획을 검토해주세요.\n"
            "승인(approve) / 수정 요청(revise) / 취소(cancel) / 모델링 건너뜀(skip_modeling)"
        ),
    }


@traced("hitl_node")
async def hitl_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """공통 HITL 노드.

    config["configurable"]["hitl_enabled"]가 False이면 자동으로 "approve" 처리한다.
    True(기본값)이면 interrupt()로 실행을 중단하고 사용자 응답을 기다린다.

    사용자 응답 형식 (dict):
        {
            "hitl_action": "approve" | "revise" | "cancel" | "skip_modeling",
            "hitl_feedback": "수정 지시사항 (revise 시)"  # optional
        }

    Returns:
        hitl_action, hitl_feedback이 반영된 상태 업데이트 dict
    """
    configurable = config.get("configurable", {}) if config else {}
    hitl_enabled: bool = configurable.get("hitl_enabled", True)

    if not hitl_enabled:
        return {"hitl_action": "approve", "hitl_feedback": None}

    payload = _build_hitl_payload(state)
    user_response: dict[str, Any] = interrupt(payload)

    action: HitlAction = user_response.get("hitl_action", "approve")
    feedback: str | None = user_response.get("hitl_feedback")

    return {"hitl_action": action, "hitl_feedback": feedback}


def route_after_hitl(state: AgentState) -> str:
    """HITL 결과에 따라 다음 노드를 결정하는 조건부 엣지 함수.

    Returns:
        다음 노드명 문자열:
            - "approve"       → 현재 단계 실행 노드
            - "revise"        → 현재 단계 플랜 재수립 노드
            - "cancel"        → 종료 노드
            - "skip_modeling" → 결과 저장 노드 (모델링·평가 건너뜀)
    """
    action = state.get("hitl_action", "approve")
    current_step = state.get("current_step", "planning")

    if action == "cancel":
        return "end"

    if action == "skip_modeling":
        return "save_assets"

    if action == "revise":
        # 단계별 플랜 재수립 노드로 라우팅
        revise_map: dict[str, str] = {
            "planning": "plan_node",
            "preprocessing": "preprocessing_plan_node",
            "eda": "eda_plan_node",
            "modeling": "modeling_plan_node",
            "evaluation": "evaluation_plan_node",
        }
        return revise_map.get(current_step, "plan_node")

    # "approve"
    execute_map: dict[str, str] = {
        "planning": "preprocessing_plan_node",
        "preprocessing": "preprocessing_exec_node",
        "eda": "eda_exec_node",
        "modeling": "modeling_exec_node",
        "evaluation": "evaluation_exec_node",
        "saving": "save_assets",
    }
    return execute_map.get(current_step, "end")
