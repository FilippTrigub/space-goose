# Discord Bot Implementation Plan for K8s Manager API (MVP)

## Project Overview

Build a Discord bot that integrates with the K8s Manager API, allowing users to manage projects, sessions, and interact with the Goose AI agent directly from Discord.

**This is an MVP** - Keep it simple, no changes to existing API implementation.

---

## Critical Issues & Solutions

### 🔴 API Key Management (SOLVED)

**Solution**: Reuse existing MongoDB users collection
- API keys already stored as `blackbox_api_key_plaintext` in MongoDB
- Add `discord_user_id` field to existing users collection
- Discord bot queries MongoDB to get API key for authenticated users
- **No duplicate storage, no encryption needed for MVP**

### 🔴 Authentication Flow (SIMPLIFIED)

- User provides their K8s Manager `user_id` (not API key)
- Bot links Discord user ID → K8s Manager user_id in MongoDB
- All commands fetch API key from MongoDB via Discord ID
- **No DM-required, no sensitive data in Discord**

### 🔴 Response Handling (FIRE-AND-FORGET ONLY)

- Use `/projects/{project_id}/messages/send` endpoint (non-streaming)
- Activation can take up to **120 seconds** - use defer pattern
- Split responses > 2000 characters across multiple Discord messages
- **No streaming support in MVP**

### 🔴 Session Management (EXPLICIT)

- `/ask` - Creates NEW session and sends message
- `/ask-session <session_name>` - Sends to EXISTING session
- User must specify session explicitly (no context needed)
- **Simple, stateless approach**

---

## Architecture (Simplified for MVP)

### Technology Stack

- **Language**: Python 3.10+
- **Discord Library**: discord.py (v2.x)
- **HTTP Client**: aiohttp (async)
- **Database**: MongoDB (existing - reuse users collection)
- **Environment**: Docker container or systemd service

### Component Structure

```
discord-bot/
├── bot.py                 # Main bot entry point
├── config.py              # Configuration (bot token, MongoDB URI, API URL)
├── cogs/
│   ├── auth_cog.py       # /register, /whoami, /unregister
│   ├── project_cog.py    # /projects commands
│   ├── session_cog.py    # /sessions commands
│   └── messaging_cog.py  # /ask, /ask-session
├── services/
│   ├── api_client.py     # K8s Manager API wrapper (aiohttp)
│   └── mongodb_client.py # MongoDB queries (get user by discord_id)
├── utils/
│   ├── embeds.py         # Discord embed formatters
│   └── helpers.py        # Split long messages, format responses
├── requirements.txt
├── .env.example
└── README.md
```

**Removed from MVP:**
- ❌ key_store.py (use MongoDB directly)
- ❌ context_manager.py (stateless design)
- ❌ admin_cog.py (not needed for MVP)
- ❌ models/ (simple dict-based data handling)
- ❌ validators.py (basic validation inline)

---

## Detailed Implementation Plan

### Phase 1: Core Infrastructure (Simplified)

#### 1.1 Project Setup
- [ ] Create Discord bot application on Discord Developer Portal
- [ ] Set up Python project with virtual environment
- [ ] Install dependencies: `discord.py`, `aiohttp`, `pymongo`, `python-dotenv`
- [ ] Create `.env` file with bot token, MongoDB URI, API URL
- [ ] Set up basic bot skeleton with command tree

#### 1.2 MongoDB Client (Reuse Existing DB)
- [ ] Create `mongodb_client.py` with connection to existing MongoDB
- [ ] Implement helper functions:
  - `get_user_by_discord_id(discord_user_id)` → Get user + API key
  - `link_discord_user(user_id, discord_user_id)` → Add discord_user_id field
  - `unlink_discord_user(discord_user_id)` → Remove discord_user_id field
  - `get_user_info(user_id)` → Validate user exists
- [ ] **NO CHANGES to existing MongoDB schema or API code**

#### 1.3 API Client (Fire-and-Forget Only)
- [ ] Create `K8sManagerClient` class with aiohttp
- [ ] Implement methods for required endpoints:
  - `get_projects(api_key)` → GET `/projects`
  - `create_project(api_key, name, repo_url=None)` → POST `/projects`
  - `delete_project(api_key, project_id)` → DELETE `/projects/{project_id}`
  - `activate_project(api_key, project_id)` → POST `/projects/{project_id}/activate`
  - `deactivate_project(api_key, project_id)` → POST `/projects/{project_id}/deactivate`
  - `get_sessions(api_key, project_id)` → GET `/projects/{project_id}/sessions`
  - `create_session(api_key, project_id, name)` → POST `/projects/{project_id}/sessions`
  - `delete_session(api_key, project_id, session_id)` → DELETE `/projects/{project_id}/sessions/{session_id}`
  - `send_message_sync(api_key, project_id, session_id, content)` → POST `/projects/{project_id}/messages/send`
