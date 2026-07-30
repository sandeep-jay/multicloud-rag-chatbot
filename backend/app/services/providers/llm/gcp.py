"""GCP Vertex AI Gemini chat LLM provider."""

from langchain_google_genai import ChatGoogleGenerativeAI

from backend.app.core.config_manager import settings
from backend.app.services.providers.base import BaseLlmProvider


class GcpLlmProvider(BaseLlmProvider):
    name = 'gcp'

    def __init__(self) -> None:
        self._validate_config()

    def _validate_config(self) -> None:
        missing = []
        for key in ('GCP_PROJECT_ID', 'GCP_LLM_MODEL'):
            if not getattr(settings, key, None):
                missing.append(key)
        if missing:
            raise ValueError(f'GCP LLM missing config: {missing}')

    def _llm_kwargs(self, streaming: bool = False, callbacks: list | None = None) -> dict:  # noqa: FBT001
        kwargs = dict(
            model=settings.GCP_LLM_MODEL,
            project=settings.GCP_PROJECT_ID,
            location=getattr(settings, 'GCP_LOCATION', 'us-central1'),
            vertexai=True,
            temperature=settings.TEMPERATURE,
            max_output_tokens=settings.MAX_TOKENS,
        )
        if streaming:
            kwargs['streaming'] = True
        if callbacks:
            kwargs['callbacks'] = callbacks
        return kwargs

    def get_llm(self):
        return ChatGoogleGenerativeAI(**self._llm_kwargs())

    def get_streaming_llm(self, callbacks: list | None = None):
        return ChatGoogleGenerativeAI(**self._llm_kwargs(streaming=True, callbacks=callbacks))
