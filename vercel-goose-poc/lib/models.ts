import mongoose from 'mongoose'

// Project Schema for Kubernetes
const ProjectSchema = new mongoose.Schema({
  _id: { type: String, required: true }, // UUID
  user_id: { type: String, required: true, index: true },
  project_id: { type: String, required: true, index: true },
  name: { type: String, required: true },
  description: { type: String, default: '' },
  
  // Kubernetes resources
  namespace: { type: String, required: true },
  deployment: String,
  service: String,
  ingress: String,
  
  // Status and endpoint
  status: { 
    type: String, 
    enum: ['inactive', 'activating', 'active', 'deactivating', 'error'],
    default: 'inactive'
  },
  endpoint: String, // HTTP endpoint when active
  error_message: String,
  
  // Timestamps
  last_activated_at: Date,
  last_deactivated_at: Date,
  created_at: { type: Date, default: Date.now },
  updated_at: { type: Date, default: Date.now }
}, {
  timestamps: true,
  collection: 'projects'
})

// Indexes
ProjectSchema.index({ user_id: 1, project_id: 1 }, { unique: true })
ProjectSchema.index({ status: 1 }) // For filtering

// User Schema (static for POC)
const UserSchema = new mongoose.Schema({
  _id: { type: String, required: true },
  name: { type: String, required: true },
  email: { type: String, required: true },
  created_at: { type: Date, default: Date.now }
}, {
  collection: 'users'
})

// Export models
export const Project = mongoose.models.Project || mongoose.model('Project', ProjectSchema)
export const User = mongoose.models.User || mongoose.model('User', UserSchema)

// Types
export interface IProject {
  _id: string
  user_id: string
  project_id: string
  name: string
  description: string
  namespace: string
  deployment?: string
  service?: string
  ingress?: string
  status: 'inactive' | 'activating' | 'active' | 'deactivating' | 'error'
  endpoint?: string
  error_message?: string
  last_activated_at?: Date
  last_deactivated_at?: Date
  created_at: Date
  updated_at: Date
}

export interface IUser {
  _id: string
  name: string
  email: string
  created_at: Date
}
