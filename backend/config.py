"""
ThookAI Configuration Module

Handles environment variable loading, validation, and configuration management
for production deployment.
"""

import os
import logging
from typing import Optional, List
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration"""
    mongo_url: str = field(default_factory=lambda: os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db_name: str = field(default_factory=lambda: os.environ.get('DB_NAME', 'thook_database'))
    max_pool_size: int = field(default_factory=lambda: int(os.environ.get('MONGO_MAX_POOL_SIZE', '100')))
    min_pool_size: int = field(default_factory=lambda: int(os.environ.get('MONGO_MIN_POOL_SIZE', '10')))
    server_selection_timeout_ms: int = field(default_factory=lambda: int(os.environ.get('MONGO_TIMEOUT_MS', '5000')))


@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret_key: str = field(default_factory=lambda: os.environ.get('JWT_SECRET_KEY', ''))
    jwt_algorithm: str = field(default_factory=lambda: os.environ.get('JWT_ALGORITHM', 'HS256'))
    jwt_expire_days: int = field(default_factory=lambda: int(os.environ.get('JWT_EXPIRE_DAYS', '7')))
    cors_origins: List[str] = field(default_factory=lambda: os.environ.get('CORS_ORIGINS', '*').split(','))
    fernet_key: Optional[str] = field(default_factory=lambda: os.environ.get('FERNET_KEY'))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.environ.get('RATE_LIMIT_PER_MINUTE', '60')))
    rate_limit_auth_per_minute: int = field(default_factory=lambda: int(os.environ.get('RATE_LIMIT_AUTH_PER_MINUTE', '10')))
    
    def validate(self) -> List[str]:
        """Validate security configuration and return list of warnings/errors"""
        issues = []
        
        # Check JWT secret
        if not self.jwt_secret_key:
            issues.append("CRITICAL: JWT_SECRET_KEY is not set!")
        elif len(self.jwt_secret_key) < 32:
            issues.append("WARNING: JWT_SECRET_KEY should be at least 32 characters")
        elif 'change' in self.jwt_secret_key.lower() or 'placeholder' in self.jwt_secret_key.lower():
            issues.append("CRITICAL: JWT_SECRET_KEY appears to be a placeholder value!")
        
        # Check CORS
        if '*' in self.cors_origins:
            issues.append("WARNING: CORS_ORIGINS is set to '*' - restrict in production")
        
        return issues


@dataclass
class LLMConfig:
    """LLM provider configuration"""
    emergent_key: Optional[str] = field(default_factory=lambda: os.environ.get('EMERGENT_LLM_KEY'))
    openai_key: Optional[str] = field(default_factory=lambda: os.environ.get('OPENAI_API_KEY'))
    anthropic_key: Optional[str] = field(default_factory=lambda: os.environ.get('ANTHROPIC_API_KEY'))
    gemini_key: Optional[str] = field(default_factory=lambda: os.environ.get('GEMINI_API_KEY'))
    perplexity_key: Optional[str] = field(default_factory=lambda: os.environ.get('PERPLEXITY_API_KEY'))
    elevenlabs_key: Optional[str] = field(default_factory=lambda: os.environ.get('ELEVENLABS_API_KEY'))
    pinecone_key: Optional[str] = field(default_factory=lambda: os.environ.get('PINECONE_API_KEY'))
    
    def has_llm_provider(self) -> bool:
        """Check if at least one LLM provider is configured"""
        return bool(
            self.emergent_key or self.openai_key or self.anthropic_key or self.gemini_key
        )
    
    def get_status(self) -> dict:
        """Get configuration status for all providers"""
        return {
            'emergent': bool(self.emergent_key and not self.emergent_key.startswith('placeholder')),
            'openai': bool(self.openai_key and self.openai_key.startswith('sk-') and 'placeholder' not in self.openai_key),
            'anthropic': bool(self.anthropic_key and self.anthropic_key.startswith('sk-ant-') and 'placeholder' not in self.anthropic_key),
            'gemini': bool(self.gemini_key and 'placeholder' not in self.gemini_key),
            'perplexity': bool(self.perplexity_key and self.perplexity_key.startswith('pplx-') and 'placeholder' not in self.perplexity_key),
            'elevenlabs': bool(self.elevenlabs_key and 'placeholder' not in self.elevenlabs_key),
            'pinecone': bool(self.pinecone_key and 'placeholder' not in self.pinecone_key),
        }


@dataclass
class R2Config:
    """Cloudflare R2 media storage configuration"""
    r2_account_id: Optional[str] = field(default_factory=lambda: os.environ.get('R2_ACCOUNT_ID'))
    r2_access_key_id: Optional[str] = field(default_factory=lambda: os.environ.get('R2_ACCESS_KEY_ID'))
    r2_secret_access_key: Optional[str] = field(default_factory=lambda: os.environ.get('R2_SECRET_ACCESS_KEY'))
    r2_bucket_name: Optional[str] = field(default_factory=lambda: os.environ.get('R2_BUCKET_NAME', 'thookai-media'))
    r2_public_url: Optional[str] = field(default_factory=lambda: os.environ.get('R2_PUBLIC_URL'))
    
    def has_r2(self) -> bool:
        """Check if all required R2 config values are set"""
        return all([
            self.r2_account_id,
            self.r2_access_key_id,
            self.r2_secret_access_key,
            self.r2_bucket_name,
            self.r2_public_url
        ])


@dataclass

class EmailConfig:
    """Email (Resend) configuration"""
    resend_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('RESEND_API_KEY'))
    from_email: str = field(default_factory=lambda: os.environ.get('FROM_EMAIL', 'noreply@thookai.com'))
    frontend_url: str = field(default_factory=lambda: os.environ.get('FRONTEND_URL', 'http://localhost:3000'))

    def is_configured(self) -> bool:
        """Check if Resend API key is set"""
        # FIXED: strip whitespace before checking
        return bool((self.resend_api_key or "").strip())

@dataclass
class GoogleConfig:
    """Google OAuth configuration"""
    client_id: Optional[str] = field(default_factory=lambda: os.environ.get('GOOGLE_CLIENT_ID'))
    client_secret: Optional[str] = field(default_factory=lambda: os.environ.get('GOOGLE_CLIENT_SECRET'))
    backend_url: str = field(default_factory=lambda: os.environ.get('BACKEND_URL', 'http://localhost:8001'))

    def is_configured(self) -> bool:
        # FIXED: strip whitespace from config values before checking
        return bool((self.client_id or "").strip() and (self.client_secret or "").strip())

    @property
    def redirect_uri(self) -> str:
        # FIXED: strip trailing slash from backend_url to prevent double-slash in redirect_uri
        base = (self.backend_url or "").strip().rstrip('/')
        return f"{base}/api/auth/google/callback"



@dataclass
class StripeConfig:
    """Stripe billing configuration"""
    secret_key: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_SECRET_KEY'))
    publishable_key: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PUBLISHABLE_KEY'))
    webhook_secret: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_WEBHOOK_SECRET'))
    price_pro_monthly: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_PRO_MONTHLY'))
    price_pro_annual: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_PRO_ANNUAL'))
    price_studio_monthly: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_STUDIO_MONTHLY'))
    price_studio_annual: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_STUDIO_ANNUAL'))
    price_agency_monthly: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_AGENCY_MONTHLY'))
    price_agency_annual: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_AGENCY_ANNUAL'))
    price_credits_100: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_CREDITS_100'))
    price_credits_500: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_CREDITS_500'))
    price_credits_1000: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_CREDITS_1000'))

    def all_price_ids_configured(self) -> bool:
        """Check if all required subscription price IDs are set."""
        return all([
            self.price_pro_monthly, self.price_pro_annual,
            self.price_studio_monthly, self.price_studio_annual,
            self.price_agency_monthly, self.price_agency_annual
        ])

    def is_fully_configured(self) -> bool:
        """Check if Stripe is fully configured for production billing."""
        # FIXED: reject placeholder/example keys
        key = (self.secret_key or "").strip()
        if not key or any(p in key.lower() for p in ("placeholder", "example", "your_")):
            return False
        return bool(self.webhook_secret and self.all_price_ids_configured())


@dataclass
class VideoProviderConfig:
    """Video generation provider configuration"""
    runway_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('RUNWAY_API_KEY'))
    kling_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('KLING_API_KEY'))
    luma_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('LUMA_API_KEY'))
    pika_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('PIKA_API_KEY'))
    heygen_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('HEYGEN_API_KEY'))
    did_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('DID_API_KEY'))
    fal_key: Optional[str] = field(default_factory=lambda: os.environ.get('FAL_KEY'))


@dataclass
class VoiceProviderConfig:
    """Voice/audio generation provider configuration"""
    playht_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('PLAYHT_API_KEY'))
    playht_user_id: Optional[str] = field(default_factory=lambda: os.environ.get('PLAYHT_USER_ID'))
    google_tts_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('GOOGLE_TTS_API_KEY'))


@dataclass
class PlatformOAuthConfig:
    """Social platform OAuth configuration"""
    linkedin_client_id: Optional[str] = field(default_factory=lambda: os.environ.get('LINKEDIN_CLIENT_ID'))
    linkedin_client_secret: Optional[str] = field(default_factory=lambda: os.environ.get('LINKEDIN_CLIENT_SECRET'))
    meta_app_id: Optional[str] = field(default_factory=lambda: os.environ.get('META_APP_ID'))
    meta_app_secret: Optional[str] = field(default_factory=lambda: os.environ.get('META_APP_SECRET'))
    twitter_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('TWITTER_API_KEY'))
    twitter_api_secret: Optional[str] = field(default_factory=lambda: os.environ.get('TWITTER_API_SECRET'))
    encryption_key: Optional[str] = field(default_factory=lambda: os.environ.get('ENCRYPTION_KEY'))


@dataclass
class PineconeConfig:
    """Pinecone vector store configuration"""
    environment: str = field(default_factory=lambda: os.environ.get('PINECONE_ENVIRONMENT', 'us-east-1'))
    index_name: str = field(default_factory=lambda: os.environ.get('PINECONE_INDEX_NAME', 'thookai-personas'))


@dataclass
class N8nConfig:
    """n8n workflow orchestration configuration"""
    n8n_url: str = field(default_factory=lambda: os.environ.get('N8N_URL', 'http://n8n:5678'))
    webhook_secret: str = field(default_factory=lambda: os.environ.get('N8N_WEBHOOK_SECRET', ''))
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_API_KEY'))
    backend_callback_url: str = field(default_factory=lambda: os.environ.get('N8N_BACKEND_CALLBACK_URL', 'http://backend:8001'))
    workflow_scheduled_posts: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_WORKFLOW_SCHEDULED_POSTS'))
    workflow_reset_daily_limits: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_WORKFLOW_RESET_DAILY_LIMITS'))
    workflow_refresh_monthly_credits: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_WORKFLOW_REFRESH_MONTHLY_CREDITS'))
    workflow_cleanup_old_jobs: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_WORKFLOW_CLEANUP_OLD_JOBS'))
    workflow_cleanup_expired_shares: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_WORKFLOW_CLEANUP_EXPIRED_SHARES'))
    workflow_aggregate_daily_analytics: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_WORKFLOW_AGGREGATE_DAILY_ANALYTICS'))
    workflow_cleanup_stale_jobs: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_WORKFLOW_CLEANUP_STALE_JOBS'))
    workflow_nightly_strategist: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_WORKFLOW_NIGHTLY_STRATEGIST'))
    workflow_analytics_poll_24h: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_WORKFLOW_ANALYTICS_POLL_24H'))
    workflow_analytics_poll_7d: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_WORKFLOW_ANALYTICS_POLL_7D'))

    def is_configured(self) -> bool:
        """Check if n8n is configured with required URL and secret."""
        return bool(self.n8n_url and self.webhook_secret)


@dataclass
class LightRAGConfig:
    """LightRAG knowledge graph sidecar configuration.

    CRITICAL: embedding_model and embedding_dim are FROZEN after first document insert.
    Changing them requires full index rebuild (delete all NanoVectorDB files + re-ingest).
    """
    url: str = field(default_factory=lambda: os.environ.get('LIGHTRAG_URL', 'http://lightrag:9621'))
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get('LIGHTRAG_API_KEY'))
    embedding_model: str = field(default_factory=lambda: os.environ.get('LIGHTRAG_EMBEDDING_MODEL', 'text-embedding-3-small'))
    embedding_dim: int = field(default_factory=lambda: int(os.environ.get('LIGHTRAG_EMBEDDING_DIM', '1536')))

    def is_configured(self) -> bool:
        """Check if LightRAG sidecar URL is set."""
        return bool(self.url)

    def assert_embedding_config(self) -> None:
        """Fail loudly if embedding config diverges from locked decision.

        Must match NanoVectorDB stored dimension. Called once at FastAPI startup.
        """
        assert self.embedding_model == "text-embedding-3-small", (
            f"LIGHTRAG_EMBEDDING_MODEL must be 'text-embedding-3-small', got: {self.embedding_model}"
        )
        assert self.embedding_dim == 1536, (
            f"LIGHTRAG_EMBEDDING_DIM must be 1536 for text-embedding-3-small, got: {self.embedding_dim}"
        )


@dataclass
class StrategistConfig:
    """Strategist Agent cadence and behaviour configuration.

    These are application constants — not environment-driven.
    All fields are tuned for launch-day cadence per STRAT-04/05/06.
    """
    # STRAT-04: hard cap on recommendation cards delivered per user per day
    max_cards_per_day: int = 3
    # STRAT-05: days a dismissed topic is suppressed before re-surfacing
    suppression_days: int = 14
    # STRAT-06: consecutive dismissals threshold before delivery rate is halved
    consecutive_dismissal_threshold: int = 5
    # Minimum approved content jobs required before running strategist for a user
    min_approved_content: int = 3
    # LLM synthesis call timeout in seconds
    synthesis_timeout: float = 30.0
    # Documentation field: n8n beat runs the nightly strategist at this UTC hour
    nightly_cron_hour_utc: int = 3


@dataclass
class RemotionConfig:
    """Remotion video compositor sidecar configuration"""
    remotion_service_url: str = field(default_factory=lambda: os.environ.get('REMOTION_SERVICE_URL', 'http://localhost:3001'))
    remotion_license_key: str = field(default_factory=lambda: os.environ.get('REMOTION_LICENSE_KEY', ''))

    def is_configured(self) -> bool:
        """Check if Remotion sidecar is reachable (URL is non-default or REMOTION_SERVICE_URL is set)."""
        return bool(os.environ.get('REMOTION_SERVICE_URL'))


@dataclass
class AppConfig:
    """Application configuration"""
    environment: str = field(default_factory=lambda: os.environ.get('ENVIRONMENT', 'development'))
    debug: bool = field(default_factory=lambda: os.environ.get('DEBUG', 'false').lower() == 'true')
    log_level: str = field(default_factory=lambda: os.environ.get('LOG_LEVEL', 'INFO'))
    redis_url: Optional[str] = field(default_factory=lambda: os.environ.get('REDIS_URL'))
    celery_broker_url: Optional[str] = field(default_factory=lambda: os.environ.get('CELERY_BROKER_URL'))
    celery_result_backend: Optional[str] = field(default_factory=lambda: os.environ.get('CELERY_RESULT_BACKEND'))
    frontend_url: str = field(default_factory=lambda: os.environ.get('FRONTEND_URL', 'http://localhost:3000'))
    backend_url: str = field(default_factory=lambda: os.environ.get('BACKEND_URL', 'http://localhost:8001'))
    sentry_dsn: Optional[str] = field(default_factory=lambda: os.environ.get('SENTRY_DSN'))
    
    @property
    def is_production(self) -> bool:
        return self.environment == 'production'
    
    @property
    def is_development(self) -> bool:
        return self.environment == 'development'


@dataclass
class Settings:
    """Main settings container"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    app: AppConfig = field(default_factory=AppConfig)
    r2: R2Config = field(default_factory=R2Config)
    email: EmailConfig = field(default_factory=EmailConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    stripe: StripeConfig = field(default_factory=StripeConfig)
    video: VideoProviderConfig = field(default_factory=VideoProviderConfig)
    voice: VoiceProviderConfig = field(default_factory=VoiceProviderConfig)
    platforms: PlatformOAuthConfig = field(default_factory=PlatformOAuthConfig)
    pinecone: PineconeConfig = field(default_factory=PineconeConfig)
    n8n: N8nConfig = field(default_factory=N8nConfig)
    lightrag: LightRAGConfig = field(default_factory=LightRAGConfig)
    remotion: RemotionConfig = field(default_factory=RemotionConfig)
    strategist: StrategistConfig = field(default_factory=StrategistConfig)

    def validate(self) -> dict:
        """
        Validate all configuration and return status report
        """
        report = {
            'status': 'ok',
            'environment': self.app.environment,
            'warnings': [],
            'errors': [],
            'providers': self.llm.get_status(),
            'r2_storage': self.r2.has_r2(),
            'email': self.email.is_configured(),
            'stripe': self.stripe.is_fully_configured()
        }
        
        # Security validation
        security_issues = self.security.validate()
        for issue in security_issues:
            if issue.startswith('CRITICAL'):
                report['errors'].append(issue)
                report['status'] = 'error'
            else:
                report['warnings'].append(issue)
                if report['status'] == 'ok':
                    report['status'] = 'warning'
        
        # LLM validation
        if not self.llm.has_llm_provider():
            report['warnings'].append("WARNING: No LLM provider configured - AI features will be limited")
            if report['status'] == 'ok':
                report['status'] = 'warning'
        
        # Production-specific checks
        if self.app.is_production:
            if self.app.debug:
                report['errors'].append("CRITICAL: DEBUG=true in production!")
                report['status'] = 'error'
            
            if '*' in self.security.cors_origins:
                report['errors'].append("CRITICAL: CORS_ORIGINS='*' in production!")
                report['status'] = 'error'
        
        return report
    
    def log_startup_info(self):
        """Log configuration info at startup"""
        report = self.validate()
        
        logger.info("="*60)
        logger.info("ThookAI Configuration Report")
        logger.info("="*60)
        logger.info(f"Environment: {self.app.environment}")
        logger.info(f"Status: {report['status'].upper()}")
        
        if report['errors']:
            for error in report['errors']:
                logger.error(error)
        
        if report['warnings']:
            for warning in report['warnings']:
                logger.warning(warning)
        
        # Log provider status
        logger.info("LLM Providers:")
        for provider, configured in report['providers'].items():
            status = "✓ Configured" if configured else "✗ Not configured"
            logger.info(f"  {provider}: {status}")
        
        logger.info("="*60)
        
        return report


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def validate_required_env_vars() -> list:
    """
    Check that critical environment variables are set.
    Returns list of missing variable names.

    Required in ALL environments:
      MONGO_URL, DB_NAME, JWT_SECRET_KEY, FERNET_KEY

    Required in production (ENVIRONMENT=production):
      REDIS_URL, ANTHROPIC_API_KEY (or OPENAI_API_KEY),
      R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL,
      STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
      ENCRYPTION_KEY
    """
    missing = []

    # Always required
    always_required = ["MONGO_URL", "DB_NAME", "JWT_SECRET_KEY", "FERNET_KEY"]
    for var in always_required:
        val = os.environ.get(var, "").strip()
        if not val or val in ("change_this_to_a_random_64_char_string", "your_fernet_key_here"):
            missing.append(var)

    env = os.environ.get("ENVIRONMENT", "development")
    if env == "production":
        prod_required = [
            "REDIS_URL",
            "R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET_NAME", "R2_PUBLIC_URL",
            "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET",
            "ENCRYPTION_KEY",
        ]
        for var in prod_required:
            val = os.environ.get(var, "").strip()
            if not val:
                missing.append(var)

        # At least one LLM provider required in production
        has_llm = any(
            os.environ.get(k, "").strip()
            for k in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "EMERGENT_LLM_KEY"]
        )
        if not has_llm:
            missing.append("ANTHROPIC_API_KEY (or OPENAI_API_KEY or EMERGENT_LLM_KEY)")

    return missing


# Convenience function for quick access
settings = get_settings()
