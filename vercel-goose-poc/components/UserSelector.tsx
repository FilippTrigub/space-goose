'use client'

import { IUser } from '@/lib/models'

interface UserSelectorProps {
  users: IUser[]
  selectedUserId: string
  onSelectUser: (userId: string) => void
}

export default function UserSelector({ users, selectedUserId, onSelectUser }: UserSelectorProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Select User</h2>
      <div className="space-y-2">
        {users.map((user) => (
          <label key={user._id} className="flex items-center space-x-3 cursor-pointer">
            <input
              type="radio"
              name="user"
              value={user._id}
              checked={selectedUserId === user._id}
              onChange={(e) => onSelectUser(e.target.value)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
            />
            <div>
              <div className="text-sm font-medium text-gray-900">{user.name}</div>
              <div className="text-sm text-gray-500">{user.email}</div>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}
