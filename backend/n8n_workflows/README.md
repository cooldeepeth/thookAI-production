# n8n Workflow Templates

These JSON files define the 7 scheduled workflows that replaced Celery beat
in Phase 9. Import them into your n8n instance to activate scheduling.

## Prerequisites

Set these environment variables on the n8n container before activating workflows:

- `N8N_BACKEND_CALLBACK_URL` — URL to reach FastAPI (e.g., `http://backend:8001` in
  Docker Compose, or the public URL in production such as `https://api.yourdomain.com`)
- `N8N_WEBHOOK_SECRET` — shared secret for HMAC-SHA256 signing (must match
  `N8N_WEBHOOK_SECRET` in FastAPI's `.env`)

## Import Instructions

### Via n8n UI

1. Open n8n at http://localhost:5678
2. Click "Workflows" in the left sidebar
3. Click the "+" button and choose "Import from File"
4. Select each JSON file from this directory one at a time
5. After import, click the "Active" toggle on each workflow to enable scheduling

### Via n8n REST API

```bash
N8N_API_KEY="your-n8n-api-key"
N8N_URL="http://localhost:5678"

for f in backend/n8n_workflows/*.json; do
  curl -X POST "$N8N_URL/api/v1/workflows" \
    -H "Content-Type: application/json" \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    -d @"$f"
  echo "Imported: $f"
done
```

After import, activate each workflow via:

```bash
# List workflow IDs
curl "$N8N_URL/api/v1/workflows" -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data[] | {id, name}'

# Activate by ID
curl -X PATCH "$N8N_URL/api/v1/workflows/{id}" \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -d '{"active": true}'
```

## Workflow Schedule Map

| Workflow | Cron | Frequency | Original Celery Task |
|----------|------|-----------|---------------------|
| cleanup-stale-jobs | `*/10 * * * *` | Every 10 min | cleanup_stale_running_jobs |
| cleanup-old-jobs | `0 2 * * *` | Daily 02:00 UTC | cleanup_old_jobs |
| cleanup-expired-shares | `30 2 * * *` | Daily 02:30 UTC | cleanup_expired_shares |
| reset-daily-limits | `0 0 * * *` | Daily 00:00 UTC | reset_daily_limits |
| refresh-monthly-credits | `5 0 1 * *` | 1st of month 00:05 UTC | refresh_monthly_credits |
| aggregate-daily-analytics | `0 1 * * *` | Daily 01:00 UTC | aggregate_daily_analytics |
| process-scheduled-posts | `*/5 * * * *` | Every 5 min | process_scheduled_posts |

## Workflow Structure

Each workflow follows a 3-node pattern:

```
Cron Trigger → Execute Task (POST /api/n8n/execute/{task}) → Callback (POST /api/n8n/callback)
```

1. **Cron Trigger** — fires on the configured schedule
2. **Execute Task** — sends an HMAC-signed POST to the FastAPI execute endpoint
3. **Callback** — sends an HMAC-signed POST to `/api/n8n/callback` with the execution result

The Callback node includes `affected_user_ids` for `process-scheduled-posts`, which
triggers per-user `workflow_status` notifications via the SSE notification stream.

## HMAC Signing

Each workflow signs its HTTP requests with HMAC-SHA256 using `N8N_WEBHOOK_SECRET`.
The signature is computed over the request body and sent in the `X-ThookAI-Signature`
header.

### If expression-based HMAC doesn't work in your n8n version

Some n8n versions restrict `require('crypto')` in expression fields. If you see
errors like "require is not defined", use a Code node approach instead:

1. Add a **Code node** before each HTTP Request node
2. Set the code to:

```javascript
const crypto = require('crypto');
const secret = $env.N8N_WEBHOOK_SECRET || '';
const body = JSON.stringify({});
const signature = crypto.createHmac('sha256', secret).update(body).digest('hex');
return [{ json: { _signature: signature } }];
```

3. In the HTTP Request node's `X-ThookAI-Signature` header, reference `{{$json._signature}}`

For the Callback node, compute the signature over the full callback payload:

```javascript
const crypto = require('crypto');
const secret = $env.N8N_WEBHOOK_SECRET || '';
const payload = {
  workflow_type: 'your-workflow-name',
  status: $input.first().json.status || 'completed',
  result: $input.first().json.result || {},
  executed_at: new Date().toISOString()
};
const signature = crypto.createHmac('sha256', secret)
  .update(JSON.stringify(payload))
  .digest('hex');
return [{ json: { ...payload, _signature: signature } }];
```

## Cutover Verification

After importing and activating all workflows, verify the full cutover:

1. Confirm `celeryconfig.py` has `beat_schedule = {}` (no Celery beat entries)
2. Confirm `Procfile` has NO `beat:` process line (only `web:` and `worker:`)
3. Confirm `docker-compose.yml` has NO `celery-beat` service
4. Open n8n UI and verify each workflow shows "Active" status
5. Check n8n execution history after the first scheduled run for each workflow
6. For `process-scheduled-posts`: schedule a test post and confirm it publishes within 5 minutes

## Notification Visibility

After workflows run, users receive in-app notifications via the SSE stream:

- `process-scheduled-posts` — "Scheduled posts processed" with publish count
- `reset-daily-limits` — "Daily limits reset"
- `refresh-monthly-credits` — "Monthly credits refreshed"
- `aggregate-daily-analytics` — "Daily analytics aggregated"

Cleanup tasks (`cleanup-stale-jobs`, `cleanup-old-jobs`, `cleanup-expired-shares`)
do NOT send user notifications — they are infrastructure-only operations.