- [ ] Add error handling for HTTP status codes (401, 404, 400, 500)
- [ ] Set timeout to 150 seconds (activation takes up to 120s)
- [ ] **NO streaming endpoint, NO retry logic for MVP**

---

### Phase 2: Authentication (Simplified)

#### 2.1 User Registration (Auth Cog)

**Commands:**
- `/register <user_id>` - Link Discord account to K8s Manager user
- `/whoami` - Show your linked user info
- `/unregister` - Unlink your Discord account

**Implementation:**

```python
@app_commands.command(name="register")
async def register(interaction: discord.Interaction, user_id: str):
    """Link your Discord account to K8s Manager user"""

    # Check if user exists in MongoDB
    user = mongodb_client.get_user_info(user_id)
    if not user:
        await interaction.response.send_message(
            f"❌ User '{user_id}' not found. Contact admin.",
            ephemeral=True
        )
        return

    # Check if already registered
    existing = mongodb_client.get_user_by_discord_id(str(interaction.user.id))
    if existing:
        await interaction.response.send_message(
            f"❌ Already registered as '{existing['user_id']}'",
            ephemeral=True
        )
        return

    # Check if user has API key
    if not user.get('blackbox_api_key_plaintext'):
        await interaction.response.send_message(
            f"❌ User '{user_id}' has no API key configured.",
            ephemeral=True
        )
        return

    # Link Discord ID to user
    mongodb_client.link_discord_user(user_id, str(interaction.user.id))

    await interaction.response.send_message(
        f"✅ Linked to user '{user_id}' ({user['name']})",
        ephemeral=True
    )
```

**Security Notes:**
- Users provide user_id (not API key) - no sensitive data in Discord
- API keys stay in MongoDB (already trusted storage)
- Ephemeral messages (only visible to user)

---

### Phase 3: Project Management (Simplified)

#### 3.1 Project CRUD (Project Cog)

**Commands:**
- `/projects-list` - List all your projects
- `/projects-create <name> [repo_url]` - Create a new project
- `/projects-delete <project_name>` - Delete a project
- `/projects-activate <project_name>` - Activate a project (takes up to 120s)
- `/projects-deactivate <project_name>` - Deactivate a project
- `/projects-info <project_name>` - Get project details

**Implementation Notes:**
- User specifies project by name in every command (stateless)
- Map project name to project_id by listing projects first
- Defer response for activate (shows "Bot is thinking...")
- Use embeds for rich project information display
- **No context management, no autocomplete for MVP**

---

### Phase 4: Session Management (Simplified)

#### 4.1 Session CRUD (Session Cog)

**Commands:**
- `/sessions-list <project_name>` - List sessions in project
- `/sessions-create <project_name> <session_name>` - Create new session
- `/sessions-delete <project_name> <session_name>` - Delete session

**Implementation Notes:**
- User always specifies project and session names (stateless)
- Map names to IDs by querying API first
- **No session history for MVP** (complex pagination)
- **No context/selection for MVP**

---

### Phase 5: Messaging (Fire-and-Forget Only)

#### 5.1 Message Sending (Messaging Cog)

**Commands:**
- `/ask <project_name> <message>` - Create NEW session and send message
- `/ask-session <project_name> <session_name> <message>` - Send to EXISTING session

**Implementation:**

```python
@app_commands.command(name="ask")
async def ask(interaction: discord.Interaction, project_name: str, message: str):
    """Create new session and send message"""

    await interaction.response.defer()

    # Get user API key
    user = mongodb_client.get_user_by_discord_id(str(interaction.user.id))
    api_key = user['blackbox_api_key_plaintext']

    # Find project by name
    projects = await api_client.get_projects(api_key)
    project = next((p for p in projects if p['name'] == project_name), None)

    if not project:
        await interaction.followup.send(f"❌ Project '{project_name}' not found")
        return

    project_id = project['id']

    # Create new session
    session_name = f"chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    session = await api_client.create_session(api_key, project_id, session_name)
    session_id = session['session']['session_id']

    # Send message (fire-and-forget)
    result = await api_client.send_message_sync(
        api_key, project_id, session_id, message
    )

    # Format and send response
    response_text = result.get('result', {}).get('response', 'No response')

    # Split if > 2000 chars
    chunks = split_message(response_text)
    for chunk in chunks:
        await interaction.followup.send(f"🤖 **Session: {session_name}**\n{chunk}")


@app_commands.command(name="ask-session")
async def ask_session(interaction: discord.Interaction, project_name: str,
                      session_name: str, message: str):
    """Send message to existing session"""

    await interaction.response.defer()

    # Get user, project, session (similar to above)
    # Send message to specific session_id
    # Format and return response
```

