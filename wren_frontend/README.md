# Wren Frontend

A minimal React dashboard for managing Wren deployments.

## Tech Stack

- **Vite** - Build tool
- **React 18** - UI library
- **TanStack Router** - Type-safe file-based routing
- **TanStack Query** - Data fetching (ready to add)
- **Tailwind CSS v4** - Styling
- **Supabase** - Authentication

## Quick Start

```bash
# Install dependencies
npm install

# Copy environment file and fill in your values
cp .env.example .env

# Start development server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

## Environment Variables

Create a `.env` file with:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_WREN_API_URL=http://localhost:8000
```

Get these from your Supabase project dashboard under Settings > API.

## Project Structure

```
src/
├── lib/
│   ├── supabase.ts    # Supabase client
│   ├── api.ts         # Backend API client + types
│   └── utils.ts       # Utility functions (cn)
├── routes/
│   ├── __root.tsx     # Root layout
│   ├── login.tsx      # /login - Auth page
│   ├── _authenticated.tsx      # Protected layout with sidebar
│   └── _authenticated/
│       ├── index.tsx           # / - Dashboard
│       ├── deployments.tsx     # /deployments
│       └── integrations.tsx    # /integrations
├── components/        # Reusable components (add as needed)
├── types/             # TypeScript types (add as needed)
└── main.tsx           # Entry point
```

## Routing

Uses [TanStack Router](https://tanstack.com/router) with file-based routing:

- Files in `src/routes/` automatically become routes
- `_authenticated.tsx` is a layout route that protects child routes
- `$param.tsx` creates dynamic routes (e.g., `deployments.$id.tsx`)
- Route tree is auto-generated in `routeTree.gen.ts`

### Adding a new protected route

1. Create `src/routes/_authenticated/my-page.tsx`:

```tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_authenticated/my-page')({
  component: MyPage,
})

function MyPage() {
  return <div>My Page</div>
}
```

2. Add link to sidebar in `_authenticated.tsx`

## Authentication

Auth is handled by Supabase. The flow:

1. User visits any protected route
2. `_authenticated.tsx` checks for session via `beforeLoad`
3. No session → redirect to `/login`
4. Login form calls `supabase.auth.signInWithPassword()` or OAuth
5. On success → redirect to dashboard

### Using auth in components

```tsx
import { supabase } from '@/lib/supabase'

// Get current session
const { data: { session } } = await supabase.auth.getSession()

// Sign out
await supabase.auth.signOut()

// Listen for auth changes
supabase.auth.onAuthStateChange((event, session) => {
  console.log(event, session)
})
```

## API Client

The `lib/api.ts` provides a fetch wrapper that automatically adds auth headers:

```tsx
import { api } from '@/lib/api'

// List deployments
const deployments = await api.deployments.list()

// Get single deployment
const deployment = await api.deployments.get('dep_123')
```

### Adding TanStack Query (recommended)

Install and create hooks:

```tsx
// lib/queries.ts
import { useQuery } from '@tanstack/react-query'
import { api } from './api'

export function useDeployments() {
  return useQuery({
    queryKey: ['deployments'],
    queryFn: api.deployments.list,
  })
}
```

Wrap app with QueryClientProvider in `__root.tsx`.

## Styling

Uses Tailwind CSS v4 with the Vite plugin. Just use utility classes:

```tsx
<div className="flex items-center gap-4 p-4 bg-gray-100 rounded-lg">
  <h1 className="text-2xl font-bold">Title</h1>
</div>
```

### Adding shadcn/ui components

```bash
npx shadcn@latest add button card input
```

Components are copied to `src/components/ui/`.

## Scripts

```bash
npm run dev      # Start dev server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## Extending

### Add a new page with data fetching

1. Create route file
2. Add TanStack Query hook
3. Use hook in component with loading/error states

### Add a form

1. Install `react-hook-form` and `zod`
2. Create form component with validation
3. Submit via mutation hook

### Add real-time updates

```tsx
import { supabase } from '@/lib/supabase'

// Subscribe to changes
const channel = supabase
  .channel('runs')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'runs' },
    (payload) => console.log(payload)
  )
  .subscribe()

// Cleanup
channel.unsubscribe()
```
