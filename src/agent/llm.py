"""Qwen3 LLM 클라이언트 설정 모듈.

OpenAI 호환 API를 통해 Qwen3 모델에 접근하는 AsyncOpenAI 클라이언트를 제공한다.
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI


def get_llm_client() -> AsyncOpenAI:
    """AsyncOpenAI 클라이언트 인스턴스를 반환한다.

    환경변수:
        OPENAI_API_KEY: API 인증 키 (기본값: "none")
        OPENAI_BASE_URL: OpenAI 호환 API 엔드포인트

    Returns:
        AsyncOpenAI: Qwen3 모델용 비동기 클라이언트
    """
    return AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "none"),
        base_url=os.environ.get("OPENAI_BASE_URL", "http://model.frodo.com/v1"),
    )


def get_model_name() -> str:
    """사용할 LLM 모델명을 반환한다.

    환경변수:
        OPENAI_MODEL: 모델명 (기본값: "qwen3-vl-30b-fp8")

    Returns:
        str: 모델명 문자열
    """
    return os.environ.get("OPENAI_MODEL", "qwen3-vl-30b-fp8")


# 모듈 수준 싱글톤 (애플리케이션 생명주기 동안 재사용)
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """모듈 수준 싱글톤 클라이언트를 반환한다."""
    global _client
    if _client is None:
        _client = get_llm_client()
    return _client
