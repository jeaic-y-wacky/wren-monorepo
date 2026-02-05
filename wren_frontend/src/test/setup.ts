import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

// Mock supabase globally — every module importing @/lib/supabase gets this
vi.mock('@/lib/supabase', () => {
  const mockSupabase = {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: null },
        error: null,
      }),
      signInWithPassword: vi.fn(),
      signInWithOAuth: vi.fn(),
      signOut: vi.fn(),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
    },
  }
  return { supabase: mockSupabase }
})
