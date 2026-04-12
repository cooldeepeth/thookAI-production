# Phase 30 — Validation Map

| Plan | Task | Automated Test Command |
|------|------|------------------------|
| 30-01 | Task 1: Fix _publish_to_platform | `cd backend && pytest tests/test_publishing.py::TestPublishToPlatformFixed -x -q` |
| 30-01 | Task 2: Fix scheduled_tasks | `cd backend && pytest tests/test_publishing.py::TestScheduledTasksFixed -x -q` |
| 30-02 | Task 1: Proactive 24h refresh | `cd backend && pytest tests/test_platform_oauth.py::TestProactiveTokenRefresh -x -q` |
| 30-02 | Task 2: Instagram _refresh_token branch | `cd backend && pytest tests/test_platform_oauth.py::TestInstagramTokenRefresh -x -q` |
| 30-03 | Task 1: token_expiring_soon + Fernet | `cd backend && pytest tests/test_platform_oauth.py::TestTokenExpiringSoon tests/test_platform_oauth.py::TestFernetEncryptionRoundTrip -x -q` |
| 30-03 | Task 2: Full regression suite | `cd backend && pytest tests/test_publishing.py tests/test_platform_oauth.py tests/test_analytics_social.py -x -q` |
| 30-04 | Task 1: LinkedIn media upload | `cd backend && pytest tests/test_publishing.py::TestPublishLinkedInMedia -x -q` |
| 30-04 | Task 2: X media upload + Instagram wiring | `cd backend && pytest tests/test_publishing.py::TestPublishXMedia tests/test_publishing.py::TestPublishInstagramMediaWiring -x -q` |

## Full Phase Gate

```bash
cd backend && pytest tests/test_publishing.py tests/test_platform_oauth.py tests/test_analytics_social.py -x -q
```
