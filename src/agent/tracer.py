"""Phoenix tracing 설정 모듈.

Arize Phoenix SDK를 이용해 OpenTelemetry 기반 tracing을 초기화한다.
PostgreSQL을 storage backend로 사용하며, 모든 노드의 LLM 호출·Jupyter 실행 결과를
span으로 캡처한다.
"""

from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable, TypeVar

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
import phoenix as px


_tracer: trace.Tracer | None = None
_initialized: bool = False


def init_tracing(project_name: str = "dtest-agent") -> None:
    """Phoenix tracing을 초기화한다.

    환경변수:
        PHOENIX_COLLECTOR_ENDPOINT: Phoenix OTLP 수집 엔드포인트
        OTEL_EXPORTER_OTLP_HEADERS: OTLP exporter 인증 헤더
        PHOENIX_API_KEY: Phoenix API 키

    Args:
        project_name: Phoenix 프로젝트명
    """
    global _tracer, _initialized

    if _initialized:
        return

    endpoint = os.environ.get(
        "PHOENIX_COLLECTOR_ENDPOINT",
        "http://phoenix.frodo.com/v1/traces",
    )

    # OTLP HTTP exporter (Phoenix 서버로 span 전송)
    headers_raw = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "")
    headers: dict[str, str] = {}
    for item in headers_raw.split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            headers[k.strip()] = v.strip()

    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _tracer = trace.get_tracer(project_name)
    _initialized = True


def get_tracer() -> trace.Tracer:
    """초기화된 Tracer 인스턴스를 반환한다.

    Returns:
        trace.Tracer: OpenTelemetry Tracer
    """
    if not _initialized:
        init_tracing()
    assert _tracer is not None
    return _tracer


F = TypeVar("F", bound=Callable[..., Any])


def traced(span_name: str | None = None) -> Callable[[F], F]:
    """노드 함수에 OpenTelemetry span을 감싸는 데코레이터.

    Args:
        span_name: span 이름 (None이면 함수명 사용)

    Returns:
        데코레이터 함수
    """
    def decorator(func: F) -> F:
        import asyncio

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            name = span_name or func.__name__
            with tracer.start_as_current_span(name) as span:
                # 첫 번째 인자가 AgentState인 경우 current_step을 attribute로 기록
                if args and isinstance(args[0], dict):
                    state = args[0]
                    span.set_attribute("agent.step", state.get("current_step", ""))
                    span.set_attribute("agent.user_input", state.get("user_input", ""))
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            name = span_name or func.__name__
            with tracer.start_as_current_span(name) as span:
                if args and isinstance(args[0], dict):
                    state = args[0]
                    span.set_attribute("agent.step", state.get("current_step", ""))
                    span.set_attribute("agent.user_input", state.get("user_input", ""))
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator
