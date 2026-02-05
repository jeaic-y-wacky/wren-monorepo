import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_authenticated/deployments')({
  component: DeploymentsPage,
})

function DeploymentsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Deployments</h1>
      <p className="text-gray-600">Your deployments will appear here.</p>
    </div>
  )
}
