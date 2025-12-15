# Authentication System

MedAnki uses Google OAuth 2.0 for user authentication with JWT tokens for session management.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  React Frontend │────▶│  FastAPI Backend│────▶│  Google OAuth   │
│  @react-oauth   │     │  /api/auth/*    │     │  Token Verify   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        │                       ▼
        │               ┌─────────────────┐
        │               │  SQLite Store   │
        │               │  users table    │
        │               │  saved_cards    │
        │               └─────────────────┘
        │                       │
        ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  localStorage   │     │  JWT Service    │
│  auth_token     │     │  python-jose    │
└─────────────────┘     └─────────────────┘
```

## Components

### Backend Services

- **GoogleAuthService** (`packages/core/src/medanki/services/google_auth.py`)
  - Verifies Google ID tokens using `google-auth` library
  - Extracts user info (email, name, picture)

- **JWTService** (`packages/core/src/medanki/services/jwt_service.py`)
  - Creates and verifies JWT access tokens
  - Configurable expiry (default 24 hours)

- **UserRepository** (`packages/core/src/medanki/storage/user_repository.py`)
  - CRUD operations for users and saved cards
  - Async SQLite operations via aiosqlite

### API Routes

- **POST /api/auth/google** - Exchange Google token for JWT
- **GET /api/auth/me** - Get current user (requires auth)
- **POST /api/saved-cards** - Save cards to user account
- **GET /api/saved-cards** - List user's saved cards
- **DELETE /api/saved-cards/{card_id}** - Remove saved card
- **GET /api/saved-cards/export** - Export as .apkg file

### Frontend Components

- **GoogleLoginButton** (`web/src/components/GoogleLoginButton.tsx`)
  - Renders Google Sign-In button using `@react-oauth/google`
  - Handles OAuth callback and token exchange

- **UserMenu** (`web/src/components/UserMenu.tsx`)
  - Displays user avatar and name when authenticated
  - Provides logout functionality

- **SaveCardsButton** (`web/src/components/SaveCardsButton.tsx`)
  - Saves selected cards to user account
  - Shows login prompt if not authenticated

- **authStore** (`web/src/stores/authStore.ts`)
  - Zustand store for auth state management
  - Persists token to localStorage

## Environment Variables

### Backend (`.env`)
```bash
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256  # optional, default HS256
JWT_EXPIRY_HOURS=24  # optional, default 24
```

### Frontend (`web/.env`)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
```

## Database Schema

### users table
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    google_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    picture TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### saved_cards table
```sql
CREATE TABLE saved_cards (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    job_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, card_id)
);
```

## Authentication Flow

1. User clicks "Sign in with Google" button
2. Google OAuth popup opens, user authenticates
3. Frontend receives Google ID token
4. Frontend sends token to `/api/auth/google`
5. Backend verifies token with Google
6. Backend creates/retrieves user in database
7. Backend generates JWT and returns to frontend
8. Frontend stores JWT in localStorage
9. Subsequent requests include JWT in Authorization header

## Testing

### Unit Tests
- `tests/unit/services/test_google_auth.py` - GoogleAuthService tests
- `tests/unit/services/test_jwt_service.py` - JWTService tests
- `tests/unit/storage/test_user_repository.py` - UserRepository tests
- `tests/unit/api/test_auth_routes.py` - Auth route tests
- `tests/unit/api/test_saved_cards_routes.py` - Saved cards route tests
- `web/src/stores/__tests__/authStore.test.ts` - Auth store tests
- `web/src/components/__tests__/GoogleLoginButton.test.tsx`
- `web/src/components/__tests__/SaveCardsButton.test.tsx`

### Integration Tests
- `tests/integration/test_auth_api.py` - Full auth flow with mocked Google

### E2E Tests
- `tests/e2e/auth.spec.ts` - Auth UI flows
- `tests/e2e/saved-cards.spec.ts` - Saved cards flows

## Security Considerations

- JWT tokens expire after 24 hours by default
- Google tokens are verified server-side
- User passwords are never stored (OAuth only)
- CORS configured to allow frontend origin
- Protected routes require valid JWT in Authorization header
