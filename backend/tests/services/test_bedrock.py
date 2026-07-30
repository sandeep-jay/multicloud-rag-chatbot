"""
Copyright ©2025. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from backend.app.services.aws_client import AWSClientService
from backend.app.services.bedrock import BedrockService


@pytest.fixture()
def mock_bedrock_client():
    return MagicMock()


@pytest.fixture()
def mock_aws_client():
    mock_client = MagicMock(spec=AWSClientService)
    mock_client.get_client.return_value = MagicMock()
    return mock_client


@pytest.fixture()
def mock_langsmith_client():
    return MagicMock()


def test_initialize_bedrock_with_aws_client(mock_aws_client):
    """Test initialization of BedrockService with AWS client."""
    with patch('backend.app.services.bedrock.settings') as mock_settings:
        mock_settings.BEDROCK_MODEL_ID = 'anthropic.claude-instant-v1'
        mock_settings.LANGCHAIN_API_KEY = None
        mock_settings.AWS_REGION = 'us-east-1'
        mock_settings.MAX_TOKENS = 750
        mock_settings.TOP_K = 10
        mock_settings.TEMPERATURE = 0.3
        mock_settings.RETRIEVER_NUMBER_OF_RESULTS = 6
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'

        service = BedrockService(aws_client=mock_aws_client)

        assert service is not None
        assert service.aws_client == mock_aws_client
        mock_aws_client.get_client.assert_called_once_with('bedrock-runtime')
        assert service.client == mock_aws_client.get_client.return_value


def test_initialize_with_role_arn():
    """Test initialization of BedrockService with role ARN."""
    with (
        patch('backend.app.services.bedrock.settings') as mock_settings,
        patch('backend.app.services.bedrock.AWSClientService') as mock_aws_client_class,
    ):
        # Configure settings and mock
        mock_settings.BEDROCK_MODEL_ID = 'amazon.titan-text-express-v1'
        mock_settings.LANGCHAIN_API_KEY = None
        mock_settings.AWS_REGION = 'us-east-1'
        mock_settings.MAX_TOKENS = 750
        mock_settings.TOP_K = 10
        mock_settings.TEMPERATURE = 0.3
        mock_settings.RETRIEVER_NUMBER_OF_RESULTS = 6
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'

        # Create a mock aws client instance
        mock_aws_client = MagicMock()
        mock_aws_client.get_client.return_value = MagicMock()
        mock_aws_client_class.return_value = mock_aws_client

        # Initialize with role ARN
        role_arn = 'arn:aws:iam::123456789012:role/test-role'
        service = BedrockService(role_arn=role_arn)

        # Verify AWSClientService was created with role ARN
        mock_aws_client_class.assert_called_once_with(
            region_name='us-east-1',
            role_arn=role_arn,
        )

        # Verify client was correctly obtained
        mock_aws_client.get_client.assert_called_once_with('bedrock-runtime')
        assert service.client == mock_aws_client.get_client.return_value


def test_initialize_with_provided_client(mock_bedrock_client):
    """Test initialization with provided client."""
    with patch('backend.app.services.bedrock.settings') as mock_settings:
        mock_settings.BEDROCK_MODEL_ID = 'anthropic.claude-v2'
        mock_settings.LANGCHAIN_API_KEY = None
        mock_settings.MAX_TOKENS = 750
        mock_settings.TOP_K = 10
        mock_settings.TEMPERATURE = 0.3
        mock_settings.RETRIEVER_NUMBER_OF_RESULTS = 6
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'

        service = BedrockService(bedrock_client=mock_bedrock_client)

        assert service is not None
        assert service.client == mock_bedrock_client
        assert service.aws_client is None


def test_generate_text(mock_bedrock_client):
    """Test generate_text method."""
    # Mock response
    mock_response = {
        'completion': 'This is a test response from Claude.',
    }
    encoded_response = json.dumps(mock_response).encode('utf-8')
    mock_bedrock_client.invoke_model.return_value = {
        'body': MagicMock(read=lambda: encoded_response),
    }

    # Create service instance
    with patch('backend.app.services.bedrock.settings') as mock_settings:
        mock_settings.BEDROCK_MODEL_ID = 'anthropic.claude-v2'
        mock_settings.LANGCHAIN_API_KEY = None
        mock_settings.MAX_TOKENS = 750
        mock_settings.TOP_K = 10
        mock_settings.TEMPERATURE = 0.3
        mock_settings.RETRIEVER_NUMBER_OF_RESULTS = 6
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'

        service = BedrockService(bedrock_client=mock_bedrock_client)

        # Call method
        response = service.generate_text('What is the capital of France?')

        # Assertions
        assert response == 'This is a test response from Claude.'
        mock_bedrock_client.invoke_model.assert_called_once()


def test_generate_text_with_params(mock_bedrock_client):
    """Test generate_text with custom parameters."""
    # Mock response
    mock_response = {
        'completion': 'This is a test response with custom parameters.',
    }
    encoded_response = json.dumps(mock_response).encode('utf-8')
    mock_bedrock_client.invoke_model.return_value = {
        'body': MagicMock(read=lambda: encoded_response),
    }

    # Create service instance
    with patch('backend.app.services.bedrock.settings') as mock_settings:
        mock_settings.BEDROCK_MODEL_ID = 'anthropic.claude-v2'
        mock_settings.LANGCHAIN_API_KEY = None
        mock_settings.MAX_TOKENS = 750
        mock_settings.TOP_K = 10
        mock_settings.TEMPERATURE = 0.3
        mock_settings.RETRIEVER_NUMBER_OF_RESULTS = 6
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'

        service = BedrockService(bedrock_client=mock_bedrock_client)

        # Call method with custom parameters
        response = service.generate_text(
            'What is the capital of France?',
            temperature=0.5,
            max_tokens=200,
        )

        # Assertions
        assert response == 'This is a test response with custom parameters.'

        # Verify the parameters were passed correctly
        call_args = mock_bedrock_client.invoke_model.call_args
        body_arg = json.loads(call_args.kwargs['body'])
        assert body_arg['temperature'] == 0.5
        assert body_arg['max_tokens'] == 200


def test_generate_text_error(mock_bedrock_client):
    """Test generate_text with an error."""
    mock_bedrock_client.invoke_model.side_effect = ClientError(
        {'Error': {'Code': 'ValidationException', 'Message': 'Test error'}},
        'InvokeModel',
    )

    with patch('backend.app.services.bedrock.settings') as mock_settings:
        mock_settings.BEDROCK_MODEL_ID = 'anthropic.claude-v2'
        mock_settings.LANGCHAIN_API_KEY = None
        mock_settings.MAX_TOKENS = 750
        mock_settings.TOP_K = 10
        mock_settings.TEMPERATURE = 0.3
        mock_settings.RETRIEVER_NUMBER_OF_RESULTS = 6
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'

        service = BedrockService(bedrock_client=mock_bedrock_client)

        with pytest.raises(ValueError, match='Invalid request to Bedrock'):
            service.generate_text('What is the capital of France?')


def test_get_llm(mock_bedrock_client):
    """Non-Anthropic models use BedrockLLM."""
    with (
        patch('backend.app.services.bedrock.settings') as mock_settings,
        patch('backend.app.services.bedrock.BedrockLLM') as mock_bedrock_llm,
    ):
        mock_settings.BEDROCK_MODEL_ID = 'amazon.titan-text-express-v1'
        mock_settings.LANGCHAIN_API_KEY = None
        mock_settings.AWS_REGION = 'us-east-1'
        mock_settings.MAX_TOKENS = 750
        mock_settings.TOP_K = 10
        mock_settings.TEMPERATURE = 0.3
        mock_settings.RETRIEVER_NUMBER_OF_RESULTS = 6
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'

        # Set up mock
        mock_llm = MagicMock()
        mock_bedrock_llm.return_value = mock_llm

        # Create service instance
        service = BedrockService(bedrock_client=mock_bedrock_client)

        # Call method
        llm = service.get_llm(temperature=0.1)

        # Assertions
        # Instead of direct object comparison, check that the mock was called correctly
        mock_bedrock_llm.assert_called_once_with(
            model_id=mock_settings.BEDROCK_MODEL_ID,
            model_kwargs={'temperature': 0.1, 'top_k': 10, 'max_tokens': 750},
            region_name=mock_settings.AWS_REGION,
            client=mock_bedrock_client,
        )
        # Check that we got the mock that was returned
        assert llm is mock_llm


def test_get_llm_uses_chat_bedrock_for_claude(mock_bedrock_client):
    """Anthropic Claude inference profiles use ChatBedrock (Messages API)."""
    with (
        patch('backend.app.services.bedrock.settings') as mock_settings,
        patch('backend.app.services.bedrock.ChatBedrock') as mock_chat_bedrock,
    ):
        mock_settings.BEDROCK_MODEL_ID = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'
        mock_settings.LANGCHAIN_API_KEY = None
        mock_settings.AWS_REGION = 'us-west-2'
        mock_settings.MAX_TOKENS = 750
        mock_settings.TOP_K = 10
        mock_settings.TEMPERATURE = 0.3
        mock_settings.RETRIEVER_NUMBER_OF_RESULTS = 6
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'

        mock_llm = MagicMock()
        mock_chat_bedrock.return_value = mock_llm

        service = BedrockService(bedrock_client=mock_bedrock_client)
        llm = service.get_llm()

        mock_chat_bedrock.assert_called_once()
        assert llm is mock_llm


def test_get_agent_client(mock_bedrock_client):
    """Test get_agent_client method with aws_client."""
    with patch('backend.app.services.bedrock.settings') as mock_settings:
        mock_settings.BEDROCK_MODEL_ID = 'anthropic.claude-v2'
        mock_settings.LANGCHAIN_API_KEY = None
        mock_settings.MAX_TOKENS = 750
        mock_settings.TOP_K = 10
        mock_settings.TEMPERATURE = 0.3
        mock_settings.RETRIEVER_NUMBER_OF_RESULTS = 6
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'

        # Create mock aws_client
        mock_aws_client = MagicMock()
        mock_agent_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_agent_client

        # Create service instance with aws_client
        service = BedrockService(aws_client=mock_aws_client)

        # Call get_agent_client
        agent_client = service.get_agent_client()

        # Verify the correct client was returned
        assert agent_client == mock_agent_client
        mock_aws_client.get_client.assert_called_with('bedrock-agent-runtime')


def test_get_agent_client_with_role_arn():
    """Test get_agent_client when using a provided client with role ARN."""
    with (
        patch('backend.app.services.bedrock.settings') as mock_settings,
        patch('backend.app.services.bedrock.AWSClientService') as mock_aws_client_class,
    ):
        # Configure settings
        mock_settings.BEDROCK_MODEL_ID = 'anthropic.claude-v2'
        mock_settings.LANGCHAIN_API_KEY = None
        mock_settings.AWS_REGION = 'us-east-1'
        mock_settings.MAX_TOKENS = 750
        mock_settings.TOP_K = 10
        mock_settings.TEMPERATURE = 0.3
        mock_settings.RETRIEVER_NUMBER_OF_RESULTS = 6
        mock_settings.RETRIEVER_SEARCH_TYPE = 'HYBRID'

        # Set up mocks
        bedrock_client = MagicMock()
        agent_client = MagicMock()

        # First AWSClientService for bedrock client
        mock_aws_client = MagicMock()
        mock_aws_client.get_client.return_value = agent_client

        # Second AWSClientService for agent client
        mock_aws_client_class.return_value = mock_aws_client

        # Create service with provided bedrock client
        role_arn = 'arn:aws:iam::123456789012:role/test-role'
        service = BedrockService(bedrock_client=bedrock_client, role_arn=role_arn)

        # Call get_agent_client
        client = service.get_agent_client()

        # Verify the correct client was returned
        assert client == agent_client
        mock_aws_client_class.assert_called_once_with(region_name=mock_settings.AWS_REGION, role_arn=role_arn)
        mock_aws_client.get_client.assert_called_once_with('bedrock-agent-runtime')
