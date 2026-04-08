# Agent: Persona Sharing — Wire Frontend UI
Sprint: 6 | Branch: feat/persona-sharing-ui | PR target: dev
Depends on: Sprint 5 fully merged
Note: This agent works on the FRONTEND (frontend/src/) — adjust your tooling accordingly

## Context
backend/routes/persona.py has a complete, working shareable persona link system:
- POST /api/persona/share → generates a public share_token with expiry and optional password
- GET /api/persona/public/{share_token} → returns the public persona card
- DELETE /api/persona/share/{share_token} → revokes a share link
But NONE of this is accessible from the UI. The feature is completely hidden.

## Files You Will Touch
- frontend/src/pages/Persona.jsx (or .tsx — check actual filename)  (MODIFY)
- frontend/src/components/PersonaShareModal.jsx                       (CREATE)
- frontend/src/api/persona.js (or wherever API calls live)           (MODIFY)
- frontend/src/pages/PublicPersona.jsx                               (CREATE)
- frontend/src/App.jsx (or router config file)                       (MODIFY — add public route)

## Files You Must Read First (do not modify)
- backend/routes/persona.py             (read the share endpoints — understand request/response)
- frontend/src/                         (list the directory to understand file structure)
- frontend/src/pages/                   (find the Persona page file)
- frontend/src/api/                     (find where API calls are made — understand the pattern)

## Step 1: Add share button to Persona page
In the Persona page component, add a "Share Persona" button near the top right.
Clicking it opens the PersonaShareModal.

## Step 2: Create PersonaShareModal component
A modal that:
1. Shows a "Generate Share Link" button
2. On click, calls POST /api/persona/share with optional expiry (7d, 30d, never) and optional password
3. Displays the returned share URL in a copy-to-clipboard input
4. Shows active share links with a "Revoke" button for each
5. Uses the existing shadcn/ui Modal/Dialog component (check components.json for available components)

## Step 3: Add API functions
In the API client file, add:
- `createPersonaShare(expiryDays, password)` → POST /api/persona/share
- `getPersonaShares()` → GET /api/persona/shares (list active shares)
- `revokePersonaShare(shareToken)` → DELETE /api/persona/share/{token}
- `getPublicPersona(shareToken)` → GET /api/persona/public/{token} (no auth required)

## Step 4: Create PublicPersona page
A public-facing page (no auth required) at route `/p/:shareToken` that:
1. Calls GET /api/persona/public/{shareToken}
2. If password-protected, shows a password input first
3. Displays the persona card beautifully: name, bio, voice characteristics, content pillars, signature phrases
4. Shows ThookAI branding with a "Create your own" CTA linking to signup

## Step 5: Add public route to router
In the app router config, add:
`/p/:shareToken` → PublicPersona page (no auth guard — publicly accessible)

## Definition of Done
- Persona page has "Share Persona" button that opens the modal
- Modal can generate, display, and revoke share links
- /p/:shareToken route works without authentication
- PublicPersona page renders the persona card
- PR created to dev with title: "feat: persona sharing UI — share links, public view"