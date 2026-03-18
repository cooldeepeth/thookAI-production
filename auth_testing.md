# ThookAI Auth Testing Playbook

## Step 1: Create Test User & Session
```bash
mongosh --eval "
use('thook_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  auth_method: 'google',
  plan: 'free',
  credits: 100,
  onboarding_completed: false,
  platforms_connected: [],
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test Backend API
```bash
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)

# Test auth/me
curl -X GET "$API_URL/api/auth/me" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"

# Test register
curl -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@test.com","password":"Test1234!","name":"Test User"}'

# Test login
curl -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@test.com","password":"Test1234!"}'
```

## Step 3: Browser Testing
```python
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "your-app.com",
    "path": "/",
    "httpOnly": True,
    "secure": True,
    "sameSite": "None"
}])
await page.goto("https://your-app.com/dashboard")
```

## Checklist
- [ ] User document has user_id field
- [ ] Session user_id matches user's user_id
- [ ] All queries use {"_id": 0} projection
- [ ] /api/auth/me returns user data
- [ ] Dashboard loads without redirect
- [ ] Register creates new user
- [ ] Login sets cookie
- [ ] Logout clears cookie + session

## Success Indicators
- /api/auth/me returns user data (200)
- Dashboard loads without redirect to /auth
- CRUD operations work with session token

## Failure Indicators
- "User not found" errors
- 401 Unauthorized responses
- Redirect to login page
