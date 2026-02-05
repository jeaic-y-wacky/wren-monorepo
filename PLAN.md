# Wren Authentication & Frontend Implementation Plan

## What We're Building

We're adding a web interface to Wren so users can sign up, log in, and manage their deployments through a browser. Currently, wren_backend has no real authentication. We're adding proper authentication using Supabase.

**End result:** Users sign up on our frontend, get a real account, and can view/manage their Wren deployments through a dashboard.

---

## High-Level Architecture

### The Flow

1. User visits our frontend (a Vite + React app)
2. User signs up or logs in via Supabase Auth (email/password or Google/GitHub OAuth)
3. Supabase returns a JWT that proves who the user is
4. Frontend stores the JWT and includes it in every request to wren_backend
5. wren_backend calls Supabase's `auth.get_user(jwt)` to validate the token and get user info
6. Request proceeds with the verified user ID

### Why Supabase for Auth?

Supabase handles the hard parts of authentication: password hashing, email verification, OAuth flows with Google/GitHub, session management, and token refresh. It also provides a Postgres database we can use for user-related data. The Python SDK can validate JWTs with a single function call, and the free tier is generous enough for getting started.

### Why Vite + React?

Our dashboard is entirely behind authentication, so there's no SEO benefit from server-side rendering. Vite's dev server starts in milliseconds compared to seconds for Next.js. The mental model is simpler - it's just a React app that talks to our existing backend. Deployment is also easier since it's just static files that can be hosted anywhere.

### Why TanStack Router + Query?

TanStack Router provides fully type-safe routing. Route parameters, search parameters, and loaders are all typed, which catches routing errors at compile time rather than runtime. TanStack Query handles data fetching with automatic caching, background refetching, and mutation state management. When you navigate away from a page and back, data loads instantly from cache while refetching in the background. The two libraries are designed to work together - the router can prefetch data into Query's cache during navigation.

---

## Backend Changes

### Current State

The backend currently has a placeholder `get_current_user_id` function in `wren_backend/src/wren_backend/api/deps.py` that accepts any token as the user ID with no validation.

### New Behavior

We'll update the `get_current_user_id` dependency to:

1. Extract the JWT from the `Authorization: Bearer <token>` header
2. Call Supabase's `auth.get_user(jwt=token)` which validates the token server-side and returns the user
3. Extract the user's ID and use it for the rest of the request
4. Return 401 if the token is invalid or missing

### Supabase Python SDK

The official SDK provides both sync and async clients:

- **Sync:** `from supabase import create_client, Client`
- **Async:** `from supabase import acreate_client, AsyncClient`

Since wren_backend uses FastAPI with async, we'll use `acreate_client` to create an `AsyncClient`. The client is initialized once at startup with the Supabase URL and service role key.

To validate a JWT, we call `await supabase.auth.get_user(jwt=token)`. This makes a network request to Supabase's auth server, which verifies the token signature, checks expiration, and returns the user object. If the token is invalid, it raises an exception.

**Performance note:** Each call to `get_user()` makes a round-trip to Supabase (~100-600ms). For a dashboard with moderate traffic, this is acceptable. If we later need better performance, we can switch to `get_claims()` (which uses cached JWKS validation) or manual JWT verification with PyJWT.

### CORS Configuration

Since the frontend runs on a different origin than the backend, we need to configure CORS in FastAPI. We'll add the CORS middleware to `main.py` and whitelist:
- `http://localhost:5173` (Vite dev server)
- Our production frontend domain

### New Dependency

We only need to add `supabase` to `pyproject.toml`. No other dependencies required.

### Files to Modify

- `wren_backend/pyproject.toml` - add supabase dependency
- `wren_backend/src/wren_backend/api/deps.py` - update auth logic
- `wren_backend/src/wren_backend/main.py` - add CORS middleware, initialize Supabase client
- `wren_backend/src/wren_backend/core/credentials.py` - update to use Supabase storage instead of in-memory

---

## Supabase Setup

### What Supabase Provides

When you create a Supabase project, you get:
- **Auth service** - handles signup, login, OAuth, password reset, email verification
- **Postgres database** - fully managed, with Row Level Security
- **API keys** - anon key (for frontend), service role key (for backend)
- **JWT secret** - for manual token verification if needed

### Tables We'll Create

**profiles table**

This stores user profile information like display name and preferences. It's linked to Supabase's built-in `auth.users` table via a foreign key on the user ID. We'll create a database trigger that automatically creates a profile row whenever a new user signs up. Row Level Security ensures users can only read and update their own profile.

