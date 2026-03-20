# ThookAI — Admin Setup Guide

This guide covers everything needed to deploy and configure ThookAI for production.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Requirements](#server-requirements)
3. [Database Setup](#database-setup)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [API Keys Configuration](#api-keys-configuration)
7. [OAuth Setup](#oauth-setup)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Recovery](#backup--recovery)
10. [Scaling Considerations](#scaling-considerations)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| MongoDB | 6+ | Primary database |
| Nginx | Latest | Reverse proxy |
| Supervisor | Latest | Process management |

### Required Accounts

- **Emergent Platform** — For LLM integration (required)
- **Perplexity AI** — For research agent (required)
- **Social Platform Developer Accounts** — For OAuth (optional)
- **Creative AI Providers** — For media generation (optional)

---

## Server Requirements

### Minimum (Development/Testing)

- **CPU:** 2 cores
- **RAM:** 4 GB
- **Storage:** 20 GB SSD
- **Bandwidth:** 100 Mbps

### Recommended (Production)

- **CPU:** 4+ cores
- **RAM:** 8+ GB
- **Storage:** 100 GB SSD
- **Bandwidth:** 1 Gbps

### Scaling Notes

- Content generation is CPU-intensive during AI calls
- MongoDB can be offloaded to Atlas for managed scaling
- Consider Redis for session storage at scale

---

## Database Setup

### MongoDB Installation

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Database Initialization

```bash
# Connect to MongoDB
mongosh

# Create database and user
use thook_database

db.createUser({
  user: "thook_admin",
  pwd: "secure-password-here",
  roles: [{ role: "readWrite", db: "thook_database" }]
})
```

### Collections Created Automatically

The application creates these collections on first use:

| Collection | Purpose |
|------------|---------|
| `users` | User accounts and profiles |
| `persona_engines` | AI-generated personas |
| `persona_shares` | Public persona share tokens |
| `content_jobs` | Content generation jobs |
| `scheduled_posts` | Calendar scheduled content |
| `templates` | Community templates |
| `template_upvotes` | Template voting |
| `workspaces` | Agency workspaces |
| `workspace_members` | Workspace team members |
| `credit_transactions` | Credit usage history |
| `subscription_history` | Tier change history |

### Recommended Indexes

```javascript
// Users
db.users.createIndex({ "email": 1 }, { unique: true })
db.users.createIndex({ "user_id": 1 }, { unique: true })

// Persona
db.persona_engines.createIndex({ "user_id": 1 }, { unique: true })
db.persona_shares.createIndex({ "share_token": 1 }, { unique: true })
db.persona_shares.createIndex({ "user_id": 1 })

// Content
db.content_jobs.createIndex({ "user_id": 1 })
db.content_jobs.createIndex({ "job_id": 1 }, { unique: true })
db.content_jobs.createIndex({ "created_at": -1 })

// Templates
db.templates.createIndex({ "template_id": 1 }, { unique: true })
db.templates.createIndex({ "is_active": 1, "upvotes": -1 })
db.templates.createIndex({ "platform": 1, "category": 1 })

// Workspaces
db.workspaces.createIndex({ "workspace_id": 1 }, { unique: true })
db.workspaces.createIndex({ "owner_id": 1 })
db.workspace_members.createIndex({ "workspace_id": 1, "user_id": 1 })
```

---

## Backend Deployment

### 1. Clone and Configure

```bash
cd /var/www
git clone https://github.com/your-org/thook-ai.git
cd thook-ai/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Critical settings to change:**

```env
# Database
MONGO_URL="mongodb://thook_admin:password@localhost:27017/thook_database"
DB_NAME="thook_database"

# Security (MUST CHANGE)
JWT_SECRET_KEY=generate-a-random-64-char-string-here
CORS_ORIGINS="https://yourdomain.com"

# API Keys (add your keys)
EMERGENT_LLM_KEY=sk-emergent-your-key
PERPLEXITY_API_KEY=pplx-your-key
```

### 3. Supervisor Configuration

Create `/etc/supervisor/conf.d/thook-backend.conf`:

```ini
[program:thook-backend]
command=/var/www/thook-ai/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
directory=/var/www/thook-ai/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/thook-backend.err.log
stdout_logfile=/var/log/supervisor/thook-backend.out.log
environment=PATH="/var/www/thook-ai/backend/venv/bin"
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start thook-backend
```

### 4. Nginx Configuration

Create `/etc/nginx/sites-available/thook`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend
    location / {
        root /var/www/thook-ai/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/thook /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Frontend Deployment

### 1. Configure Environment

```bash
cd /var/www/thook-ai/frontend
nano .env
```

```env
REACT_APP_BACKEND_URL=https://yourdomain.com
```

### 2. Build

```bash
yarn install
yarn build
```

The built files will be in `/frontend/dist` and served by Nginx.

---

## API Keys Configuration

### Priority Order

Configure APIs in this order based on importance:

#### Tier 1 — Required for Core Features

| API | Environment Variable | How to Get |
|-----|---------------------|------------|
| Emergent LLM | `EMERGENT_LLM_KEY` | Emergent Platform → Profile → Universal Key |
| Perplexity | `PERPLEXITY_API_KEY` | perplexity.ai → Settings → API |

#### Tier 2 — Required for Social Publishing

| API | Environment Variable | How to Get |
|-----|---------------------|------------|
| LinkedIn | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | LinkedIn Developers Portal |
| Twitter/X | `TWITTER_API_KEY`, `TWITTER_API_SECRET`, etc. | Twitter Developer Portal |
| Meta | `META_APP_ID`, `META_APP_SECRET` | Meta for Developers |

#### Tier 3 — Enhanced Features

| API | Environment Variable | How to Get |
|-----|---------------------|------------|
| ElevenLabs | `ELEVENLABS_API_KEY` | elevenlabs.io → Settings → API |
| OpenAI Images | `OPENAI_IMAGE_API_KEY` | platform.openai.com |
| Stability AI | `STABILITY_API_KEY` | platform.stability.ai |

#### Tier 4 — Optional/Advanced

| API | Environment Variable | Purpose |
|-----|---------------------|---------|
| Pinecone | `PINECONE_API_KEY` | Persona learning |
| Runway ML | `RUNWAY_API_KEY` | Video generation |
| FAL AI | `FAL_API_KEY` | Fast image inference |

---

## OAuth Setup

### LinkedIn

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps)
2. Create new app
3. Request these products:
   - Sign In with LinkedIn using OpenID Connect
   - Share on LinkedIn
4. Add redirect URL: `https://yourdomain.com/api/platforms/linkedin/callback`
5. Copy Client ID and Secret to `.env`

### Twitter/X

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create project and app
3. Enable OAuth 1.0a with Read and Write
4. Add callback URL: `https://yourdomain.com/api/platforms/x/callback`
5. Copy all 4 credentials to `.env`

### Meta (Instagram/Facebook)

1. Go to [Meta for Developers](https://developers.facebook.com/apps/)
2. Create app (Business type)
3. Add Instagram Graph API product
4. Configure OAuth redirect: `https://yourdomain.com/api/platforms/instagram/callback`
5. Copy App ID and Secret to `.env`

---

## Monitoring & Logging

### Log Locations

| Log | Location |
|-----|----------|
| Backend stdout | `/var/log/supervisor/thook-backend.out.log` |
| Backend errors | `/var/log/supervisor/thook-backend.err.log` |
| Nginx access | `/var/log/nginx/access.log` |
| Nginx errors | `/var/log/nginx/error.log` |
| MongoDB | `/var/log/mongodb/mongod.log` |

### Health Check Endpoints

```bash
# Backend health
curl https://yourdomain.com/api/health

# Detailed status (authenticated)
curl -H "Authorization: Bearer $TOKEN" https://yourdomain.com/api/admin/status
```

### Recommended Monitoring

- **Uptime:** UptimeRobot, Pingdom
- **Errors:** Sentry, LogRocket
- **APM:** New Relic, Datadog
- **Logs:** ELK Stack, Papertrail

---

## Backup & Recovery

### MongoDB Backup

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
mongodump --db thook_database --out /backups/mongodb/$DATE
# Keep 7 days
find /backups/mongodb -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /usr/local/bin/backup-thook.sh
```

### Restore

```bash
mongorestore --db thook_database /backups/mongodb/20250715_020000/thook_database
```

---

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancer** — Add Nginx upstream with multiple backend instances
2. **Session Storage** — Use Redis for JWT token blacklist
3. **Database** — Migrate to MongoDB Atlas replica set
4. **CDN** — CloudFlare or AWS CloudFront for static assets

### Vertical Scaling

1. **AI Operations** — Increase CPU for content generation
2. **Memory** — More RAM for concurrent users
3. **Storage** — SSD for faster MongoDB operations

### Queue System (Future)

For high volume, consider adding:
- **Celery + Redis** for background job processing
- **Separate worker nodes** for AI generation

---

## Security Checklist

- [ ] Change `JWT_SECRET_KEY` (min 64 chars random)
- [ ] Set `CORS_ORIGINS` to production domain only
- [ ] Enable MongoDB authentication
- [ ] Configure firewall (only 80/443 open)
- [ ] Set up SSL with Let's Encrypt
- [ ] Enable rate limiting in Nginx
- [ ] Regular security updates
- [ ] Backup encryption at rest

---

## Support

For issues or questions:
1. Check logs first
2. Review API documentation at `/docs`
3. Contact support@yourdomain.com

---

*Last updated: July 2025*
