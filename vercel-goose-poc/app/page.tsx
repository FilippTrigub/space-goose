'use client'

import { useState, useEffect } from 'react'
import UserSelector from '@/components/UserSelector'
import ProjectList from '@/components/ProjectList'
import { IUser } from '@/lib/models'

export default function Home() {
  const [users, setUsers] = useState<IUser[]>([])
  const [selectedUserId, setSelectedUserId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/users')
      if (!response.ok) throw new Error('Failed to fetch users')
      const data = await response.json()
      setUsers(data.users)
      if (data.users.length > 0) {
        setSelectedUserId(data.users[0]._id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-lg text-gray-600">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="text-red-800">
          <strong>Error:</strong> {error}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <UserSelector
        users={users}
        selectedUserId={selectedUserId}
        onSelectUser={setSelectedUserId}
      />
      
      {selectedUserId && (
        <ProjectList userId={selectedUserId} />
      )}
    </div>
  )
}