**credentials table**

This stores OAuth tokens for integrations like Gmail and Slack. Each row contains a user ID, integration name, and the credential data (access token, refresh token, etc.). Row Level Security ensures users can only access their own credentials. Supabase handles encryption at rest, so we don't need to encrypt the data ourselves.

### Row Level Security

Supabase's Row Level Security (RLS) is enforced at the database level. We write policies like "users can only select rows where user_id equals their own ID." Even if our application code has a bug, RLS prevents users from accessing each other's data. This is a defense-in-depth measure.

### OAuth Providers

In the Supabase dashboard under Authentication > Providers, we'll enable Google and GitHub OAuth. This requires creating OAuth apps in the Google Cloud Console and GitHub Developer Settings, then adding the client IDs and secrets to Supabase.

---

## Frontend Structure

### Technology Stack

**Vite** is our build tool. It provides extremely fast hot module replacement during development and optimized production builds.

**React 18** is our UI library. We're using it because of its large ecosystem and good Supabase SDK support.

**TanStack Router** handles routing with full TypeScript support. Routes are defined using a file-based convention where the file structure maps to URL paths.

**TanStack Query** handles server state - fetching data, caching it, and keeping it synchronized. It provides hooks like `useQuery` for fetching and `useMutation` for updates.

**Tailwind CSS** is our styling approach. It's utility-first, which makes building UIs fast without writing custom CSS files.

**shadcn/ui** provides pre-built accessible components like buttons, modals, and forms. Unlike a component library, shadcn/ui copies the component code into your project so you own and can customize it.

### TanStack Router File Conventions

The router uses a file-based routing convention in the `src/routes/` directory:

**`__root.tsx`** is the root route file (required). It wraps the entire application and typically contains the outermost layout, global providers, and the `<Outlet />` where child routes render.

**Underscore prefix (`_name.tsx`)** creates a pathless layout route. The route doesn't add a segment to the URL, but it wraps its children with a layout. For example, `_authenticated.tsx` would wrap all authenticated pages without adding `/authenticated` to the URL.

**Dollar sign (`$param.tsx`)** creates a dynamic route parameter. For example, `deployments.$id.tsx` matches `/deployments/123` and makes `id` available as a typed parameter.

**`.lazy.tsx` suffix** enables code splitting. The component is loaded only when the route is visited. Critical route configuration (loaders, beforeLoad) stays in the main file; only the component is lazy-loaded.

### Project Structure

```
wren_frontend/
├── index.html              # Entry HTML file
├── package.json            # Dependencies and scripts
├── vite.config.ts          # Vite configuration with TanStack Router plugin
├── tsconfig.json           # TypeScript configuration
├── tailwind.config.js      # Tailwind configuration
├── src/
│   ├── main.tsx            # Entry point, renders RouterProvider
│   ├── routeTree.gen.ts    # Auto-generated by TanStack Router plugin
│   ├── routes/
│   │   ├── __root.tsx              # Root layout
│   │   ├── _authenticated.tsx      # Layout for protected routes
│   │   ├── _authenticated/
│   │   │   ├── index.tsx           # Dashboard (/)
│   │   │   ├── deployments.tsx     # Deployments list
│   │   │   ├── deployments.$id.tsx # Deployment detail
│   │   │   └── integrations.tsx    # Integrations page
│   │   ├── login.tsx               # Login page
│   │   └── signup.tsx              # Signup page
│   ├── components/
│   │   ├── ui/                     # shadcn/ui components
│   │   └── ...                     # App-specific components
│   ├── lib/
│   │   ├── supabase.ts             # Supabase client
│   │   ├── api.ts                  # Wren backend API functions
│   │   └── queries.ts              # TanStack Query definitions
│   └── types/
│       └── index.ts                # Shared TypeScript types
```

### Authentication Flow in the Frontend

When the app loads, we need to check if the user has an existing session. Supabase stores session tokens in localStorage, and we use the Supabase JS client to access them.

**Initial load:** We call `supabase.auth.getSession()` to get the current session from localStorage. This is synchronous and doesn't make a network request.

**Listening for changes:** We set up `supabase.auth.onAuthStateChange()` to listen for auth events - sign in, sign out, token refresh. This callback fires whenever the auth state changes, including when a token is refreshed in the background.

**Route protection:** The `_authenticated.tsx` layout route has a `beforeLoad` hook that checks if the user is authenticated. If not, it redirects to `/login`. This runs before the route renders, so unauthenticated users never see protected content.

