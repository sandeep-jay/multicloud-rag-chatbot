"""Wire RAGAS judge LLM/embeddings to AWS or Azure (no OpenAI default)."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from backend.app.core.config_manager import settings

logger = logging.getLogger(__name__)


def resolve_judge_provider() -> str:
    """Provider for RAGAS scoring: RAGAS_LLM_PROVIDER, else LLM_PROVIDER."""
    explicit = os.environ.get('RAGAS_LLM_PROVIDER', '').strip().lower()
    if explicit:
        return explicit
    return str(getattr(settings, 'LLM_PROVIDER', 'mock')).strip().lower()


def judge_provider_configured() -> bool:
    provider = resolve_judge_provider()
    if provider not in ('aws', 'azure', 'gcp'):
        return False
    try:
        from backend.app.services.providers import get_llm_provider

        return not get_llm_provider().is_mock
    except Exception:
        return False


def _require_cloud_provider() -> str:
    provider = resolve_judge_provider()
    if provider not in ('aws', 'azure', 'gcp'):
        raise ValueError(
            f'RAGAS judge requires LLM_PROVIDER or RAGAS_LLM_PROVIDER to be aws, azure, or gcp (got {provider!r}).',
        )
    return provider


@lru_cache(maxsize=1)
def get_ragas_judge_llm():
    """LangChain chat model for RAGAS metrics (streaming required for ragas async executor)."""
    _require_cloud_provider()
    from backend.app.services.providers import get_llm_provider

    provider = get_llm_provider()
    if provider.is_mock:
        raise ValueError('RAGAS judge LLM is mock — configure aws/azure/gcp credentials and LLM_PROVIDER.')
    return provider.get_streaming_llm()


@lru_cache(maxsize=1)
def get_ragas_judge_embeddings():
    """LangChain embeddings for RAGAS (Azure OpenAI or Bedrock)."""
    provider = _require_cloud_provider()
    if provider == 'azure':
        from langchain_openai import AzureOpenAIEmbeddings

        deployment = getattr(settings, 'AZURE_EMBEDDING_DEPLOYMENT', None) or 'text-embedding-ada-002'
        return AzureOpenAIEmbeddings(
            azure_deployment=deployment,
            azure_endpoint=str(settings.AZURE_OPENAI_ENDPOINT).rstrip('/'),
            api_key=(settings.AZURE_OPENAI_API_KEY.get_secret_value() if settings.AZURE_OPENAI_API_KEY else None),
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    if provider == 'gcp':
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model='text-embedding-005',
            project=settings.GCP_PROJECT_ID,
            location=getattr(settings, 'GCP_LOCATION', 'us-central1'),
            vertexai=True,
        )
        from langchain_aws import BedrockEmbeddings

    model_id = getattr(settings, 'BEDROCK_EMBEDDING_MODEL_ID', None) or 'amazon.titan-embed-text-v1'
    return BedrockEmbeddings(
        model_id=model_id,
        region_name=settings.AWS_REGION,
    )


def metric_score(results, metric_name: str) -> float:
    """Return mean score for a metric from ragas evaluate() (handles per-sample lists and NaNs)."""
    import math

    import numpy as np

    try:
        raw = results[metric_name]
    except (KeyError, TypeError):
        raw = getattr(results, metric_name, None)
    if raw is None:
        raise KeyError(f'Metric {metric_name!r} not in RAGAS results')

    if isinstance(raw, int | float):
        val = float(raw)
        if math.isnan(val):
            raise ValueError(f'Metric {metric_name!r} is NaN')
        return val

    arr = np.asarray(raw, dtype=float).flatten()
    if arr.size == 0:
        raise ValueError(f'Metric {metric_name!r} has no scores')
    mean = float(np.nanmean(arr))
    if math.isnan(mean):
        model = getattr(settings, 'BEDROCK_MODEL_ID', '?')
        raise ValueError(
            f'Metric {metric_name!r}: all {arr.size} samples failed. '
            f'Check BEDROCK_MODEL_ID ({model!r}) is active in {settings.AWS_REGION} '
            '(EOL models, or use us./eu. inference profile prefix for Claude 3.5+).',
        )
    failed = int(np.isnan(arr).sum())
    if failed:
        logger.warning('Metric %s: %d/%d samples failed; mean uses successful rows only', metric_name, failed, arr.size)
    return mean


def run_ragas_evaluate(dataset, metrics):
    """Run ragas.evaluate with cloud-contained LLM + embeddings."""
    from ragas import evaluate

    names = [getattr(m, 'name', str(m)) for m in metrics]
    logger.info(
        'RAGAS scoring %d samples — metrics: %s (judge via %s, model %s)...',
        len(dataset),
        names,
        resolve_judge_provider(),
        getattr(settings, 'BEDROCK_MODEL_ID', getattr(settings, 'AZURE_OPENAI_DEPLOYMENT', getattr(settings, 'GCP_LLM_MODEL', 'n/a'))),
    )
    return evaluate(
        dataset,
        metrics=metrics,
        llm=get_ragas_judge_llm(),
        embeddings=get_ragas_judge_embeddings(),
        show_progress=True,
    )
