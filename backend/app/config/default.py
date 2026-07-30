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

from typing import Any, Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DefaultSettings(BaseSettings):
    """Default application settings.

    Secret-bearing fields are typed as ``SecretStr`` so they are masked in
    ``repr``, logs, exceptions, and ``model_dump_json`` output. Read the
    cleartext via ``.get_secret_value()`` only at the boundary that needs it
    (JWT codec, HTTP client, etc.).
    """

    # CORE SETTINGS
    PROJECT_NAME: str = 'EdTech RAG Assistant API'
    VERSION: str = '1.0.0'
    API_V1_STR: str = '/api'
    # SECRET_KEY is required in production; the default below is a sentinel
    # that must never reach prod (CI/startup checks should reject it).
    SECRET_KEY: SecretStr = SecretStr('supersecretkey')

    # DATABASE SETTINGS
    DATABASE_URL: str = 'postgresql://chatbot:chatbot@localhost:5432/chatbot'

    # JWT SETTINGS
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 4  # 4 hours

    # CORS SETTINGS
    BACKEND_CORS_ORIGINS: list[str] = ['*']
    FRONTEND_URL: str = 'http://localhost:8501'  # Default Streamlit port

    @field_validator('BACKEND_CORS_ORIGINS')
    def assemble_cors_origins(cls, v: list[str] | str) -> list[str] | str:
        """Validate CORS origins."""
        if isinstance(v, str) and not v.startswith('['):
            return [i.strip() for i in v.split(',')]
        elif isinstance(v, list):
            return v
        return ['*']

    # SQLALCHEMY
    SQLALCHEMY_DATABASE_URI: str | None = None

    @field_validator('SQLALCHEMY_DATABASE_URI', mode='before')
    @classmethod
    def assemble_db_connection(cls, v: str | None, info) -> Any:
        if isinstance(v, str):
            return v
        return info.data.get('DATABASE_URL')

    # AWS settings
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: SecretStr | None = None
    AWS_REGION: str = 'us-east-1'
    AWS_ROLE_ARN: str | None = None
    AWS_PROFILE_NAME: str | None = None  # Deprecated: Use instance profiles on EC2 instead
    BEDROCK_MODEL_ID: str = 'us.anthropic.claude-3-5-haiku-20241022-v1:0'
    BEDROCK_KNOWLEDGE_BASE_ID: str | None = None
    BEDROCK_EMBEDDING_MODEL_ID: str = 'amazon.titan-embed-text-v1'

    # LangSmith settings
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: SecretStr | None = None
    LANGCHAIN_PROJECT: str = 'chatbot-poc'
    LANGCHAIN_ENDPOINT: str | None = None

    # Application settings
    APP_ENV: str | None = None

    # Logging settings
    LOG_TO_FILE: bool = True
    LOGGING_FORMAT: str = '[%(asctime)s] req=%(request_id)s - %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    LOGGING_LOCATION: str = 'fastapi.log'
    LOGGING_LEVEL: str = 'INFO'  # Default to INFO level
    LOGGING_PROPAGATION_LEVEL: str = 'INFO'

    # RAG and LLM tuning parameters
    MAX_TOKENS: int = 500  # Default for LLM max tokens
    TOP_K: int = 10  # Default for LLM top_k
    RETRIEVER_NUMBER_OF_RESULTS: int = 3  # Default number of docs to retrieve
    RETRIEVER_SEARCH_TYPE: str = 'HYBRID'  # Default search type for retriever
    TEMPERATURE: float = 0.1  # Default temperature for LLM

    # Rerank (Phase 5) — fetch RERANK_CANDIDATE_K, keep RERANK_TOP_N for generation
    RERANK_ENABLED: bool = False
    RERANK_BACKEND: str = 'flashrank'  # flashrank | keyword
    RERANK_TOP_N: int = 3
    RERANK_CANDIDATE_K: int = 10
    RERANK_MODEL: str = 'ms-marco-MiniLM-L-12-v2'
    RERANK_PREFILTER_MAX: int = 10
    RERANK_MIN_KEYWORD_OVERLAP: int = 0
    RERANK_RRF_K: int = 60

    # Multi-query (Phase 5)
    MULTI_QUERY_ENABLED: bool = False
    MULTI_QUERY_COUNT: int = 2

    # Metadata filters (Phase 5) — AWS KB filter JSON and/or client post-filter
    METADATA_FILTER_ENABLED: bool = False
    METADATA_FILTER_JSON: str | None = None
    METADATA_FILTER_CLIENT_ENABLED: bool = False
    METADATA_FILTER_CLIENT_JSON: str | None = None

    # Provider selection (mock | aws | azure | gcp); RAG_FORCE_MOCK overrides all
    RAG_FORCE_MOCK: bool = False
    RAG_PROVIDER: str | None = None  # single shortcut for both LLM and retriever
    LLM_PROVIDER: str = 'mock'
    RETRIEVER_PROVIDER: str = 'mock'

    # RAG orchestration: chain (LangChain) | langgraph
    RAG_ENGINE: str = 'chain'
    WEB_RESEARCH_ENABLED: bool = False
    WEB_SEARCH_PROVIDER: str = 'mock'  # mock | tavily
    TAVILY_API_KEY: SecretStr | None = None
    WEB_SEARCH_MAX_RESULTS: int = 5

    # Observability and platform
    LOG_JSON: bool = False
    ENABLE_DEV_API_ROUTES: bool = False
    ENABLE_OPENAPI_DOCS: bool = False

    # Rate limiting (Redis optional; fakeredis used when REDIS_URL unset)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_REGISTER_PER_MINUTE: int = 5
    RATE_LIMIT_CHAT_PER_MINUTE: int = 30
    REDIS_URL: str | None = None

    # Tenant / assistant branding (defaults when user has no tenant or tenant.rag_config)
    ASSISTANT_NAME: str = 'EdTech Support Assistant'
    SUPPORTED_TOPICS: str = 'your learning platform, course tools, integrations, and support documentation'
    OUT_OF_SCOPE_MESSAGE: str = (
        'I can only answer questions covered by the knowledge base for ' '{{supported_topics}}. Please ask a question related to those topics.'
    )

    # Performance / chat context
    CHAT_HISTORY_MAX_MESSAGES: int = 40  # Max messages passed to RAG (0 = unlimited)
    STREAM_ARTIFICIAL_DELAY_MS: int = 0  # Demo-only delay between streamed tokens; 0 = off
    SQLALCHEMY_POOL_SIZE: int = 5
    SQLALCHEMY_MAX_OVERFLOW: int = 10

    # Azure OpenAI (optional — for LLM_PROVIDER=azure)
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_KEY: SecretStr | None = None
    AZURE_OPENAI_DEPLOYMENT: str | None = None
    AZURE_OPENAI_API_VERSION: str = '2024-02-01'
    AZURE_EMBEDDING_DEPLOYMENT: str | None = None

    # Azure AI Search (optional — for RETRIEVER_PROVIDER=azure)
    AZURE_SEARCH_SERVICE_NAME: str | None = None
    AZURE_SEARCH_KEY: SecretStr | None = None
    AZURE_SEARCH_INDEX: str | None = None
    AZURE_SEARCH_VECTOR_FIELD: str = 'text_vector'

    # GCP / Vertex AI (optional — for LLM_PROVIDER=gcp or RETRIEVER_PROVIDER=gcp)
    GCP_PROJECT_ID: str | None = None
    GCP_LOCATION: str = 'us-central1'
    GCP_LLM_MODEL: str | None = None
    VERTEX_SEARCH_LOCATION: str = 'global'
    VERTEX_SEARCH_DATA_STORE_ID: str | None = None
    VERTEX_SEARCH_FILTER: str | None = None

    # Helpdesk agent (post-RAG escalation: summarize + file GitHub issue).
    # Disabled by default; enabling requires GITHUB_TOKEN + GITHUB_REPO.
    HELPDESK_ENABLED: bool = False
    GITHUB_TOKEN: SecretStr | None = None
    GITHUB_REPO: str | None = None  # 'org/repo' — use a private demo repo
    GITHUB_DEFAULT_LABELS: str = 'it-helpdesk'
    # Detection thresholds for the kb_resolved heuristic in graph/format
    HELPDESK_KB_RESOLVED_MIN_SCORE: float = 0.0  # 0 disables the score floor
    # Per-user idempotency window for create-issue (seconds)
    HELPDESK_DEDUP_WINDOW_SECONDS: int = 300
    # Max conversation turns sent to the summarizer (latest N preserved)
    HELPDESK_SUMMARIZE_MAX_TURNS: int = 6
    # Multi-turn helpdesk agent (LangGraph-oriented redesign; Phase A starts with /agent/start)
    HELPDESK_AGENT_ENABLED: bool = False
    HELPDESK_AGENT_KILL_SWITCH: bool = False
    HELPDESK_AGENT_TOOL_GITHUB_SEARCH: bool = True
    HELPDESK_AGENT_TOOL_KB_RETRY: bool = True
    HELPDESK_AGENT_TOOL_WEB_SEARCH: bool = True
    HELPDESK_AGENT_LLM_SUPERVISOR: bool = False
    HELPDESK_AGENT_USE_LANGGRAPH_CHECKPOINT: bool = True
    HELPDESK_AGENT_CHECKPOINT_BACKEND: Literal['postgres', 'sqlite', 'memory'] = 'postgres'
    HELPDESK_AGENT_CHECKPOINT_PATH: str = '.helpdesk_agent_checkpoints.sqlite'
    HELPDESK_AGENT_CHECKPOINT_TTL_SECONDS: int = 86400
    HELPDESK_AGENT_TOOL_OUTPUT_MAX_CHARS: int = 4000
    HELPDESK_AGENT_MAX_TURNS: int = 8
    HELPDESK_AGENT_MAX_QUESTIONS: int = 2
    HELPDESK_AGENT_CLARIFY_CONFIDENCE_FLOOR: float = 0.75
    HELPDESK_AGENT_MAX_TOOL_RETRIES: int = 2
    HELPDESK_AGENT_MAX_TOKENS_PER_SESSION: int = 20000
    HELPDESK_AGENT_DEADLINE_SECONDS: float = 60.0
    HELPDESK_AGENT_KB_RETRY_TIMEOUT_SECONDS: float = 12.0
    # Top-1 retrieval similarity score (0..1) the agent's KB retry must clear
    # before we treat the hits as relevant. Below this, the agent pauses for
    # web-search consent (or skips to draft if web is mock/disabled).
    HELPDESK_AGENT_KB_CONFIDENCE_FLOOR: float = 0.55
    # Cap on how many KB/web sources the agent surfaces with its solution.
    # The retry returns 15+ docs from Bedrock; users only need the top-N
    # that actually informed the answer.
    HELPDESK_AGENT_EVIDENCE_TOP_N: int = 3
    HELPDESK_AGENT_WEB_SEARCH_TIMEOUT_SECONDS: float = 10.0
    HELPDESK_AGENT_GITHUB_SEARCH_TIMEOUT_SECONDS: float = 8.0

    # Campus router (Phase 5 — capability registry + LLM domain router).
    # Off by default so PR CI and the deterministic chat path are unchanged;
    # demo mode enables it to route escalations to helpdesk and surface the
    # router decision alongside ``kb_resolved`` in chat metadata. The
    # ``ROUTER_HELPDESK_FLOOR`` is the minimum confidence at which a
    # router-classified ``helpdesk`` turn promotes the escalation chip even
    # when ``kb_resolved`` is true. See ADR-007.
    CAMPUS_ROUTER_ENABLED: bool = False
    ROUTER_HELPDESK_FLOOR: float = 0.6

    # Auth cookies (set AUTH_COOKIE_SECURE=true in production HTTPS)
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: str = 'lax'

    # Social OAuth (Google / GitHub)
    OAUTH_REDIRECT_BASE_URL: str | None = None
    OAUTH_ENABLED_PROVIDERS: str = 'google,github'
    OAUTH_GOOGLE_CLIENT_ID: str | None = None
    OAUTH_GOOGLE_CLIENT_SECRET: SecretStr | None = None
    OAUTH_GITHUB_CLIENT_ID: str | None = None
    OAUTH_GITHUB_CLIENT_SECRET: SecretStr | None = None

    # `extra='ignore'` (was `'allow'`) drops unrecognised env vars instead of
    # silently attaching them, so typos surface as missing-attribute errors at
    # the callsite. For CI/prod consider `extra='forbid'` to fail fast on
    # unknown keys. `secrets_dir` enables Docker / Kubernetes secret-file
    # mounts (e.g. `/run/secrets/SECRET_KEY`) — see docs/SECURITY.md.
    model_config = SettingsConfigDict(
        extra='ignore',
        case_sensitive=True,
        env_file_encoding='utf-8',
        secrets_dir=None,
    )
