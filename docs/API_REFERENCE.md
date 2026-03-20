# ThookAI — API Documentation

Base URL: `https://yourdomain.com/api`

All endpoints except public ones require authentication via JWT token in cookies or Authorization header.

---

## Authentication

### Register

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe"
}
```

**Response (200):**
```json
{
  "user_id": "uuid-here",
  "email": "user@example.com",
  "name": "John Doe",
  "onboarding_completed": false,
  "subscription_tier": "free",
  "credits": 100
}
```

### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "user_id": "uuid-here",
  "email": "user@example.com",
  "name": "John Doe",
  "access_token": "jwt-token-here"
}
```

### Google OAuth

```http
GET /api/auth/google
```

Redirects to Google OAuth flow. After authentication, redirects back with session established.

### Get Current User

```http
GET /api/users/me
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "user_id": "uuid-here",
  "email": "user@example.com",
  "name": "John Doe",
  "picture": "https://...",
  "onboarding_completed": true,
  "subscription_tier": "pro",
  "credits": 450,
  "credit_allowance": 500
}
```

---

## Onboarding

### Start Interview

```http
POST /api/onboarding/start
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "session_id": "uuid-here",
  "question_number": 1,
  "question": "What topics do you create content about?",
  "context": "Tell me about your main areas of expertise..."
}
```

### Answer Question

```http
POST /api/onboarding/next-question
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "uuid-here",
  "answer": "I create content about AI, startups, and product management..."
}
```

**Response (200):**
```json
{
  "session_id": "uuid-here",
  "question_number": 2,
  "question": "Who is your target audience?",
  "is_complete": false
}
```

### Complete Onboarding

```http
POST /api/onboarding/complete
Authorization: Bearer <token>
Content-Type: application/json

{
  "social_analysis": {
    "linkedin_url": "https://linkedin.com/in/username",
    "twitter_url": "https://twitter.com/username"
  }
}
```

**Response (200):**
```json
{
  "success": true,
  "persona_engine": {
    "card": {...},
    "voice_fingerprint": {...},
    "uom": {...}
  }
}
```

---

## Persona Engine

### Get My Persona

```http
GET /api/persona/me
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "user_id": "uuid-here",
  "card": {
    "personality_archetype": "Educator",
    "writing_voice_descriptor": "Clear, practical, and engaging",
    "content_niche_signature": "AI and product management",
    "inferred_audience_profile": "Tech founders and PMs",
    "top_content_format": "How-to guides",
    "hook_style": "Question-based hooks",
    "content_pillars": ["AI", "Startups", "Product"],
    "focus_platforms": ["linkedin", "x"],
    "regional_english": "US"
  },
  "voice_fingerprint": {
    "vocabulary_complexity": 0.65,
    "emoji_frequency": 0.05,
    "hook_style_preferences": ["question", "bold_claim"]
  },
  "uom": {
    "burnout_risk": "low",
    "focus_preference": "multi-platform",
    "risk_tolerance": "balanced"
  }
}
```

### Update Persona

```http
PUT /api/persona/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "card": {
    "hook_style": "Bold contrarian statements"
  }
}
```

### Share Persona

```http
POST /api/persona/share
Authorization: Bearer <token>
Content-Type: application/json

{
  "expiry_days": 30
}
```

**Response (200):**
```json
{
  "success": true,
  "share_token": "abc123xyz",
  "share_url": "/creator/abc123xyz",
  "expires_at": "2025-08-15T00:00:00Z",
  "is_permanent": false
}
```

### Get Share Status

```http
GET /api/persona/share/status
Authorization: Bearer <token>
```

### Revoke Share

```http
DELETE /api/persona/share
Authorization: Bearer <token>
```

### Public Persona View (No Auth)

```http
GET /api/persona/public/{share_token}
```

**Response (200):**
```json
{
  "success": true,
  "creator": {
    "name": "John Doe",
    "picture": "https://..."
  },
  "card": {
    "personality_archetype": "Educator",
    "writing_voice_descriptor": "...",
    ...
  },
  "voice_metrics": {...},
  "share_info": {
    "view_count": 42,
    "shared_since": "2025-07-15T00:00:00Z"
  }
}
```

