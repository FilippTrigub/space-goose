# Discord Bot MVP - Quick Reference

## Overview

Simple Discord bot for K8s Manager API. No changes to existing API implementation.

## Key Features

- Link Discord users to K8s Manager users
- Manage projects (create, list, activate, deactivate, delete)
- Manage sessions (create, list, delete)
- Send messages to AI agent (fire-and-forget only)

## Commands

### Auth
- `/register <user_id>` - Link Discord to K8s user
- `/whoami` - Show linked user
- `/unregister` - Unlink account

### Projects
- `/projects-list`
- `/projects-create <name> [repo_url]`
- `/projects-delete <project_name>`
- `/projects-activate <project_name>` (120s wait)
- `/projects-deactivate <project_name>`
- `/projects-info <project_name>`

### Sessions
- `/sessions-list <project_name>`
- `/sessions-create <project_name> <session_name>`
- `/sessions-delete <project_name> <session_name>`

### Messaging
- `/ask <project_name> <message>` - Creates NEW session
- `/ask-session <project_name> <session_name> <message>` - Sends to EXISTING session

## Architecture

```
discord-bot/
├── bot.py                 # Main entry
├── config.py              # Environment config
├── cogs/
│   ├── auth_cog.py       # Auth commands
│   ├── project_cog.py    # Project commands
│   ├── session_cog.py    # Session commands
│   └── messaging_cog.py  # Ask commands
├── services/
│   ├── api_client.py     # K8s Manager API wrapper
│   └── mongodb_client.py # MongoDB queries
└── utils/
    ├── embeds.py         # Discord formatting
    └── helpers.py        # Split messages, etc.
```

## Tech Stack

- Python 3.10+
- discord.py
- aiohttp
- pymongo
- python-dotenv

## Environment Variables

```env
DISCORD_BOT_TOKEN=your_token
K8S_MANAGER_API_URL=http://localhost:8000
MONGO_URI=mongodb://localhost:27017
MONGO_DB=k8s_manager
```

## MongoDB Changes

Add `discord_user_id` field to existing users collection:

```javascript
{
  "user_id": "user_123",
  "name": "John Doe",
  "blackbox_api_key_plaintext": "sk-...",
  "discord_user_id": "123456789"  // NEW
}
```

## Implementation Phases

1. **Phase 1** (2 days): Core infrastructure (API client, MongoDB client)
2. **Phase 2** (1 day): Authentication (register, whoami, unregister)
3. **Phase 3** (2 days): Project management (all project commands)
4. **Phase 4** (1 day): Session management (all session commands)
5. **Phase 5** (2 days): Messaging (ask, ask-session)
6. **Phase 6** (1 day): Error handling & testing

**Total: ~9 days**

## Key Design Decisions

✅ **Stateless** - User specifies project/session in every command
✅ **Fire-and-forget** - No streaming support (uses /messages/send endpoint)
✅ **Reuse MongoDB** - No separate database for bot
✅ **Simple** - No autocomplete, buttons, or pagination

❌ **No changes to API** - Bot is just a client
❌ **No context management** - Keeps implementation simple
❌ **No encryption** - API keys already in MongoDB plaintext (existing design)

## Testing Checklist

- [ ] Register user
- [ ] Create/activate/deactivate/delete project
- [ ] Create/list/delete sessions
- [ ] Send message with `/ask` (new session)
- [ ] Send message with `/ask-session` (existing)
- [ ] Test long responses (>2000 chars)
- [ ] Test error cases (invalid names, not registered, etc.)

## Security

- Users provide `user_id`, not API key (no sensitive data in Discord)
- API keys stay in MongoDB (existing storage)
- Ephemeral messages for auth commands
- Bot token in environment variable

## Example Workflow

```
1. /register user_123
   → ✅ Linked to user 'user_123' (John Doe)

2. /projects-create my-project
   → ✅ Project 'my-project' created!

3. /ask my-project "hello"
   → 🤖 Session: chat-20251006-143022
   → I'm Goose, an AI assistant...

4. /ask-session my-project chat-20251006-143022 "what can you do?"
   → 🤖 Session: chat-20251006-143022
   → I can help you with coding tasks...
```

## Next Steps

1. Create Discord bot at https://discord.com/developers/applications
2. Set up Python project with venv
3. Install dependencies
4. Implement Phase 1
5. Test and iterate
