# ThookAI Production Deployment Guide

This guide covers the production deployment preparation completed for ThookAI.

---

## 📋 Overview

The following production-readiness improvements have been implemented:

| Area | Status | Description |
|------|--------|-------------|
| Environment Variables | ✅ Complete | Full audit with `.env.example` template |
| Security Hardening | ✅ Complete | Headers, rate limiting, input validation |
| Performance Optimization | ✅ Complete | Compression, caching, connection pooling |
| Database Indexing | ✅ Complete | 80+ indexes across all collections |

---

## 1. Environment Variable Audit

### Configuration Files

| File | Purpose |
|------|---------|
| `/app/backend/.env` | Active environment configuration |
| `/app/backend/.env.example` | Template with all variables documented |
| `/app/backend/config.py` | Configuration validation module |

### Required Variables (Production)

```bash
# CRITICAL - Must be changed from defaults
JWT_SECRET_KEY=<64-character-random-string>
CORS_ORIGINS=https://yourdomain.com
FERNET_KEY=<generated-fernet-key>
ENVIRONMENT=production
DEBUG=false

# Generate keys with:
python -c "import secrets; print(secrets.token_urlsafe(64))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Configuration Validation

The server validates configuration at startup and logs a status report:

```
============================================================
ThookAI Configuration Report
============================================================
Environment: production
Status: OK
LLM Providers:
  emergent: ✓ Configured
  openai: ✗ Not configured
============================================================
```

### API Endpoints for Monitoring

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Health check with database status |
| `GET /api/config/status` | Configuration status (dev only) |

---

## 2. Security Hardening

### Security Headers (Automatic)

All responses include these security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | XSS protection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Referrer control |
| `Content-Security-Policy` | Configured | XSS prevention |
| `Strict-Transport-Security` | 1 year | Force HTTPS |
| `Permissions-Policy` | Restrictive | Disable unused APIs |

### Rate Limiting

Implemented using sliding window algorithm:

| Endpoint Type | Limit |
|--------------|-------|
| Default | 60 req/min |
| Auth endpoints | 10 req/min |
| Content creation | 20 req/min |
| Viral prediction | 30 req/min |

Response headers include:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining

429 errors include `Retry-After` header.

### Password Policy

New passwords must meet:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character
- Not in common password list

### Input Validation

- Maximum request body: 10MB
- Content-Type validation for POST/PUT/PATCH
- Pydantic validation on all endpoints

### Token Encryption

OAuth access tokens stored encrypted using Fernet:
- Generate key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- Set in `.env`: `FERNET_KEY=<your-key>`

---

## 3. Performance Optimization

### Response Compression

Gzip compression enabled for:
- `application/json`
- `text/plain`, `text/html`, `text/css`
- `application/javascript`

Settings:
- Minimum size: 500 bytes
- Compression level: 6

### Response Caching

In-memory caching for static endpoints:

| Endpoint | TTL |
|----------|-----|
| `/api/templates/categories` | 1 hour |
| `/api/billing/subscription/tiers` | 1 hour |
| `/api/billing/credits/costs` | 1 hour |
| `/api/viral/patterns` | 1 hour |
| `/api/content/providers/summary` | 5 minutes |
| `/api/persona/regional-english/options` | 24 hours |

Cache headers:
- `X-Cache: HIT` or `X-Cache: MISS`
- `Cache-Control: public, max-age=<ttl>`

### Request Timing

All responses include `X-Response-Time` header.
Slow requests (>2s) are logged as warnings.

### Database Connection Pooling

MongoDB connection settings:

```python
maxPoolSize: 100      # Maximum connections
minPoolSize: 10       # Minimum connections
connectTimeoutMS: 10000
socketTimeoutMS: 30000
retryWrites: True
retryReads: True
w: 'majority'         # Write concern
```

---

## 4. Database Indexing

### Index Summary

| Collection | Indexes |
|------------|---------|
| users | 5 |
| user_sessions | 3 (with TTL) |
| persona_engines | 3 |
| persona_shares | 4 |
| content_jobs | 11 |
| content_series | 4 |
| scheduled_posts | 5 |
| platform_tokens | 3 |
| oauth_states | 2 (with TTL) |
| templates | 9 (including text search) |
| template_upvotes | 2 |
| template_usage | 3 |
| workspaces | 3 |
| workspace_members | 5 |
| credit_transactions | 5 |
| subscription_history | 2 |
| daily_briefs | 2 (with TTL) |
| daily_brief_dismissals | 2 (with TTL) |
| learning_signals | 3 |
| onboarding_sessions | 3 (with TTL) |

**Total: 80+ indexes**

### Index Management

```bash
# Create/update indexes
cd /app/backend
python db_indexes.py create

