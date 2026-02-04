import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_authenticated/integrations')({
  component: IntegrationsPage,
})

function IntegrationsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Integrations</h1>
      <p className="text-gray-600">Connect your services here.</p>
    </div>
  )
}
