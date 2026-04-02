"""Planning 노드 모듈.

사용자 입력을 기반으로 전체 분석 플랜(목표, 데이터 소스, 분석 방향)을 수립한다.
HITL을 통해 사용자 검토 및 승인 후 다음 단계로 진행한다.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from openai.types.chat import ChatCompletionMessageParam

from src.agent.llm import get_client, get_model_name
from src.agent.state import AgentState
from src.agent.tracer import traced


_SYSTEM_PROMPT = """\
당신은 반도체 TEST 데이터 분석 전문가입니다.
사용자의 분석 요청을 이해하고, 아래 JSON 스키마에 맞는 분석 플랜을 수립해주세요.

반드시 순수 JSON만 반환하세요. 마크다운 코드블록(```), 설명 텍스트, 주석 없이 JSON 객체만 출력하세요.

JSON 스키마:
{
    "objective": "분석 목표를 한 문장으로 명확하게 기술",
    "data_source": "사용할 데이터 소스 및 파일 경로/형식",
    "preprocessing": "결측치 처리, 이상치 제거, 피처 엔지니어링 등 전처리 방향",
    "eda": "분포 분석, 상관관계, 시각화 등 EDA 방향",
    "modeling": "분류 모델 기반 접근 방향 (구체적인 모델은 현업 확인 후 결정)",
    "evaluation": "성능 지표 및 평가 방향 (모델링을 수행하지 않는 경우 null)"
}
"""


def _build_user_message(user_input: str, feedback: str | None) -> str:
    """LLM에게 전달할 사용자 메시지를 구성한다."""
    if feedback:
        return (
            f"[기존 분석 요청]\n{user_input}\n\n"
            f"[수정 요청 사항]\n{feedback}\n\n"
            "위 수정 요청 사항을 반영해서 분석 플랜을 다시 작성해주세요."
        )
    return f"다음 분석 요청에 대한 플랜을 작성해주세요:\n\n{user_input}"


def _parse_plan_json(raw: str) -> dict[str, Any] | None:
    """LLM 응답에서 JSON을 파싱한다.

    순수 JSON 응답 외에도 마크다운 코드블록으로 감싸진 경우를 방어적으로 처리한다.
    파싱 실패 시 None을 반환한다.
    """
    # 마크다운 코드블록 제거 (방어 처리)
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()

    # JSON 객체 추출 (앞뒤 불필요한 텍스트 제거)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


@traced("plan_node")
async def plan_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """사용자 입력 기반으로 전체 분석 플랜을 수립한다.

    hitl_feedback이 있으면 피드백을 반영해 플랜을 재수립하고,
    없으면 user_input 기반으로 신규 플랜을 생성한다.

    State 입력:
        user_input: 사용자 분석 요청
        hitl_feedback: (revise 시) 수정 지시사항
        plan: (revise 시) 기존 플랜

    State 출력:
        plan: 전체 분석 플랜 dict
        current_step: "planning"
        hitl_action: None (초기화)
        hitl_feedback: None (초기화)
        messages: LLM 대화 이력 추가 (HumanMessage + AIMessage)
        error: 파싱 실패 시 에러 메시지, 성공 시 None
    """
    client = get_client()
    model = get_model_name()

    user_input: str = state["user_input"]
    feedback: str | None = state.get("hitl_feedback")

    user_message_text = _build_user_message(user_input, feedback)

    # revise 케이스: 기존 플랜을 컨텍스트로 포함
    existing_plan: dict[str, Any] = state.get("plan") or {}
    messages_for_llm: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
    ]
    if existing_plan and feedback:
        messages_for_llm.append({
            "role": "user",
            "content": (
                f"[기존 플랜]\n{json.dumps(existing_plan, ensure_ascii=False, indent=2)}\n\n"
                + user_message_text
            ),
        })
    else:
        messages_for_llm.append({"role": "user", "content": user_message_text})

    response = await client.chat.completions.create(
        model=model,
        messages=messages_for_llm,
        temperature=0.3,
    )

    raw_content: str = response.choices[0].message.content or ""

    plan = _parse_plan_json(raw_content)

    # add_messages reducer가 기존 messages에 자동 누적한다.
    new_messages = [
        HumanMessage(content=user_message_text),
        AIMessage(content=raw_content),
    ]

    if plan is None:
        return {
            "current_step": "planning",
            "plan": existing_plan,
            "hitl_action": None,
            "hitl_feedback": None,
            "messages": new_messages,
            "error": f"[plan_node] LLM 응답 JSON 파싱 실패. 원본 응답:\n{raw_content}",
        }

    return {
        "current_step": "planning",
        "plan": plan,
        "hitl_action": None,
        "hitl_feedback": None,
        "messages": new_messages,
        "error": None,
    }
