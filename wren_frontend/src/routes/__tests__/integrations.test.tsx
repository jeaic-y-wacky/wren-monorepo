import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { api } from '@/lib/api'

// Mock api module
vi.mock('@/lib/api', () => ({
  api: {
    credentials: {
      list: vi.fn(),
      get: vi.fn(),
      save: vi.fn(),
      delete: vi.fn(),
    },
  },
}))

const mockApi = vi.mocked(api)

// Mock TanStack Router
vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (opts: Record<string, unknown>) => opts,
}))

import { Route } from '@/routes/_authenticated/integrations'
const IntegrationsPage = Route.component as () => React.JSX.Element

beforeEach(() => {
  vi.clearAllMocks()
  // Default: no credentials connected
  mockApi.credentials.list.mockResolvedValue([])
  // Suppress window.confirm in tests
  vi.spyOn(window, 'confirm').mockReturnValue(true)
})

describe('IntegrationsPage', () => {
  it('renders all three integrations', async () => {
    render(<IntegrationsPage />)

    expect(await screen.findByText('Discord')).toBeInTheDocument()
    expect(screen.getByText('Slack')).toBeInTheDocument()
    expect(screen.getByText('Gmail')).toBeInTheDocument()
  })

  it('shows "Connected" for configured integrations', async () => {
    mockApi.credentials.list.mockResolvedValue([
      { integration: 'slack', configured: true, updated_at: '2025-01-01' },
    ])

    render(<IntegrationsPage />)

    expect(await screen.findByText('Connected')).toBeInTheDocument()

    // Discord and Gmail should show Connect buttons
    const connectButtons = screen.getAllByRole('button', { name: 'Connect' })
    expect(connectButtons).toHaveLength(2)
  })

  it('opens edit form on Connect click', async () => {
    const user = userEvent.setup()
    render(<IntegrationsPage />)

    // Wait for load
    const connectButtons = await screen.findAllByRole('button', { name: 'Connect' })
    // Click Discord's Connect button (first one)
    await user.click(connectButtons[0])

    // Discord form should appear with Bot Token field (label has no htmlFor, use placeholder)
    expect(screen.getByPlaceholderText('Your Discord bot token')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
  })

  it('validates required fields before save', async () => {
    const user = userEvent.setup()
    render(<IntegrationsPage />)

    const connectButtons = await screen.findAllByRole('button', { name: 'Connect' })
    await user.click(connectButtons[0]) // Open Discord form

    // Click Save without filling required field
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByText('Bot Token is required')).toBeInTheDocument()
    expect(mockApi.credentials.save).not.toHaveBeenCalled()
  })

  it('calls api.credentials.save on save', async () => {
    const user = userEvent.setup()
    mockApi.credentials.save.mockResolvedValue({ configured: true, updated_at: '2025-01-01' })

    render(<IntegrationsPage />)

    const connectButtons = await screen.findAllByRole('button', { name: 'Connect' })
    await user.click(connectButtons[0]) // Open Discord form

    await user.type(screen.getByPlaceholderText('Your Discord bot token'), 'my-bot-token')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(mockApi.credentials.save).toHaveBeenCalledWith('discord', {
      token: 'my-bot-token',
    })
  })

  it('calls api.credentials.delete on disconnect', async () => {
    const user = userEvent.setup()
    mockApi.credentials.list.mockResolvedValue([
      { integration: 'slack', configured: true, updated_at: '2025-01-01' },
    ])
    mockApi.credentials.delete.mockResolvedValue(undefined as never)

    render(<IntegrationsPage />)

    // Wait for the Disconnect button to appear
    const disconnectBtn = await screen.findByRole('button', { name: 'Disconnect' })
    await user.click(disconnectBtn)

    expect(mockApi.credentials.delete).toHaveBeenCalledWith('slack')
  })
})
