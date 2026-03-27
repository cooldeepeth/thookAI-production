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
        return bool(self.resend_api_key)

class GoogleConfig:
    """Google OAuth configuration"""
    client_id: Optional[str] = field(default_factory=lambda: os.environ.get('GOOGLE_CLIENT_ID'))
    client_secret: Optional[str] = field(default_factory=lambda: os.environ.get('GOOGLE_CLIENT_SECRET'))
    backend_url: str = field(default_factory=lambda: os.environ.get('BACKEND_URL', 'http://localhost:8001'))

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def redirect_uri(self) -> str:
        return f"{self.backend_url}/api/auth/google/callback"



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
        return bool(self.secret_key and self.webhook_secret and self.all_price_ids_configured())


@dataclass
class AppConfig:
    """Application configuration"""
    environment: str = field(default_factory=lambda: os.environ.get('ENVIRONMENT', 'development'))
    debug: bool = field(default_factory=lambda: os.environ.get('DEBUG', 'false').lower() == 'true')
    log_level: str = field(default_factory=lambda: os.environ.get('LOG_LEVEL', 'INFO'))
    redis_url: Optional[str] = field(default_factory=lambda: os.environ.get('REDIS_URL'))
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


# Convenience function for quick access
settings = get_settings()
