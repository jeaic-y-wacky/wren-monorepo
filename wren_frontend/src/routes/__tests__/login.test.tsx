import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { supabase } from '@/lib/supabase'

// Cast mock
const mockSupabase = vi.mocked(supabase)

// Mock TanStack Router hooks
const mockNavigate = vi.fn()
vi.mock('@tanstack/react-router', () => ({
  // createFileRoute('/login') returns a function; that function receives { component: LoginPage }
  // We pass it through so Route.component holds the actual component
  createFileRoute: () => (opts: Record<string, unknown>) => opts,
  useNavigate: () => mockNavigate,
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}))

// Import after mocks are set — Route.component will be the real LoginPage function
import { Route } from '@/routes/login'
const LoginPage = Route.component as () => React.JSX.Element

beforeEach(() => {
  vi.clearAllMocks()
})

describe('LoginPage', () => {
  it('renders email and password form', () => {
    render(<LoginPage />)

    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('shows error on failed login', async () => {
    const user = userEvent.setup()
    mockSupabase.auth.signInWithPassword.mockResolvedValue({
      data: { user: null, session: null },
      error: { message: 'Invalid login credentials' },
    } as never)

    render(<LoginPage />)

    await user.type(screen.getByPlaceholderText('Email'), 'test@example.com')
    await user.type(screen.getByPlaceholderText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Invalid login credentials')).toBeInTheDocument()
  })

  it('calls signInWithPassword on submit', async () => {
    const user = userEvent.setup()
    mockSupabase.auth.signInWithPassword.mockResolvedValue({
      data: { user: {}, session: {} },
      error: null,
    } as never)

    render(<LoginPage />)

    await user.type(screen.getByPlaceholderText('Email'), 'user@test.com')
    await user.type(screen.getByPlaceholderText('Password'), 'pass123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(mockSupabase.auth.signInWithPassword).toHaveBeenCalledWith({
      email: 'user@test.com',
      password: 'pass123',
    })
  })

  it('OAuth buttons call signInWithOAuth', async () => {
    const user = userEvent.setup()
    mockSupabase.auth.signInWithOAuth.mockResolvedValue({
      data: { url: 'https://oauth.example.com' },
      error: null,
    } as never)

    render(<LoginPage />)

    await user.click(screen.getByRole('button', { name: 'Google' }))
    expect(mockSupabase.auth.signInWithOAuth).toHaveBeenCalledWith({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })

    await user.click(screen.getByRole('button', { name: 'GitHub' }))
    expect(mockSupabase.auth.signInWithOAuth).toHaveBeenCalledWith({
      provider: 'github',
      options: { redirectTo: window.location.origin },
    })
  })
})
