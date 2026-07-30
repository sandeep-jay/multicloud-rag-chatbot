"""AWS Bedrock retriever provider tests."""

from unittest.mock import MagicMock, patch

from backend.app.services.providers.retriever.aws import AwsRetrieverProvider


def test_managed_kb_omits_vector_search_configuration():
    mock_client = MagicMock()
    with (
        patch('backend.app.services.providers.retriever.aws.settings') as mock_settings,
        patch('backend.app.services.providers.retriever.aws.AmazonKnowledgeBasesRetriever') as mock_retriever_cls,
        patch('backend.app.services.providers.retriever.aws.BedrockService') as mock_bedrock_cls,
    ):
        mock_settings.BEDROCK_KNOWLEDGE_BASE_ID = 'KB123'
        mock_settings.BEDROCK_KB_TYPE = 'managed'
        mock_settings.AWS_REGION = 'us-west-2'
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'
        mock_bedrock = mock_bedrock_cls.return_value
        mock_bedrock.get_agent_client.return_value = mock_client

        AwsRetrieverProvider(bedrock_service=mock_bedrock)

        _, kwargs = mock_retriever_cls.call_args
        assert 'retrieval_config' not in kwargs
        assert kwargs['knowledge_base_id'] == 'KB123'


def test_vector_kb_includes_vector_search_configuration():
    mock_client = MagicMock()
    with (
        patch('backend.app.services.providers.retriever.aws.settings') as mock_settings,
        patch('backend.app.services.providers.retriever.aws.AmazonKnowledgeBasesRetriever') as mock_retriever_cls,
        patch('backend.app.services.providers.retriever.aws.BedrockService') as mock_bedrock_cls,
        patch('backend.app.services.providers.retriever.aws.retrieval_candidate_count', return_value=5),
        patch('backend.app.services.providers.retriever.aws.build_bedrock_vector_filter', return_value=None),
    ):
        mock_settings.BEDROCK_KNOWLEDGE_BASE_ID = 'KB456'
        mock_settings.BEDROCK_KB_TYPE = 'vector'
        mock_settings.AWS_REGION = 'us-west-2'
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'
        mock_bedrock = mock_bedrock_cls.return_value
        mock_bedrock.get_agent_client.return_value = mock_client

        AwsRetrieverProvider(bedrock_service=mock_bedrock)

        _, kwargs = mock_retriever_cls.call_args
        assert 'vectorSearchConfiguration' in kwargs['retrieval_config']
        assert kwargs['retrieval_config']['vectorSearchConfiguration']['numberOfResults'] == 5
