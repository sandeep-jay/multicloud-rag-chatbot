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
import logging

from botocore.exceptions import (
    ClientError,
)
from langchain_aws import BedrockLLM, ChatBedrock

from backend.app.core.config_manager import settings
from backend.app.services.aws_client import AWSClientService
from backend.app.services.bedrock_model_id import resolve_bedrock_model_id
from backend.app.utils.simple_tracer import get_client

logger = logging.getLogger(__name__)


class BedrockService:
    """Unified service for interacting with AWS Bedrock"""

    def __init__(self, model_id=None, aws_client=None, bedrock_client=None, region_name=None, role_arn=None):
        self.region_name = region_name or settings.AWS_REGION
        raw_model_id = model_id or settings.BEDROCK_MODEL_ID
        self.model_id = resolve_bedrock_model_id(raw_model_id, self.region_name)
        if self.model_id != raw_model_id:
            logger.info('Bedrock inference profile %s (configured as %s)', self.model_id, raw_model_id)
        self.role_arn = role_arn or getattr(settings, 'AWS_ROLE_ARN', None)

        # Get the LangSmith client
        self.langsmith_client = get_client()
        if self.langsmith_client:
            logger.info(f'Using LangSmith client for project: {settings.LANGCHAIN_PROJECT}')
        else:
            logger.warning('LangSmith client not available, tracing will be disabled')

        # Set up AWS clients
        if bedrock_client:
            # Use provided bedrock client directly
            self.client = bedrock_client
            self.aws_client = None
            logger.info(f'Using provided Bedrock client for model: {self.model_id}')
        else:
            # Use existing AWS client or create a new one
            self.aws_client = aws_client or AWSClientService(
                region_name=self.region_name,
                role_arn=self.role_arn,
            )
            self.client = self.aws_client.get_client('bedrock-runtime')
            logger.info(f'Initialized Bedrock service with model: {self.model_id}')

    def get_agent_client(self):
        # Get a Bedrock agent runtime client for knowledge base access
        if self.aws_client:
            return self.aws_client.get_client('bedrock-agent-runtime')

        # If we're using a provided client, we need to create one for agent runtime
        try:
            # When using a provided client but no aws_client, create a new AWSClientService for agent runtime
            aws_client = AWSClientService(region_name=self.region_name, role_arn=self.role_arn)
            return aws_client.get_client('bedrock-agent-runtime')
        except Exception as e:
            logger.exception(f'Failed to create bedrock-agent-runtime client: {e!s}')
            raise RuntimeError(f'Could not create agent client: {e!s}')

    def _get_default_params(self, **kwargs):
        # Get default model parameters.
        return {
            'temperature': kwargs.get('temperature', settings.TEMPERATURE),
            'max_tokens': kwargs.get('max_tokens', settings.MAX_TOKENS),
            'top_k': kwargs.get('top_k', settings.TOP_K),
        }

    def _format_request_body(self, prompt: str, params: dict) -> dict:
        # Format the request body based on model type.
        if 'claude-3' in self.model_id:
            return {
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': params['max_tokens'],
                'temperature': params['temperature'],
            }
        elif 'anthropic.claude' in self.model_id:
            return {
                'prompt': f'\n\nHuman: {prompt}\n\nAssistant:',
                'max_tokens': params['max_tokens'],
                'temperature': params['temperature'],
            }
        else:
            return {
                'inputText': prompt,
                'textGenerationConfig': {
                    'maxTokenCount': params['max_tokens'],
                    'temperature': params['temperature'],
                },
            }

    def _extract_generated_text(self, response_body: dict) -> str:
        # Extract the generated text from the response based on model type.
        if 'claude-3' in self.model_id:
            return response_body.get('content', [{'text': ''}])[0].get('text', '')
        elif 'anthropic.claude' in self.model_id:
            return response_body.get('completion', '')
        else:
            return response_body.get('results', [{'outputText': ''}])[0].get('outputText', '')

    def _handle_bedrock_error(self, e: ClientError):
        # Handle Bedrock API errors.
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.exception(f'AWS Bedrock error ({error_code}): {e!s}')
        if error_code == 'ValidationException':
            raise ValueError(f'Invalid request to Bedrock: {e!s}')
        elif error_code == 'AccessDeniedException':
            raise PermissionError(f'Permission denied to access Bedrock: {e!s}')
        elif error_code == 'ResourceNotFoundException':
            raise ValueError(f"Bedrock model '{self.model_id}' not found: {e!s}")
        elif error_code == 'ThrottlingException':
            raise RuntimeError(f'Bedrock request rate limit exceeded: {e!s}')
        else:
            raise RuntimeError(f'Unhandled Bedrock error: {e!s}')

    def generate_text(self, prompt: str, **kwargs) -> str:
        # Generate text using the Bedrock model.

        try:
            logger.debug(f'Sending prompt to Bedrock: {prompt[:100]}...')

            # Get parameters and format request
            params = self._get_default_params(**kwargs)
            request_body = self._format_request_body(prompt, params)

            # Invoke the model
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
            )

            # Parse and extract response
            response_body = json.loads(response['body'].read())
            generated_text = self._extract_generated_text(response_body)

            logger.debug(f'Received response from Bedrock: {generated_text[:100]}...')
            return generated_text

        except ClientError as e:
            self._handle_bedrock_error(e)
        except Exception as e:
            logger.exception(f'Error generating text: {e!s}')
            raise RuntimeError(f'Unexpected error in text generation: {e!s}')

    def get_llm(self, **model_kwargs):
        # Get a LangChain LLM wrapper for Bedrock"""
        # Set default parameters
        params = {
            'temperature': settings.TEMPERATURE,
            'top_k': settings.TOP_K,
            'max_tokens': settings.MAX_TOKENS,
        }
        # Override with any provided parameters
        params.update(model_kwargs)

        # Construct kwargs for the LLM
        llm_kwargs = {
            'model_id': self.model_id,
            'model_kwargs': params,
            'region_name': self.region_name,
            'client': self.client,
        }

        # Anthropic Claude models require the Messages API (ChatBedrock).
        if 'anthropic.claude' in self.model_id:
            return ChatBedrock(**llm_kwargs)
        return BedrockLLM(**llm_kwargs)

    def get_streaming_llm(self, callbacks=None, **model_kwargs):
        """LangChain Bedrock client with token streaming enabled."""
        params = {
            'temperature': settings.TEMPERATURE,
            'top_k': settings.TOP_K,
            'max_tokens': settings.MAX_TOKENS,
        }
        params.update(model_kwargs)
        llm_kwargs = {
            'model_id': self.model_id,
            'model_kwargs': params,
            'region_name': self.region_name,
            'client': self.client,
            'streaming': True,
        }
        if callbacks:
            llm_kwargs['callbacks'] = callbacks
        if 'anthropic.claude' in self.model_id:
            return ChatBedrock(**llm_kwargs)
        return BedrockLLM(**llm_kwargs)
