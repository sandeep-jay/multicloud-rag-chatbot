"""GCP Vertex AI LLM provider wiring tests."""

from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.providers.llm.gcp import GcpLlmProvider


def test_gcp_llm_get_llm_wiring():
    fake_llm = MagicMock()
    with (
        patch('backend.app.services.providers.llm.gcp.settings') as s,
        patch(
            'backend.app.services.providers.llm.gcp.ChatGoogleGenerativeAI',
            return_value=fake_llm,
        ) as ctor,
    ):
        s.GCP_PROJECT_ID = 'my-project'
        s.GCP_LOCATION = 'us-central1'
        s.GCP_LLM_MODEL = 'gemini-2.5-flash'
        s.TEMPERATURE = 0.2
        s.MAX_TOKENS = 123
        p = GcpLlmProvider()
        out = p.get_llm()
        assert out is fake_llm
        ctor.assert_called_once()
        kwargs = ctor.call_args.kwargs
        assert kwargs['model'] == 'gemini-2.5-flash'
        assert kwargs['project'] == 'my-project'
        assert kwargs['location'] == 'us-central1'
        assert kwargs['vertexai'] is True
        assert kwargs['temperature'] == 0.2
        assert kwargs['max_output_tokens'] == 123


def test_gcp_llm_missing_config_raises():
    with patch('backend.app.services.providers.llm.gcp.settings') as s:
        s.GCP_PROJECT_ID = None
        s.GCP_LLM_MODEL = None
        with pytest.raises(ValueError, match='GCP LLM missing config'):
            GcpLlmProvider()
