"""Tests for provider registry and env resolution."""

from unittest.mock import MagicMock, patch

from backend.app.services.providers import (
    get_llm_provider,
    get_retriever_provider,
    register_llm,
)
from backend.app.services.providers.llm.mock import MockLlmProvider
from backend.app.services.providers.retriever.mock import MockRetrieverProvider


def _patch_settings(**kwargs):
    return patch.multiple(
        'backend.app.services.providers.settings',
        **kwargs,
    )


def test_llm_mock_default():
    with _patch_settings(RAG_FORCE_MOCK=False, RAG_PROVIDER=None, LLM_PROVIDER='mock', RETRIEVER_PROVIDER='mock'):
        p = get_llm_provider()
        assert isinstance(p, MockLlmProvider)


def test_retriever_mock_default():
    with _patch_settings(RAG_FORCE_MOCK=False, RAG_PROVIDER=None, LLM_PROVIDER='mock', RETRIEVER_PROVIDER='mock'):
        p = get_retriever_provider()
        assert isinstance(p, MockRetrieverProvider)


def test_rag_force_mock_overrides():
    with _patch_settings(RAG_FORCE_MOCK=True, RAG_PROVIDER='azure', LLM_PROVIDER='azure', RETRIEVER_PROVIDER='azure'):
        assert isinstance(get_llm_provider(), MockLlmProvider)
        assert isinstance(get_retriever_provider(), MockRetrieverProvider)


def test_explicit_providers_override_rag_provider_shortcut():
    """LLM_PROVIDER / RETRIEVER_PROVIDER win over RAG_PROVIDER when both are set."""
    with (
        _patch_settings(RAG_FORCE_MOCK=False, RAG_PROVIDER='azure', LLM_PROVIDER='aws', RETRIEVER_PROVIDER='aws'),
        patch('backend.app.services.providers.llm.aws.AwsLlmProvider.create_or_mock') as m_llm,
        patch('backend.app.services.providers.retriever.aws.AwsRetrieverProvider.create_or_mock') as m_ret,
    ):
        fake_llm = MagicMock()
        fake_llm.is_mock = False
        fake_llm.name = 'aws'
        fake_ret = MagicMock()
        fake_ret.is_mock = False
        fake_ret.name = 'aws'
        m_llm.return_value = fake_llm
        m_ret.return_value = fake_ret
        assert get_llm_provider() is fake_llm
        assert get_retriever_provider() is fake_ret


def test_rag_provider_shortcut_when_side_vars_unset():
    with (
        _patch_settings(RAG_FORCE_MOCK=False, RAG_PROVIDER='azure', LLM_PROVIDER=None, RETRIEVER_PROVIDER=None),
        patch('backend.app.services.providers.llm.azure.AzureLlmProvider.create_or_mock') as m_llm,
        patch(
            'backend.app.services.providers.retriever.azure.AzureRetrieverProvider.create_or_mock',
        ) as m_ret,
    ):
        fake_llm = MagicMock()
        fake_llm.is_mock = False
        fake_llm.name = 'azure'
        fake_ret = MagicMock()
        fake_ret.is_mock = False
        fake_ret.name = 'azure'
        m_llm.return_value = fake_llm
        m_ret.return_value = fake_ret
        assert get_llm_provider() is fake_llm
        assert get_retriever_provider() is fake_ret


def test_unknown_provider_falls_back_to_mock():
    with _patch_settings(RAG_FORCE_MOCK=False, RAG_PROVIDER=None, LLM_PROVIDER='not-a-real-provider', RETRIEVER_PROVIDER='mock'):
        assert isinstance(get_llm_provider(), MockLlmProvider)


def test_register_llm_extensibility():
    class FakeLlm(MockLlmProvider):
        name = 'foo'
        is_mock = False

        def get_llm(self):
            return MagicMock()

    register_llm('ext_llm_registry_test_xyz', FakeLlm)
    with _patch_settings(RAG_FORCE_MOCK=False, RAG_PROVIDER=None, LLM_PROVIDER='ext_llm_registry_test_xyz', RETRIEVER_PROVIDER='mock'):
        p = get_llm_provider()
        assert p.name == 'foo'


def test_aws_retriever_placeholder_kb_falls_back_to_mock_retriever():
    with _patch_settings(
        RAG_FORCE_MOCK=False,
        RAG_PROVIDER=None,
        LLM_PROVIDER='mock',
        RETRIEVER_PROVIDER='aws',
        BEDROCK_KNOWLEDGE_BASE_ID='your_knowledge_base_id',
    ):
        p = get_retriever_provider()
        assert isinstance(p, MockRetrieverProvider)


def test_decoupled_aws_llm_azure_retriever_mixed():
    """LLM_PROVIDER=aws and RETRIEVER_PROVIDER=azure should call both factories."""
    with (
        _patch_settings(
            RAG_FORCE_MOCK=False,
            RAG_PROVIDER=None,
            LLM_PROVIDER='aws',
            RETRIEVER_PROVIDER='azure',
            BEDROCK_KNOWLEDGE_BASE_ID='real-kb-id',
        ),
        patch('backend.app.services.providers.llm.aws.AwsLlmProvider.create_or_mock') as m_llm,
        patch(
            'backend.app.services.providers.retriever.azure.AzureRetrieverProvider.create_or_mock',
        ) as m_ret,
    ):
        fake_llm = MagicMock()
        fake_llm.is_mock = False
        fake_llm.name = 'aws'
        fake_ret = MagicMock()
        fake_ret.is_mock = False
        fake_ret.name = 'azure'
        m_llm.return_value = fake_llm
        m_ret.return_value = fake_ret
        assert get_llm_provider() is fake_llm
        assert get_retriever_provider() is fake_ret


def test_gcp_provider_shortcut_when_side_vars_unset():
    with (
        _patch_settings(RAG_FORCE_MOCK=False, RAG_PROVIDER='gcp', LLM_PROVIDER=None, RETRIEVER_PROVIDER=None),
        patch('backend.app.services.providers.llm.gcp.GcpLlmProvider.create_or_mock') as m_llm,
        patch('backend.app.services.providers.retriever.gcp.GcpRetrieverProvider.create_or_mock') as m_ret,
    ):
        fake_llm = MagicMock()
        fake_llm.is_mock = False
        fake_llm.name = 'gcp'
        fake_ret = MagicMock()
        fake_ret.is_mock = False
        fake_ret.name = 'gcp'
        m_llm.return_value = fake_llm
        m_ret.return_value = fake_ret
        assert get_llm_provider() is fake_llm
        assert get_retriever_provider() is fake_ret


def test_gcp_retriever_placeholder_datastore_falls_back_to_mock():
    with _patch_settings(
        RAG_FORCE_MOCK=False,
        RAG_PROVIDER=None,
        LLM_PROVIDER='mock',
        RETRIEVER_PROVIDER='gcp',
        VERTEX_SEARCH_DATA_STORE_ID='your-data-store-id',
    ):
        p = get_retriever_provider()
        assert isinstance(p, MockRetrieverProvider)
