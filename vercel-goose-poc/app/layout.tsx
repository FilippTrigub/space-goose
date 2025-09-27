import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Kubernetes Goose POC',
  description: 'Proof of concept for Goose API with Kubernetes isolation',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <div className="container mx-auto py-8 px-4 max-w-7xl">
          <header className="mb-8 bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  Kubernetes Goose POC
                </h1>
                <p className="text-gray-600 mt-2">
                  Manage isolated Goose API environments in Kubernetes
                </p>
              </div>
              <div className="text-right">
                <div className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                  ⚙️ K8s Environment
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Namespace prefix: {process.env.KUBE_NAMESPACE_PREFIX || 'user-'}
                </div>
              </div>
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  )
}