**Response Handling:**
- Split responses > 2000 characters into multiple messages
- Format code blocks properly
- Show session name in response
- **No streaming for MVP**

---

### Phase 6: Error Handling & Polish (MVP)

#### 6.1 Error Handling Strategy

**Error Types & Responses:**

| Error | User Message |
|-------|--------------|
| Not registered | "❌ Not registered. Use `/register <user_id>`" |
| No API key | "❌ Your user has no API key configured" |
| Project not found | "❌ Project '{name}' not found" |
| Session not found | "❌ Session '{name}' not found" |
| Project not active | "❌ Project is inactive. Use `/projects-activate`" |
| API timeout | "⏱️ Request timed out (>150s)" |
| API error (500) | "❌ API error: {detail}" |
| API error (401) | "❌ Authentication failed (invalid API key)" |

#### 6.2 User Experience (Simple)

- **Embeds**: For project/session lists and info
- **Emojis**: Status indicators (✅ ❌ ⏱️ 📂 💬 🤖)
- **Colors**: Green for success, red for errors, blue for info
- **Ephemeral**: Auth commands only visible to user
- **Defer**: Long operations show "thinking..." state

**No MVP Features:**
- ❌ Autocomplete
- ❌ Buttons/pagination
- ❌ Progress updates

#### 6.3 Logging (Basic)

- Log command usage (command name, user ID, timestamp)
- Log errors with stack traces
- **No analytics or monitoring for MVP**

---

## Command Reference Summary (MVP)

### Authentication Commands
| Command | Description |
|---------|-------------|
| `/register <user_id>` | Link Discord to K8s Manager user |
| `/whoami` | Show your linked user info |
| `/unregister` | Unlink your Discord account |

### Project Commands
| Command | Description |
|---------|-------------|
| `/projects-list` | List all your projects |
| `/projects-create <name> [repo_url]` | Create project |
| `/projects-delete <project_name>` | Delete project |
| `/projects-activate <project_name>` | Activate project (120s wait) |
| `/projects-deactivate <project_name>` | Deactivate project |
| `/projects-info <project_name>` | Get project details |

### Session Commands
| Command | Description |
|---------|-------------|
| `/sessions-list <project_name>` | List sessions in project |
| `/sessions-create <project_name> <session_name>` | Create session |
| `/sessions-delete <project_name> <session_name>` | Delete session |

### Messaging Commands
| Command | Description |
|---------|-------------|
| `/ask <project_name> <message>` | Create new session and send message |
| `/ask-session <project_name> <session_name> <message>` | Send to existing session |

---

## Data Flow Examples (MVP)

### Example 1: New User Workflow

```
1. User: /register user_123
   Bot: "✅ Linked to user 'user_123' (John Doe)"

2. User: /projects-list
   Bot: "📂 No projects found"

3. User: /projects-create my-project
   Bot: (shows "Bot is thinking...")
   ... (waits up to 120s for pod readiness)
   Bot: "✅ Project 'my-project' created and activated!"

4. User: /ask my-project "Hello, who are you?"
   Bot: (shows "Bot is thinking...")
   Bot: "🤖 **Session: chat-20251006-143022**
        I'm Goose, an AI coding assistant..."

5. User: /ask-session my-project chat-20251006-143022 "What can you do?"
   Bot: (shows "Bot is thinking...")
   Bot: "🤖 **Session: chat-20251006-143022**
        I can help you with coding tasks..."
```

### Example 2: Reusing Existing Session

```
1. User: /sessions-list my-project
   Bot: "💬 Sessions in 'my-project':
        - chat-20251006-143022 (3 messages)
        - debug-session (1 message)"

2. User: /ask-session my-project debug-session "Check the logs"
   Bot: (shows "Bot is thinking...")
   Bot: "🤖 **Session: debug-session**
        I'll check the logs for you..."
```

---

## Security Checklist (MVP)

- [ ] API keys stay in MongoDB (existing storage)
- [x] No API keys in Discord messages (users provide user_id only)
- [ ] Use environment variables for bot token
- [ ] Never log API keys
- [ ] Use HTTPS for all API calls to K8s Manager API
- [ ] Validate user inputs (project names, session names)
- [ ] Ephemeral messages for auth commands
- [ ] Log errors without exposing sensitive data

