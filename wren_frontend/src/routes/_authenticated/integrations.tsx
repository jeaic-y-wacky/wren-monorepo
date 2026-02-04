import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type Credential } from '@/lib/api'

export const Route = createFileRoute('/_authenticated/integrations')({
  component: IntegrationsPage,
})

// Integration definitions
const INTEGRATIONS = [
  {
    id: 'discord',
    name: 'Discord',
    description: 'Send messages to Discord channels',
    icon: '💬',
    fields: [
      { key: 'token', label: 'Bot Token', type: 'password', required: true, placeholder: 'Your Discord bot token' },
      { key: 'default_channel_id', label: 'Default Channel ID', type: 'text', required: false, placeholder: 'Optional channel ID' },
      { key: 'default_guild_id', label: 'Default Guild ID', type: 'text', required: false, placeholder: 'Optional server ID' },
    ],
  },
  {
    id: 'slack',
    name: 'Slack',
    description: 'Send messages to Slack workspaces',
    icon: '📱',
    fields: [
      { key: 'token', label: 'Bot Token', type: 'password', required: true, placeholder: 'xoxb-...' },
      { key: 'default_channel', label: 'Default Channel', type: 'text', required: false, placeholder: '#general' },
    ],
  },
  {
    id: 'gmail',
    name: 'Gmail',
    description: 'Read and send emails',
    icon: '📧',
    fields: [
      { key: 'client_id', label: 'Client ID', type: 'text', required: true, placeholder: 'OAuth client ID' },
      { key: 'client_secret', label: 'Client Secret', type: 'password', required: true, placeholder: 'OAuth client secret' },
      { key: 'refresh_token', label: 'Refresh Token', type: 'password', required: true, placeholder: 'OAuth refresh token' },
    ],
  },
] as const

type IntegrationId = typeof INTEGRATIONS[number]['id']

function IntegrationsPage() {
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<IntegrationId | null>(null)
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load existing credentials
  useEffect(() => {
    loadCredentials()
  }, [])

  const loadCredentials = async () => {
    try {
      const creds = await api.credentials.list()
      setCredentials(creds)
    } catch (e) {
      console.error('Failed to load credentials:', e)
    } finally {
      setLoading(false)
    }
  }

  const isConnected = (integrationId: string) => {
    return credentials.some(c => c.integration === integrationId)
  }

  const handleConnect = (integrationId: IntegrationId) => {
    setEditing(integrationId)
    setFormData({})
    setError(null)
  }

  const handleCancel = () => {
    setEditing(null)
    setFormData({})
    setError(null)
  }

  const handleSave = async () => {
    if (!editing) return

    const integration = INTEGRATIONS.find(i => i.id === editing)
    if (!integration) return

    // Validate required fields
    for (const field of integration.fields) {
      if (field.required && !formData[field.key]) {
        setError(`${field.label} is required`)
        return
      }
    }

    setSaving(true)
    setError(null)

    try {
      await api.credentials.save(editing, formData)
      await loadCredentials()
      setEditing(null)
      setFormData({})
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save credentials')
    } finally {
      setSaving(false)
    }
  }

  const handleDisconnect = async (integrationId: string) => {
    if (!confirm('Are you sure you want to disconnect this integration?')) return

    try {
      await api.credentials.delete(integrationId)
      await loadCredentials()
    } catch (e) {
      console.error('Failed to delete credentials:', e)
    }
  }

  if (loading) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">Integrations</h1>
        <p className="text-gray-500">Loading...</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Integrations</h1>
      <p className="text-gray-600 mb-8">Connect your services to use them in Wren scripts.</p>

      <div className="grid gap-4 max-w-2xl">
        {INTEGRATIONS.map((integration) => {
          const connected = isConnected(integration.id)
          const isEditing = editing === integration.id

          return (
            <div
              key={integration.id}
              className="border rounded-lg p-4 bg-white"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{integration.icon}</span>
                  <div>
                    <h3 className="font-semibold">{integration.name}</h3>
                    <p className="text-sm text-gray-500">{integration.description}</p>
                  </div>
                </div>

                {!isEditing && (
                  <div className="flex items-center gap-2">
                    {connected ? (
                      <>
                        <span className="text-sm text-green-600 flex items-center gap-1">
                          <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                          Connected
                        </span>
                        <button
                          onClick={() => handleConnect(integration.id)}
                          className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDisconnect(integration.id)}
                          className="px-3 py-1 text-sm text-red-600 border border-red-200 rounded hover:bg-red-50"
                        >
                          Disconnect
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => handleConnect(integration.id)}
                        className="px-4 py-1.5 text-sm bg-black text-white rounded hover:bg-gray-800"
                      >
                        Connect
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Edit form */}
              {isEditing && (
                <div className="mt-4 pt-4 border-t">
                  <div className="space-y-3">
                    {integration.fields.map((field) => (
                      <div key={field.key}>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {field.label}
                          {field.required && <span className="text-red-500 ml-1">*</span>}
                        </label>
                        <input
                          type={field.type}
                          placeholder={field.placeholder}
                          value={formData[field.key] || ''}
                          onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                          className="w-full px-3 py-2 border rounded-md text-sm"
                        />
                      </div>
                    ))}
                  </div>

                  {error && (
                    <p className="mt-3 text-sm text-red-500">{error}</p>
                  )}

                  <div className="mt-4 flex gap-2">
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="px-4 py-2 text-sm bg-black text-white rounded hover:bg-gray-800 disabled:opacity-50"
                    >
                      {saving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={handleCancel}
                      className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
