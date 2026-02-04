import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_WREN_API_URL || 'http://localhost:8000'

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession()

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(session && { Authorization: `Bearer ${session.access_token}` }),
      ...options?.headers,
    },
  })

  if (!res.ok) {
    throw new Error(await res.text())
  }

  return res.json()
}

// API endpoints
export const api = {
  deployments: {
    list: () => apiFetch<Deployment[]>('/v1/deployments'),
    get: (id: string) => apiFetch<Deployment>(`/v1/deployments/${id}`),
  },
  runs: {
    list: (deploymentId: string) => apiFetch<Run[]>(`/v1/deployments/${deploymentId}/runs`),
    get: (id: string) => apiFetch<Run>(`/v1/runs/${id}`),
  },
}

// Types - extend as needed
export interface Deployment {
  id: string
  name: string
  status: 'active' | 'paused' | 'error' | 'deleted'
  script_content: string
  triggers: unknown[]
  integrations: string[]
  created_at: string
  updated_at: string
}

export interface Run {
  id: string
  deployment_id: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'timeout' | 'cancelled'
  trigger_type: string
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  stdout: string | null
  stderr: string | null
}
