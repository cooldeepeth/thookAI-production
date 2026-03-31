# Coding Conventions

**Analysis Date:** 2026-03-31

## Naming Patterns

**Files:**
- Python: `snake_case.py` (e.g., `auth_utils.py`, `content_tasks.py`)
- React/Frontend: `PascalCase.jsx` for components (e.g., `AuthContext.jsx`), `camelCase.js` for utilities
- UI components from shadcn: `kebab-case.jsx` (e.g., `toggle-group.jsx`, `radio-group.jsx`)

**Functions/Methods:**
- Python: `snake_case()` for all functions and methods
- React: `camelCase()` for all functions, `PascalCase()` for components and custom hooks
- Custom hooks: `useXxx()` pattern (e.g., `useAuth`, `checkAuth`)
- Handler functions: `handleXxx()` or `onXxx()` pattern in React components

**Variables:**
- Python: `snake_case` for all variables and constants. Module-level constants in `UPPER_CASE`
- React/JS: `camelCase` for all variables, `UPPER_CASE` for constants
- Environment variables: `UPPER_CASE` with underscores (e.g., `REACT_APP_BACKEND_URL`, `MONGO_URL`)

**Types:**
- Python: Use type hints for all functions (PEP 484). Import from `typing` module
- React: No TypeScript — JSDoc comments used sparingly
- Dataclasses in Python: All config uses `@dataclass` decorator with field factories

**Database Models:**
- MongoDB collections referenced as `db.collection_name` throughout
- Query operations use Motor async methods: `await db.collection.find_one()`, `await db.collection.insert_one()`
- Fields in documents use `snake_case`

## Code Style

**Formatting:**
- Python: Black formatter (configured in `requirements.txt`)
- React/Frontend: No explicit formatter configured, uses React Scripts defaults
- Line length: Implicit 88-char limit (Black default)

**Linting:**
- Python: 
  - flake8 for style checks
  - isort for import sorting (configured in `requirements.txt`)
  - mypy for type checking
- React/Frontend:
  - ESLint with react-app config + custom rules in `package.json`
  - Rule: `react-hooks/exhaustive-deps: warn` (allows warnings, not errors)

**Import Organization:**
- Python order (per isort):
  1. Future imports (`from __future__ import`)
  2. Standard library (`os`, `logging`, `asyncio`, etc.)
  3. Third-party (`fastapi`, `pymongo`, `pydantic`, etc.)
  4. Local imports (`from database import db`, `from config import settings`)
- React order:
  1. React/hooks (`import React`, `import { useState }`)
  2. Third-party UI (`@radix-ui`, `lucide-react`)
  3. Local utilities (`from @/lib/utils`, `from @/context/AuthContext`)
  4. Styles/CSS last

**Path Aliases:**
- React: `@/*` maps to `src/*` (defined in `jsconfig.json`)
- Backend: No path aliases, relative imports from project root

## Error Handling

**Python Patterns:**
- Use explicit exception catching: `except SpecificException as e:`
- Always log before re-raising: `logger.warning(f"Issue: {e}")` then `raise`
- For API routes: raise `HTTPException(status_code=xxx, detail="message")`
- Use try/finally blocks to ensure cleanup (especially for database connections)
- Log at appropriate levels: `logger.warning()` for recoverable issues, `logger.error()` for failures, `logger.critical()` for severe startup issues

**React Patterns:**
- Use bare `catch { }` blocks (no error object) in async operations
- Catch errors in useEffect/useCallback but don't necessarily rethrow — often just set UI state (e.g., `setUser(null)`)
- No formal error boundaries detected — errors logged to browser console

**Example from codebase:**
```python
# backend/services/llm_client.py
try:
    return settings.llm.openai_key or constructor_key
except Exception:
    return constructor_key
```

```javascript
// frontend/src/context/AuthContext.jsx
try {
  const token = localStorage.getItem("thook_token");
  // ... operation
} catch {
  setUser(null);
} finally {
  setLoading(false);
}
```