### Regional English Options

```http
GET /api/persona/regional-english/options
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "options": [
    {
      "code": "US",
      "name": "American English",
      "spelling_rules": ["-ize spellings", "color", "theater"],
      "date_format": "MM/DD/YYYY"
    },
    ...
  ]
}
```

### Update Regional English

```http
PUT /api/persona/regional-english
Authorization: Bearer <token>
Content-Type: application/json

{
  "regional_english": "UK"
}
```

---

## Content

### Create Content

```http
POST /api/content/create
Authorization: Bearer <token>
Content-Type: application/json

{
  "topic": "3 lessons from scaling my startup",
  "platform": "linkedin",
  "content_type": "thought_leadership"
}
```

**Response (202):**
```json
{
  "job_id": "uuid-here",
  "status": "processing",
  "message": "Content generation started"
}
```

### Poll Content Status

```http
GET /api/content/poll/{job_id}
Authorization: Bearer <token>
```

**Response (200) - Processing:**
```json
{
  "job_id": "uuid-here",
  "status": "processing",
  "stage": "writing",
  "progress": 75
}
```

**Response (200) - Complete:**
```json
{
  "job_id": "uuid-here",
  "status": "ready",
  "draft": "Here's the generated content...",
  "word_count": 245,
  "platform": "linkedin",
  "metadata": {
    "hook_type": "question",
    "cta_style": "engagement"
  }
}
```

### List Content

```http
GET /api/content?status=ready&platform=linkedin&limit=20&offset=0
Authorization: Bearer <token>
```

### Get Providers Summary

```http
GET /api/content/providers/summary
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "summary": {
    "image": {
      "configured": 2,
      "total": 8,
      "providers": ["openai", "stability"]
    },
    "video": {...},
    "voice": {...}
  }
}
```

---

## Dashboard

### Get Stats

```http
GET /api/dashboard/stats
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "stats": {
    "total_content": 45,
    "scheduled_posts": 8,
    "credits_remaining": 450,
    "platforms_connected": 2
  }
}
```

### Get Daily Brief

```http
GET /api/dashboard/daily-brief
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "brief": {
    "greeting": "Good morning, John!",
    "suggestions": [
      {
        "topic": "AI trends this week",
        "hook": "What if I told you...",
        "platform": "linkedin"
      }
    ],
    "trending_topics": ["AI", "remote work"]
  }
}
```

---

## Scheduling

### Get Calendar

```http
GET /api/dashboard/calendar?month=7&year=2025
Authorization: Bearer <token>
```

### Schedule Content

```http
POST /api/dashboard/schedule
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_id": "uuid-here",
  "platform": "linkedin",
  "scheduled_time": "2025-07-20T09:00:00Z"
}
```

---

## Templates Marketplace

### List Templates

```http
GET /api/templates?platform=linkedin&category=thought_leadership&sort=popular&limit=20
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "templates": [
    {
      "template_id": "uuid-here",
      "title": "The Contrarian Take",
      "category": "thought_leadership",
      "platform": "linkedin",
      "hook_type": "contrarian",
      "hook": "Everyone says X, but...",
      "upvotes": 42,
      "uses_count": 156,
      "author_archetype": "Provocateur",
      "user_upvoted": false
    }
  ],
  "total": 156
}
```

### Get Categories

```http
GET /api/templates/categories
Authorization: Bearer <token>
```

### Get Featured

```http
GET /api/templates/featured
Authorization: Bearer <token>
```

### Publish Template

```http
POST /api/templates
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_id": "uuid-here",
  "title": "My Winning Hook",
  "category": "thought_leadership",
  "tags": ["hooks", "engagement"]
}
```

### Use Template

```http
POST /api/templates/{template_id}/use
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "prefill": {
    "platform": "linkedin",
    "raw_input": "[Template inspiration]...",
    "category": "thought_leadership"
  }
}
```