**API calls:** When making requests to wren_backend, we get the current session's access token and include it in the `Authorization: Bearer <token>` header. TanStack Query's query functions handle this automatically through a shared API client.

### Pages We'll Build

**Login Page (`/login`)**

A form with email and password fields, plus buttons for "Sign in with Google" and "Sign in with GitHub". On successful login, redirects to the dashboard. Shows error messages for invalid credentials.

**Signup Page (`/signup`)**

Similar to login, with email, password, and password confirmation fields. OAuth buttons for Google and GitHub. On successful signup, either redirects to dashboard or shows a "check your email" message depending on whether email verification is required.

**Dashboard (`/`)**

Overview of the user's account. Shows stats like number of deployments, recent run count, success/failure rate. Quick links to create a deployment or view recent activity.

**Deployments List (`/deployments`)**

A table or card grid showing all the user's deployments. Each deployment shows its name, status (active, paused, error), last run time, and last run result. Actions to view details, pause/resume, or delete.

**Deployment Detail (`/deployments/$id`)**

Full information about a single deployment. Shows the script content (read-only), configured triggers, and required integrations. Below that, a run history table showing each execution with status, start time, duration, and a link to view logs.

**Integrations (`/integrations`)**

A list of available integrations (Gmail, Slack, Discord, etc.). Each shows whether it's connected or not. A "Connect" button initiates the OAuth flow for that service. A "Disconnect" button removes the stored credentials.

---

## Environment Variables

### Backend

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Your Supabase project URL (e.g., `https://xxx.supabase.co`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side key that bypasses RLS, used for backend operations |

The service role key should never be exposed to the frontend. It has full access to the database, bypassing Row Level Security.

### Frontend

| Variable | Purpose |
|----------|---------|
| `VITE_SUPABASE_URL` | Same Supabase project URL as backend |
| `VITE_SUPABASE_ANON_KEY` | Public anon key for client-side Supabase operations |
| `VITE_WREN_API_URL` | URL of the wren_backend API (e.g., `http://localhost:8000`) |

The `VITE_` prefix is required by Vite to expose environment variables to browser code. The anon key is safe to expose - it only allows operations permitted by Row Level Security policies.

---

## Implementation Phases

### Phase 1: Supabase Project Setup

Create a new Supabase project and gather the configuration values from the dashboard. Enable Google and GitHub OAuth providers by creating OAuth apps and adding the credentials. Run the SQL to create the profiles and credentials tables with their triggers and RLS policies.

### Phase 2: Backend Changes

Add the `supabase` package to wren_backend's dependencies. Create a Supabase client that's initialized at startup. Update the `get_current_user_id` dependency to validate JWTs via `auth.get_user()`. Add CORS middleware to allow requests from the frontend. Update the credentials storage to use Supabase instead of in-memory.

### Phase 3: Frontend Scaffolding

Create the wren_frontend directory and initialize a Vite React TypeScript project. Install TanStack Router, TanStack Query, Tailwind CSS, and the Supabase JS client. Configure the Vite plugin for TanStack Router's file-based routing. Set up the route structure with placeholder pages. Create the Supabase client and API client utilities.

### Phase 4: Authentication Pages

Build the login page with email/password form and OAuth buttons. Build the signup page. Implement the auth state management using `onAuthStateChange`. Add the protected route layout that redirects unauthenticated users.

### Phase 5: Dashboard Pages

Build the root layout with sidebar navigation and header showing the current user. Build the dashboard overview with stats. Build the deployments list with data fetching via TanStack Query. Build the deployment detail page with run history. Build the integrations page for OAuth connection management.

### Phase 6: Polish and Deploy

Add loading states using TanStack Query's `isPending`. Add error handling and error boundaries. Add toast notifications for successful and failed actions. Test the complete flow end-to-end. Deploy the frontend to a static hosting service. Update CORS configuration for the production domain.

---

## Security Considerations

**Token Validation:** All validation happens server-side via Supabase's `auth.get_user()`. We never trust tokens without verification. Invalid or expired tokens return 401 Unauthorized.

**Row Level Security:** Database-level security ensures users can only access their own data. Even if application code has bugs, RLS prevents unauthorized access.

**CORS:** We only allow requests from our frontend domain. No wildcard origins in production.

**Environment Variables:** Secrets are never committed to git. The service role key and any server-side secrets stay on the backend. Only the anon key (which is designed to be public) is exposed to the frontend.

**Session Storage:** Supabase stores sessions in localStorage. The frontend never handles passwords directly - they're submitted directly to Supabase's auth endpoints.