# View index statistics
python db_indexes.py stats

# Drop all indexes (dangerous!)
python db_indexes.py drop --confirm-drop
```

### Key Indexes

**Users:**
```javascript
{ email: 1 }        // unique
{ user_id: 1 }      // unique
{ google_id: 1 }    // sparse
```

**Content Jobs:**
```javascript
{ job_id: 1 }                           // unique
{ user_id: 1, status: 1 }               // compound
{ user_id: 1, created_at: -1 }          // compound
{ scheduled_at: 1 }                      // sparse
```

**Templates:**
```javascript
{ is_active: 1, upvotes: -1 }           // popular templates
{ title: "text", description: "text" }   // full-text search
```

### TTL Indexes (Auto-cleanup)

| Collection | TTL |
|------------|-----|
| user_sessions | Token expiry |
| oauth_states | 10 minutes |
| daily_briefs | 48 hours |
| daily_brief_dismissals | 48 hours |
| onboarding_sessions | 24 hours |

---

## 5. Production Checklist

### Before Deployment

- [ ] Generate new `JWT_SECRET_KEY` (64+ chars)
- [ ] Generate new `FERNET_KEY`
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure `CORS_ORIGINS` (no wildcards)
- [ ] Configure MongoDB connection string with auth
- [ ] Set up SSL/TLS certificates
- [ ] Configure DNS and domain

### API Keys (Optional but Recommended)

- [ ] `EMERGENT_LLM_KEY` or individual LLM keys
- [ ] `PERPLEXITY_API_KEY` for research features
- [ ] At least one image generation provider
- [ ] `ELEVENLABS_API_KEY` for voice features
- [ ] `PINECONE_API_KEY` for vector search

### Monitoring

- [ ] Set up health check monitoring on `/api/health`
- [ ] Configure log aggregation
- [ ] Set up error tracking (optional: `SENTRY_DSN`)
- [ ] Monitor slow request warnings in logs

### Security

- [ ] Enable HTTPS only
- [ ] Configure firewall rules
- [ ] Set up DDoS protection
- [ ] Review CORS origins
- [ ] Audit rate limit settings

---

## 6. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Request                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Middleware Stack                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 7. TimingMiddleware (logs slow requests)                 │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 6. CacheMiddleware (serves cached responses)             │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 5. CompressionMiddleware (gzip responses)                │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 4. InputValidationMiddleware (validates requests)        │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 3. RateLimitMiddleware (throttles requests)              │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 2. SecurityHeadersMiddleware (adds security headers)     │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 1. CORSMiddleware (handles CORS)                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Routes: auth, content, persona, templates, etc.          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MongoDB (with indexes)                       │
│  Connection Pool: 10-100 connections                             │
│  Write Concern: majority                                         │
│  80+ optimized indexes                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Files Created/Modified

| File | Type | Description |
|------|------|-------------|
| `/app/backend/.env.example` | New | Environment template (32 variables) |
| `/app/backend/config.py` | New | Configuration validation module |
| `/app/backend/middleware/__init__.py` | New | Middleware package |
| `/app/backend/middleware/security.py` | New | Security middleware |
| `/app/backend/middleware/performance.py` | New | Performance middleware |
| `/app/backend/db_indexes.py` | New | Database index management |
| `/app/backend/server.py` | Modified | Integrated all middleware |
| `/app/backend/database.py` | Modified | Connection pooling |
| `/app/backend/auth_utils.py` | Modified | Password policy |
| `/app/backend/.env` | Modified | New configuration options |

---

## 8. Quick Reference

### Generate Secure Keys

```bash
# JWT Secret (64 chars)
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Fernet Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8001/api/health

# Check security headers
curl -D - http://localhost:8001/api/health -o /dev/null

# Check rate limit headers
curl -D - http://localhost:8001/api/templates/categories -o /dev/null | grep X-RateLimit

# Check cache headers
curl -D - http://localhost:8001/api/templates/categories -o /dev/null | grep X-Cache
```

### Logs

```bash
# Backend logs
tail -f /var/log/supervisor/backend.err.log

# Look for slow requests
grep "Slow request" /var/log/supervisor/backend.err.log

# Look for rate limiting
grep "Rate limit exceeded" /var/log/supervisor/backend.err.log
```

---

**ThookAI is now production-ready!** 🚀
