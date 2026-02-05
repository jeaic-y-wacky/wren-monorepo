import { createFileRoute, redirect, Outlet, Link, useNavigate } from '@tanstack/react-router'
import { supabase } from '@/lib/supabase'

export const Route = createFileRoute('/_authenticated')({
  beforeLoad: async () => {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      throw redirect({ to: '/login' })
    }
    return { session }
  },
  component: AuthenticatedLayout,
})

function AuthenticatedLayout() {
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    navigate({ to: '/login' })
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white p-4">
        <h1 className="text-xl font-bold mb-8">Wren</h1>
        <nav className="space-y-2">
          <Link to="/" className="block px-3 py-2 rounded hover:bg-gray-800">
            Dashboard
          </Link>
          <Link to="/deployments" className="block px-3 py-2 rounded hover:bg-gray-800">
            Deployments
          </Link>
          <Link to="/integrations" className="block px-3 py-2 rounded hover:bg-gray-800">
            Integrations
          </Link>
        </nav>
        <button
          onClick={handleSignOut}
          className="mt-8 w-full px-3 py-2 text-left text-gray-400 hover:text-white"
        >
          Sign out
        </button>
      </aside>

      {/* Main content */}
      <main className="flex-1 p-8 bg-gray-50">
        <Outlet />
      </main>
    </div>
  )
}
