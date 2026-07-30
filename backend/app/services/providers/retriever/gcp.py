"""GCP Vertex AI Search retriever provider."""

from __future__ import annotations

from langchain.schema import Document
from langchain.schema.retriever import BaseRetriever
from langchain_google_community import VertexAISearchRetriever
from pydantic import PrivateAttr

from backend.app.core.config_manager import settings
from backend.app.services.providers.base import BaseRetrieverProvider
from backend.app.services.rerank import retrieval_candidate_count

_PLACEHOLDER_DATA_STORE_IDS = frozenset(
    {
        'your-data-store-id',
        'your_data_store_id',
        'none',
        'changeme',
        'placeholder',
        'disabled',
        'mock',
        'xxxxx',
    }
)


def _data_store_implies_mock(data_store_id: str | None) -> bool:
    if data_store_id is None:
        return True
    normalized = data_store_id.strip()
    if not normalized:
        return True
    return normalized.lower() in _PLACEHOLDER_DATA_STORE_IDS


def _normalize_document(doc: Document) -> Document:
    """Map Vertex AI Search metadata to the app's KB source schema."""
    meta = dict(doc.metadata or {})
    struct = meta.get('structData') or meta.get('struct_data') or {}
    if not isinstance(struct, dict):
        struct = {}

    def pick(*keys: str, default: str = '') -> str:
        for key in keys:
            if key in struct and struct[key] not in (None, ''):
                return str(struct[key])
            if key in meta and meta[key] not in (None, ''):
                return str(meta[key])
        return default

    score = meta.get('score')
    if score is None:
        score = meta.get('relevanceScore', meta.get('relevance_score'))

    normalized = {
        'kb_url': pick('kb_url', 'url', 'link', default='#'),
        'kb_number': pick('kb_number', 'kbNumber', 'id', default='N/A'),
        'kb_category': pick('kb_category', 'kbCategory', 'category'),
        'short_description': pick('short_description', 'shortDescription', 'title', 'name'),
        'score': score,
        'source': pick('source', default='vertex_ai_search'),
    }
    return Document(page_content=doc.page_content, metadata=normalized)


class GcpSearchRetriever(BaseRetriever):
    _inner: BaseRetriever = PrivateAttr()

    def __init__(self, inner: BaseRetriever, **kwargs) -> None:
        super().__init__(**kwargs)
        object.__setattr__(self, '_inner', inner)

    def _get_relevant_documents(self, query: str, **_kwargs) -> list[Document]:
        docs = self._inner.invoke(query)
        return [_normalize_document(doc) for doc in docs]


class GcpRetrieverProvider(BaseRetrieverProvider):
    name = 'gcp'

    def __init__(self) -> None:
        if _data_store_implies_mock(settings.VERTEX_SEARCH_DATA_STORE_ID):
            raise ValueError('VERTEX_SEARCH_DATA_STORE_ID missing or placeholder')
        if not settings.GCP_PROJECT_ID:
            raise ValueError('GCP_PROJECT_ID missing')
        self._retriever = self._build_retriever()

    def _build_retriever(self) -> GcpSearchRetriever:
        kwargs = dict(
            project_id=settings.GCP_PROJECT_ID,
            location_id=getattr(settings, 'VERTEX_SEARCH_LOCATION', 'global'),
            data_store_id=settings.VERTEX_SEARCH_DATA_STORE_ID,
            max_documents=retrieval_candidate_count(),
        )
        search_filter = getattr(settings, 'VERTEX_SEARCH_FILTER', None)
        if search_filter and str(search_filter).strip():
            kwargs['filter'] = str(search_filter).strip()
        inner = VertexAISearchRetriever(**kwargs)
        return GcpSearchRetriever(inner=inner)

    def get_retriever(self):
        return self._retriever
