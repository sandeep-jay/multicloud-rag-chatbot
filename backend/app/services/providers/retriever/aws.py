"""AWS Bedrock Knowledge Base retriever provider."""

from langchain_aws import AmazonKnowledgeBasesRetriever

from backend.app.core.config_manager import settings
from backend.app.services.bedrock import BedrockService
from backend.app.services.providers.base import BaseRetrieverProvider
from backend.app.services.rerank import retrieval_candidate_count
from backend.app.services.retrieval import build_bedrock_vector_filter

# KB IDs that commonly appear in .env examples — treat as "not configured".
_PLACEHOLDER_KB_IDS = frozenset(
    {
        'your_knowledge_base_id',
        'your-knowledge-base-id',
        'none',
        'changeme',
        'placeholder',
        'disabled',
        'mock',
        'xxxxx',
    }
)


def _kb_id_implies_mock(kb_id: str | None) -> bool:
    if kb_id is None:
        return True
    normalized = kb_id.strip()
    if not normalized:
        return True
    return normalized.lower() in _PLACEHOLDER_KB_IDS


class AwsRetrieverProvider(BaseRetrieverProvider):
    name = 'aws'

    def __init__(self, bedrock_service: BedrockService | None = None, bedrock_client=None) -> None:
        if _kb_id_implies_mock(settings.BEDROCK_KNOWLEDGE_BASE_ID):
            raise ValueError('BEDROCK_KNOWLEDGE_BASE_ID missing or placeholder')
        if bedrock_service is not None:
            self._bedrock = bedrock_service
        elif bedrock_client is not None:
            self._bedrock = BedrockService(bedrock_client=bedrock_client)
        else:
            self._bedrock = BedrockService()
        self._retriever = self._build_retriever()

    def _build_retriever(self):
        agent_client = self._bedrock.get_agent_client()
        kb_type = (getattr(settings, 'BEDROCK_KB_TYPE', 'vector') or 'vector').strip().lower()
        retriever_kwargs = {
            'knowledge_base_id': settings.BEDROCK_KNOWLEDGE_BASE_ID,
            'region_name': settings.AWS_REGION,
            'client': agent_client,
        }
        if kb_type != 'managed':
            vector_search_configuration = {
                'numberOfResults': retrieval_candidate_count(),
                'overrideSearchType': settings.RETRIEVER_SEARCH_TYPE,
            }
            bedrock_filter = build_bedrock_vector_filter()
            if bedrock_filter:
                vector_search_configuration['filter'] = bedrock_filter
            retriever_kwargs['retrieval_config'] = {
                'vectorSearchConfiguration': vector_search_configuration,
            }
        return AmazonKnowledgeBasesRetriever(**retriever_kwargs)

    def get_retriever(self):
        return self._retriever
