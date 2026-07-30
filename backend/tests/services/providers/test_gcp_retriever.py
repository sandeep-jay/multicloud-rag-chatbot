"""GCP Vertex AI Search retriever tests."""

from unittest.mock import MagicMock, patch

import pytest
from langchain.schema import Document

from backend.app.services.providers.retriever.gcp import (
    GcpRetrieverProvider,
    GcpSearchRetriever,
    _normalize_document,
)


def test_normalize_document_maps_struct_data():
    doc = Document(
        page_content='hello',
        metadata={
            'structData': {
                'kb_url': 'https://kb.example/1',
                'kb_number': 'KB-42',
                'kb_category': 'tools',
                'short_description': 'Fix login',
            },
            'relevanceScore': 0.88,
        },
    )
    out = _normalize_document(doc)
    assert out.page_content == 'hello'
    assert out.metadata['kb_url'] == 'https://kb.example/1'
    assert out.metadata['kb_number'] == 'KB-42'
    assert out.metadata['score'] == 0.88


def test_gcp_search_retriever_normalizes_results():
    inner = MagicMock()
    inner.invoke.return_value = [Document(page_content='chunk', metadata={'kb_url': 'u', 'kb_number': 'KB-1', 'score': 0.5})]
    r = GcpSearchRetriever(inner=inner)
    docs = r.get_relevant_documents('q')
    assert len(docs) == 1
    assert docs[0].metadata['kb_number'] == 'KB-1'
    inner.invoke.assert_called_once_with('q')


def test_gcp_retriever_provider_get_retriever():
    with (
        patch('backend.app.services.providers.retriever.gcp.settings') as s,
        patch('backend.app.services.providers.retriever.gcp.VertexAISearchRetriever') as ctor,
        patch('backend.app.services.providers.retriever.gcp.retrieval_candidate_count', return_value=5),
    ):
        s.GCP_PROJECT_ID = 'proj'
        s.VERTEX_SEARCH_LOCATION = 'global'
        s.VERTEX_SEARCH_DATA_STORE_ID = 'ds-123'
        s.VERTEX_SEARCH_FILTER = None
        s.RETRIEVER_NUMBER_OF_RESULTS = 5
        fake_inner = MagicMock()
        ctor.return_value = fake_inner
        p = GcpRetrieverProvider()
        ret = p.get_retriever()
        assert isinstance(ret, GcpSearchRetriever)
        ctor.assert_called_once()
        kwargs = ctor.call_args.kwargs
        assert kwargs['project_id'] == 'proj'
        assert kwargs['data_store_id'] == 'ds-123'
        assert kwargs['max_documents'] == 5


def test_gcp_retriever_placeholder_datastore_raises():
    with patch('backend.app.services.providers.retriever.gcp.settings') as s:
        s.VERTEX_SEARCH_DATA_STORE_ID = 'your-data-store-id'
        with pytest.raises(ValueError, match='VERTEX_SEARCH_DATA_STORE_ID'):
            GcpRetrieverProvider()
