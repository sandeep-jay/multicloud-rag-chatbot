"""RAG LLM and retriever provider registries (config-driven)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.core.config_manager import settings

from .llm.aws import AwsLlmProvider
from .llm.mock import MockLlmProvider
from .retriever.aws import AwsRetrieverProvider
from .retriever.mock import MockRetrieverProvider

if TYPE_CHECKING:
    from collections.abc import Callable

    from .base import BaseLlmProvider, BaseRetrieverProvider

_LLM_REGISTRY: dict[str, Callable[[], BaseLlmProvider]] = {}
_RET_REGISTRY: dict[str, Callable[[], BaseRetrieverProvider]] = {}


def register_llm(name: str, factory: Callable[[], BaseLlmProvider]) -> None:
    _LLM_REGISTRY[name.strip().lower()] = factory


def register_retriever(name: str, factory: Callable[[], BaseRetrieverProvider]) -> None:
    _RET_REGISTRY[name.strip().lower()] = factory


def _resolve_name(side_default: str, side_var: str) -> str:
    if getattr(settings, 'RAG_FORCE_MOCK', False):
        return 'mock'
    val = getattr(settings, side_var, None)
    if val is not None and str(val).strip():
        return str(val).strip().lower()
    shortcut = getattr(settings, 'RAG_PROVIDER', None)
    if shortcut is not None and str(shortcut).strip():
        return str(shortcut).strip().lower()
    return side_default


def get_llm_provider() -> BaseLlmProvider:
    name = _resolve_name('mock', 'LLM_PROVIDER')
    factory = _LLM_REGISTRY.get(name)
    if factory is None:
        return MockLlmProvider()
    return factory()


def get_retriever_provider() -> BaseRetrieverProvider:
    name = _resolve_name('mock', 'RETRIEVER_PROVIDER')
    factory = _RET_REGISTRY.get(name)
    if factory is None:
        return MockRetrieverProvider()
    return factory()


def _azure_llm_factory() -> BaseLlmProvider:
    from .llm.azure import AzureLlmProvider

    return AzureLlmProvider.create_or_mock(MockLlmProvider)


def _gcp_llm_factory() -> BaseLlmProvider:
    from .llm.gcp import GcpLlmProvider

    return GcpLlmProvider.create_or_mock(MockLlmProvider)


def _gcp_retriever_factory() -> BaseRetrieverProvider:
    from .retriever.gcp import GcpRetrieverProvider

    return GcpRetrieverProvider.create_or_mock(MockRetrieverProvider)


def _azure_retriever_factory() -> BaseRetrieverProvider:
    from .retriever.azure import AzureRetrieverProvider

    return AzureRetrieverProvider.create_or_mock(MockRetrieverProvider)


register_llm('aws', lambda: AwsLlmProvider.create_or_mock(MockLlmProvider))
register_llm('azure', _azure_llm_factory)
register_llm('gcp', _gcp_llm_factory)
register_llm('mock', MockLlmProvider)

register_retriever('aws', lambda: AwsRetrieverProvider.create_or_mock(MockRetrieverProvider))
register_retriever('azure', _azure_retriever_factory)
register_retriever('gcp', _gcp_retriever_factory)
register_retriever('mock', MockRetrieverProvider)