### Upvote Template

```http
POST /api/templates/{template_id}/upvote
Authorization: Bearer <token>
```

---

## Agency Workspace

### Create Workspace

```http
POST /api/agency/workspace
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Agency",
  "description": "Content team workspace"
}
```

**Note:** Requires Studio or Agency tier.

### List Workspaces

```http
GET /api/agency/workspaces
Authorization: Bearer <token>
```

### Get Workspace

```http
GET /api/agency/workspace/{workspace_id}
Authorization: Bearer <token>
```

### Invite Creator

```http
POST /api/agency/workspace/{workspace_id}/invite
Authorization: Bearer <token>
Content-Type: application/json

{
  "email": "creator@example.com",
  "role": "creator"
}
```

### List Members

```http
GET /api/agency/workspace/{workspace_id}/members
Authorization: Bearer <token>
```

### List Creators

```http
GET /api/agency/workspace/{workspace_id}/creators
Authorization: Bearer <token>
```

### Get Workspace Content

```http
GET /api/agency/workspace/{workspace_id}/content?status=ready&limit=50
Authorization: Bearer <token>
```

### Accept Invitation

```http
POST /api/agency/invitations/{invite_id}/accept
Authorization: Bearer <token>
```

### Decline Invitation

```http
POST /api/agency/invitations/{invite_id}/decline
Authorization: Bearer <token>
```

---

## Billing

### Get Credits

```http
GET /api/billing/credits
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "credits": 450,
  "credit_allowance": 500,
  "subscription_tier": "pro",
  "reset_date": "2025-08-01T00:00:00Z"
}
```

### Get Subscription

```http
GET /api/billing/subscription
Authorization: Bearer <token>
```

### Upgrade Subscription

```http
POST /api/billing/subscription/upgrade
Authorization: Bearer <token>
Content-Type: application/json

{
  "tier": "pro"
}
```

### Get Transactions

```http
GET /api/billing/transactions?limit=20
Authorization: Bearer <token>
```

---

## Platform Connections

### Available Platforms

```http
GET /api/platforms/available
Authorization: Bearer <token>
```

### Connected Platforms

```http
GET /api/platforms/connected
Authorization: Bearer <token>
```

### Connect Platform

```http
POST /api/platforms/{platform}/connect
Authorization: Bearer <token>
```

Returns OAuth URL to redirect user for authorization.

### Disconnect Platform

```http
DELETE /api/platforms/{platform}/disconnect
Authorization: Bearer <token>
```

---

## Analytics

### Overview

```http
GET /api/analytics/overview
Authorization: Bearer <token>
```

### Performance Trends

```http
GET /api/analytics/trends?period=30d
Authorization: Bearer <token>
```

---

## Repurpose

### Repurpose Content

```http
POST /api/repurpose
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_id": "uuid-here",
  "target_platform": "x"
}
```

---

## Viral Prediction

### Predict Hook

```http
POST /api/viral/predict
Authorization: Bearer <token>
Content-Type: application/json

{
  "hook": "What if I told you that 90% of startups fail because...",
  "platform": "linkedin"
}
```

**Response (200):**
```json
{
  "success": true,
  "score": 8.5,
  "analysis": {
    "pattern": "curiosity_gap",
    "strengths": ["Creates tension", "Uses statistics"],
    "suggestions": ["Consider adding specificity"]
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

Common HTTP status codes:
- `400` — Bad request (validation error)
- `401` — Unauthorized (missing/invalid token)
- `403` — Forbidden (insufficient permissions/tier)
- `404` — Not found
- `422` — Validation error
- `500` — Server error

---

## Rate Limits

| Endpoint Type | Limit |
|---------------|-------|
| Authentication | 10/minute |
| Content Generation | 20/hour |
| General API | 100/minute |

Exceeded limits return `429 Too Many Requests`.

---

## Webhooks (Coming Soon)

Future support for webhooks on:
- Content generation complete
- Scheduled post published
- Workspace invitation accepted

---

*API Version: 1.0.0*
*Last Updated: July 2025*
