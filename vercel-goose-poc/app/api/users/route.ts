import { NextRequest, NextResponse } from 'next/server'
import { connectDB } from '@/lib/db'
import { User } from '@/lib/models'

// Static users for POC
const STATIC_USERS = [
  { _id: 'user1', name: 'Alice Johnson', email: 'alice@example.com' },
  { _id: 'user2', name: 'Bob Smith', email: 'bob@example.com' },
  { _id: 'user3', name: 'Carol Davis', email: 'carol@example.com' }
]

export async function GET() {
  try {
    await connectDB()
    
    // For POC, we'll seed the static users if they don't exist
    for (const userData of STATIC_USERS) {
      await User.findByIdAndUpdate(
        userData._id,
        userData,
        { upsert: true, new: true }
      )
    }
    
    const users = await User.find({}).sort({ name: 1 })
    
    return NextResponse.json({ users })
  } catch (error) {
    console.error('Error fetching users:', error)
    return NextResponse.json(
      { error: 'Failed to fetch users' },
      { status: 500 }
    )
  }
}
