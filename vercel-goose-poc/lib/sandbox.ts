import { Sandbox } from '@vercel/sandbox'
import ms from 'ms'

export interface SandboxConfig {
  projectId: string
  projectName: string
}

export interface SandboxResult {
  sandbox: Sandbox
  domain: string
  logs: string[]
}

export class SandboxManager {
  async createProjectSandbox(config: SandboxConfig): Promise<SandboxResult> {
    const logs: string[] = []
    
    try {
      logs.push('Creating Vercel sandbox...')
      logs.push(`Project: ${config.projectName}`)

      // Create sandbox configuration
      const sandboxConfig = {
        teamId: process.env.VERCEL_TEAM_ID!,
        projectId: process.env.VERCEL_PROJECT_ID!,
        token: process.env.VERCEL_TOKEN!,
        
        // For POC, we'll create a simple Node.js server instead of cloning a repo
        // This is simpler and faster for demonstration
        timeout: ms('30m'), // 30 minutes
        ports: [3001],
        runtime: 'node22' as const,
        resources: { vcpus: 2 }
      }

      logs.push('Creating sandbox instance...')
      const sandbox = await Sandbox.create(sandboxConfig)
      logs.push('Sandbox created successfully')

      // Install Node.js and create a simple Goose-like API server
      await this.setupSimpleGooseApi(sandbox, logs)
      
      const domain = sandbox.domain(3001)
      logs.push(`Sandbox available at: ${domain}`)

      return {
        sandbox,
        domain,
        logs
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      logs.push(`Error: ${errorMessage}`)
      throw new Error(`Failed to create sandbox: ${errorMessage}`)
    }
  }

  private async setupSimpleGooseApi(sandbox: Sandbox, logs: string[]) {
    logs.push('Setting up Goose API server...')
    
    // Install Express
    logs.push('Installing Express...')
    const installResult = await sandbox.runCommand({
      cmd: 'npm',
      args: ['install', 'express', 'cors']
    })
    
    if (installResult.exitCode !== 0) {
      throw new Error('Failed to install Node.js dependencies')
    }
    
    // Create a simple server that mimics Goose API
    const serverScript = `
const express = require('express')
const cors = require('cors')
const app = express()
const port = 3001

app.use(cors())
app.use(express.json())

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() })
})

// Simple messages endpoint that mimics Goose API
app.post('/api/v1/sessions/messages', (req, res) => {
  const { message } = req.body
  
  // Simple echo response for POC
  const response = {
    id: Date.now().toString(),
    message: message,
    response: \`I received your message: "\${message}". This is a POC response from the Vercel Sandbox!\`,
    timestamp: new Date().toISOString(),
    sandbox_info: {
      runtime: 'node22',
      domain: req.get('host')
    }
  }
  
  res.json(response)
})

// List sessions endpoint
app.get('/api/v1/sessions', (req, res) => {
  res.json({
    sessions: [
      {
        id: 'poc-session-1',
        name: 'POC Session',
        created_at: new Date().toISOString()
      }
    ]
  })
})

app.listen(port, '0.0.0.0', () => {
  console.log(\`Goose API POC server listening on port \${port}\`)
})
`

    // Write the server file
    logs.push('Creating server script...')
    await sandbox.writeFiles([{
      path: 'server.js',
      content: Buffer.from(serverScript)
    }])
    
    // Start the server in the background
    logs.push('Starting Goose API server...')
    await sandbox.runCommand({
      cmd: 'node',
      args: ['server.js'],
      detached: true
    })
    
    // Wait a bit for the server to start
    await new Promise(resolve => setTimeout(resolve, 3000))
    logs.push('Goose API server started successfully')
  }

  async stopSandbox(sandbox: Sandbox): Promise<void> {
    try {
      await sandbox.stop()
    } catch (error) {
      console.error('Error stopping sandbox:', error)
    }
  }
}
