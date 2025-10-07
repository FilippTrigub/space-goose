# Discord Bot Commands

This document provides an overview of all available Discord slash commands for managing K8s projects and AI chat sessions.

---

## 🔐 Authentication Commands

### `/register <user_id> <blackbox_api_key>`
Link your Discord account to a K8s Manager user account.

**Parameters:**
- `user_id`: Your K8s Manager user ID

**Example:**
```
/register user1 ***
```

### `/whoami`
Display your linked K8s Manager account information, including user ID, name, and API key status.

### `/unregister`
Unlink your Discord account from K8s Manager.

---

## 📦 Project Management Commands

### `/projects-list`
List all your projects with their status, endpoint, and session count.

### `/projects-create <name> [repo_url]`
Create a new project. The project will be automatically activated and ready to use.

**Parameters:**
- `name`: Name for the new project
- `repo_url` (optional): GitHub repository URL to clone

**Example:**
```
/projects-create my-project https://github.com/user/repo
```

**Note:** Project creation may take up to 120 seconds.

### `/projects-delete <project_name>`
Delete a project and all its associated resources.

**Parameters:**
- `project_name`: Name of the project to delete

### `/projects-activate <project_name>`
Activate an inactive project. This spins up the Kubernetes pod and makes the project ready for use.

**Parameters:**
- `project_name`: Name of the project to activate

**Note:** Activation may take up to 120 seconds.

### `/projects-deactivate <project_name>`
Deactivate an active project to save resources.

**Parameters:**
- `project_name`: Name of the project to deactivate

### `/projects-info <project_name>`
Get detailed information about a project, including status, endpoint, repository, sessions, and timestamps.

**Parameters:**
- `project_name`: Name of the project

---

## 💬 Session Management Commands

### `/sessions-list <project_name>`
List all chat sessions in a project.

**Parameters:**
- `project_name`: Name of the project

**Note:** Project must be active.

### `/sessions-create <project_name> <session_name>`
Create a new chat session in a project.

**Parameters:**
- `project_name`: Name of the project
- `session_name`: Name for the new session

**Example:**
```
/sessions-create my-project debug-session
```

### `/sessions-delete <project_name> <session_name>`
Delete a chat session from a project.

**Parameters:**
- `project_name`: Name of the project
- `session_name`: Name of the session to delete

---

## 🤖 AI Chat Commands

### `/ask <project_name> <message>`
Create a new session and send a message to the AI agent. The response will be streamed in real-time.

**Parameters:**
- `project_name`: Name of the project
- `message`: Your message to the AI

**Example:**
```
/ask my-project How do I fix this error?
```

**Features:**
- ✅ Auto-creates a new session with timestamp
- ✅ Real-time streaming response (updates every 3 seconds)
- ✅ Handles long responses (up to 1900 characters)
- ⚠️ If response exceeds 1900 chars, it will be truncated with a warning

### `/ask-session <project_name> <session_name> <message>`
Send a message to an existing chat session. The response will be streamed in real-time.

**Parameters:**
- `project_name`: Name of the project
- `session_name`: Name of the session
- `message`: Your message to the AI

**Example:**
```
/ask-session my-project debug-session What's the next step?
```

**Features:**
- ✅ Maintains conversation history
- ✅ Real-time streaming response (updates every 3 seconds)
- ✅ Handles long responses (up to 1900 characters)
- ⚠️ If response exceeds 1900 chars, it will be truncated with a warning

---

## 📝 Notes

### Response Limits
Discord messages have a 2000-character limit. When AI responses exceed 1900 characters, they will be truncated with the following message:

> ⚠️ **Response truncated** - Use session commands to view full content

To view the full conversation history, you can use the K8s Manager API or web interface directly.

### Project Activation
- Projects must be **active** before you can create sessions or send messages
- Use `/projects-activate` to activate an inactive project
- Activation typically takes 30-120 seconds

### Session Naming
- Sessions auto-created by `/ask` use timestamp format: `chat-YYYYMMDD-HHMMSS`
- Sessions created with `/sessions-create` can have custom names
- Session names must be unique within a project

### Streaming Behavior
- Responses are streamed in real-time
- Messages update every 3 seconds during streaming
- You'll see "_Thinking..._" while waiting for the first response chunk

---

## 🚀 Quick Start

1. **Register your account:**
   ```
   /register user1
   ```

2. **Create a project:**
   ```
   /projects-create my-first-project
   ```

3. **Start chatting:**
   ```
   /ask my-first-project Hello! Can you help me?
   ```

4. **Continue the conversation:**
   ```
   /ask-session my-first-project chat-20250107-143022 Tell me more
   ```
