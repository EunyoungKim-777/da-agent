"""전처리(Preprocessing) 노드 모듈.

전처리 세부 플랜을 수립하고, HITL 승인 후 Jupyter Cell 단위로 코드를 실행한다.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.agent.llm import get_client, get_model_name
from src.agent.nodes.jupyter import execute_cell
from src.agent.state import AgentState
from src.agent.tracer import traced


@traced("preprocessing_plan_node")
async def preprocessing_plan_node(
    state: AgentState, config: RunnableConfig
) -> dict[str, Any]:
    """전처리 단계의 세부 플랜 및 실행 코드를 생성한다.

    전체 분석 플랜(state["plan"])과 데이터 소스 정보를 바탕으로
    결측치 처리·이상치 제거·피처 엔지니어링 등 전처리 코드를 작성한다.
    hitl_feedback이 있으면 피드백을 반영해 플랜과 코드를 재생성한다.

    State 입력:
        plan: 전체 분석 플랜
        hitl_feedback: (revise 시) 수정 지시사항

    State 출력:
        step_plan: 전처리 세부 플랜 dict
        jupyter_code: 실행할 전처리 Python 코드
        current_step: "preprocessing"
        hitl_action: None (초기화)
    """
    # TODO: LLM 호출로 전처리 플랜 및 코드 생성 구현
    return {
        "current_step": "preprocessing",
        "step_plan": {},
        "jupyter_code": "",
        "hitl_action": None,
        "hitl_feedback": None,
    }


@traced("preprocessing_exec_node")
async def preprocessing_exec_node(
    state: AgentState, config: RunnableConfig
) -> dict[str, Any]:
    """승인된 전처리 코드를 Jupyter Cell 단위로 실행하고 결과를 저장한다.

    State 입력:
        jupyter_code: 실행할 전처리 코드
        analysis_result: 기존 누적 결과

    State 출력:
        jupyter_output: Jupyter 실행 결과 문자열
        analysis_result: "preprocessing" 결과 추가
    """
    # TODO: execute_cell() 호출 및 결과 파싱 구현
    return {
        "jupyter_output": "",
        "analysis_result": {
            **state.get("analysis_result", {}),
            "preprocessing": {},
        },
    }
