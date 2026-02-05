import { describe, it, expect, vi, beforeEach } from 'vitest'
import { supabase } from '@/lib/supabase'
import { apiFetch, api } from '@/lib/api'

// Cast the mock for type-safe access
const mockSupabase = vi.mocked(supabase)

// Capture global fetch
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  vi.clearAllMocks()
  mockSupabase.auth.getSession.mockResolvedValue({
    data: { session: null },
    error: null,
  } as never)
})

// Helper to create a mock Response
function mockResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(typeof body === 'string' ? body : JSON.stringify(body)),
  } as Response
}

describe('apiFetch', () => {
  it('attaches Bearer token from session', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: {
        session: { access_token: 'test-token-123' },
      },
      error: null,
    } as never)
    mockFetch.mockResolvedValue(mockResponse({ ok: true }))

    await apiFetch('/v1/test')

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/v1/test',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token-123',
        }),
      }),
    )
  })

  it('works without session (no auth header)', async () => {
    mockFetch.mockResolvedValue(mockResponse({ ok: true }))

    await apiFetch('/v1/test')

    const callHeaders = mockFetch.mock.calls[0][1].headers
    expect(callHeaders).not.toHaveProperty('Authorization')
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValue(mockResponse('Not Found', false, 404))

    await expect(apiFetch('/v1/missing')).rejects.toThrow('Not Found')
  })
})

describe('api.deployments', () => {
  it('list() unwraps {deployments: [...]}', async () => {
    const deployments = [{ id: '1', name: 'test' }]
    mockFetch.mockResolvedValue(mockResponse({ deployments }))

    const result = await api.deployments.list()

    expect(result).toEqual(deployments)
  })
})

describe('api.runs', () => {
  it('list() unwraps {runs: [...]}', async () => {
    const runs = [{ id: 'r1', status: 'success' }]
    mockFetch.mockResolvedValue(mockResponse({ runs }))

    const result = await api.runs.list('d1')

    expect(result).toEqual(runs)
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/v1/deployments/d1/runs',
      expect.anything(),
    )
  })
})

describe('api.credentials', () => {
  it('get() returns null on error', async () => {
    mockFetch.mockResolvedValue(mockResponse('Server Error', false, 500))

    const result = await api.credentials.get('discord')

    expect(result).toBeNull()
  })

  it('save() sends {credentials: {...}}', async () => {
    mockFetch.mockResolvedValue(mockResponse({ configured: true, updated_at: '2025-01-01' }))

    await api.credentials.save('slack', { token: 'xoxb-123' })

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/v1/credentials/slack',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ credentials: { token: 'xoxb-123' } }),
      }),
    )
  })
})
