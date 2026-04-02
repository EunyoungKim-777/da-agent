"""AgentState 정의 모듈."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages


StepName = Literal[
    "planning",
    "preprocessing",
    "eda",
    "modeling",
    "evaluation",
    "saving",
    "end",
]

HitlAction = Literal["approve", "revise", "cancel", "skip_modeling"]


class AgentState(TypedDict):
    """반도체 TEST 데이터 분석 자동화 Agent의 전체 상태."""

    # 사용자 입력
    user_input: str

    # 현재 실행 단계
    current_step: StepName

    # 전체 분석 플랜 (Planning 노드에서 생성)
    plan: dict[str, Any]

    # 현재 단계의 세부 플랜
    step_plan: dict[str, Any]

    # HITL 결과: "approve" / "revise" / "cancel" / "skip_modeling"
    hitl_action: Optional[HitlAction]

    # HITL 피드백 텍스트 (revise 시 수정 지시사항)
    hitl_feedback: Optional[str]

    # 현재 단계에서 실행할 Jupyter 코드
    jupyter_code: Optional[str]

    # Jupyter Cell 실행 결과
    jupyter_output: Optional[str]

    # 단계별 분석 결과 누적 (키: 단계명, 값: 결과 dict)
    analysis_result: dict[str, Any]

    # LLM 대화 이력 (add_messages reducer로 자동 누적)
    messages: Annotated[list, add_messages]

    # 에러 메시지
    error: Optional[str]