**Acceptable for MVP:**
- API keys in MongoDB plaintext (existing design)
- No encryption at rest (MongoDB access control sufficient)
- No rate limiting (trust Discord's built-in limits)
- No admin commands (out of scope)

---

## Deployment Considerations

### Environment Variables Required

```env
# Discord Bot
DISCORD_BOT_TOKEN=your_bot_token_here

# K8s Manager API
K8S_MANAGER_API_URL=http://your-api-url:8000

# MongoDB (same as K8s Manager)
MONGO_URI=mongodb://localhost:27017
MONGO_DB=k8s_manager

# Optional
LOG_LEVEL=INFO
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

### Systemd Service

```ini
[Unit]
Description=K8s Manager Discord Bot
After=network.target

[Service]
Type=simple
User=discordbot
WorkingDirectory=/opt/k8s-discord-bot
Environment="PATH=/opt/k8s-discord-bot/venv/bin"
ExecStart=/opt/k8s-discord-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Testing Strategy (MVP)

### Manual Testing Checklist
- [ ] Register Discord user with `/register user_id`
- [ ] Check `/whoami` shows correct user
- [ ] Create project with `/projects-create`
- [ ] List projects with `/projects-list`
- [ ] Activate project (verify 120s wait works)
- [ ] Create session with `/sessions-create`
- [ ] Send message with `/ask` (creates new session)
- [ ] Send message with `/ask-session` (existing session)
- [ ] Test long responses (> 2000 chars split)
- [ ] Delete session, project
- [ ] Test error cases (invalid project name, not registered, etc.)
- [ ] Unregister with `/unregister`

**No automated tests for MVP**

---

## Performance Targets (MVP)

- **Command Response Time**: < 2 seconds (excluding API calls)
- **Project Activation**: Up to 120 seconds (K8s pod startup)
- **Message Send**: Depends on AI (30-120s typical)
- **List Operations**: < 2 seconds
- **Bot Uptime**: Best effort
- **Memory Usage**: < 100MB

---

## Future Enhancements (Post-MVP)

1. **Context Management**
   - Remember active project/session per user
   - Autocomplete for project/session names
   - `/ask <message>` without specifying project

2. **Advanced Features**
   - Session history with pagination
   - Streaming responses (real-time updates)
   - Message threading (Discord threads)
   - Progress updates during activation

3. **User Experience**
   - Buttons for project activation/deactivation
   - Interactive project/session selection menus
   - Better formatting for code responses

4. **Security**
   - Encrypt API keys at rest
   - Proper OAuth flow
   - API key rotation

---

## Estimated Timeline (MVP)

- **Phase 1**: Core Infrastructure - 2 days
- **Phase 2**: Authentication - 1 day
- **Phase 3**: Project Management - 2 days
- **Phase 4**: Session Management - 1 day
- **Phase 5**: Messaging - 2 days
- **Phase 6**: Error Handling & Testing - 1 day

**Total**: ~9 days for MVP implementation

---

## MongoDB Schema Changes Required

**Add to existing users collection:**

```javascript
{
  "user_id": "user_123",                      // Existing
  "name": "John Doe",                         // Existing
  "blackbox_api_key_plaintext": "sk-...",    // Existing
  "blackbox_api_key_masked": "sk-12345***",  // Existing
  "blackbox_api_key_set": true,              // Existing
  "created_at": ISODate("..."),              // Existing
  "updated_at": ISODate("..."),              // Existing
  "discord_user_id": "123456789"             // NEW - Add this field
}
```

**No schema changes to projects collection needed.**

---

## Key Decisions for MVP

✅ **Reuse MongoDB** - No separate database for Discord bot
✅ **Stateless** - No context management, user specifies everything
✅ **Fire-and-forget only** - No streaming support
✅ **Simple commands** - Explicit project/session names
✅ **Basic embeds** - No buttons, autocomplete, or pagination
✅ **Manual testing** - No automated tests

❌ **No encryption** - API keys stay plaintext in MongoDB
❌ **No DM requirement** - Users provide user_id, not API key
❌ **No rate limiting** - Trust Discord's built-in limits
❌ **No admin commands** - Out of scope

---

## Conclusion (MVP)

This simplified plan provides a working Discord bot integration for the K8s Manager API without changing any existing implementation. The bot acts as a simple client that:
1. Links Discord users to K8s Manager users
2. Provides slash commands for all API operations
3. Handles long-running operations with Discord's defer pattern
4. Splits long responses across multiple messages

**No changes required to:**
- K8s Manager API
- MongoDB schema (only adds one optional field)
- Existing authentication system
- Any API endpoints

**Next Steps:**
1. Create Discord bot application
2. Set up Python project with dependencies
3. Implement Phase 1 (infrastructure)
4. Test with real K8s Manager API
5. Deploy and iterate