## Logging

**Framework:**
- Python: `logging` module (standard library)
- React: No formal logging library — uses `console` (with TODO for Sentry)

**Patterns:**
- Python: Logger initialized per-module: `logger = logging.getLogger(__name__)`
- Log critical startup info in `server.py` lifespan context manager: `logger.info("Starting ThookAI API...")`
- Use structured logging with f-strings: `logger.info(f"User {user_id} registered")`
- Security-sensitive data (passwords, tokens) NEVER logged
- All database operations log at DEBUG level or on error at WARNING level

**Example:**
```python
# backend/server.py
logger = logging.getLogger(__name__)
logger.info("Starting ThookAI API...")
if not settings.security.jwt_secret_key:
    raise RuntimeError("JWT_SECRET_KEY must be set in production")
```

## Comments

**When to Comment:**
- Comment non-obvious logic: why something is done, not what is being done
- Document complex algorithms with docstrings
- Mark known issues with `# TODO:` or `# FIXME:` (searchable)
- Mark important assumptions with `# NOTE:` or `# IMPORTANT:`

**Docstring Style:**
- Python: Triple-quoted docstrings on functions and classes
  ```python
  def validate(self, password: str) -> tuple[bool, list[str]]:
      """
      Validate password against policy.
      Returns (is_valid, list_of_errors)
      """
  ```
- Multiline docstrings preferred for public APIs and services
- React: JSDoc-style comments rare; prefer clear code over comments

## Function Design

**Size:**
- Python: Aim for functions under 50 lines
- React components: Aim for under 100 lines (split larger components)
- Complex logic extracted to helper functions

**Parameters:**
- Python: Use type hints for all parameters
- Python: Pass configuration via `settings` singleton, not function arguments
- React: Props validated by usage (no PropTypes), optional props have defaults
- Use dataclasses (Python) or objects (React) for multiple related parameters

**Return Values:**
- Python functions should return typed values: `-> str`, `-> dict`, `-> List[str]`, `-> Optional[dict]`
- React components return JSX
- Async functions return the same types wrapped in a coroutine
- Database queries return `dict` or `None` (single) or `List[dict]` (multiple)

**Example:**
```python
# backend/auth_utils.py
def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain, hashed)
```

## Module Design

**Exports:**
- Python modules export functions/classes at module level (no `__all__` required but ok to use)
- React components export as named exports: `export function Button() { }`
- Services in `backend/services/` export a class or set of functions as the API

**Barrel Files:**
- Not used in Python backend
- React UI components in `src/components/ui/` are individual files, not re-exported from index

**Example Structure:**
```
backend/
  services/
    llm_client.py        # exports: LlmChat, MessageRole, ConversationMessage
    stripe_service.py    # exports: StripeService class
    persona_refinement.py # exports: functions
```

## Config Pattern (Critical)

**All configuration must:**
1. Come from `backend/config.py` dataclasses
2. Read from environment via `field(default_factory=lambda: os.environ.get(...))`
3. Be accessed via `from config import settings`
4. Never use `os.environ.get()` directly in route/agent/service files

**Example:**
```python
# backend/routes/auth.py
from config import settings

SECRET_KEY = settings.security.jwt_secret_key
```

NOT:
```python
SECRET_KEY = os.environ.get('JWT_SECRET_KEY')  # WRONG
```

## Database Pattern (Critical)

**All database access:**
1. Use `from database import db`
2. Call Motor async methods: `await db.collection.find_one(...)`, `await db.collection.insert_one(...)`
3. Never use synchronous PyMongo calls
4. Query filters as dicts: `{"email": user_email, "_id": 0}` (second param = projection)

**Example:**
```python
# backend/routes/auth.py
from database import db

user = await db.users.find_one({"email": data.email}, {"_id": 0})
```

---

*Convention analysis: 2026-03-31*
