# Quick Start Guide

Get your Discord bot up and running in 5 minutes!

## Prerequisites

- Python 3.10+
- Access to K8s Manager API
- MongoDB (same as K8s Manager)
- Discord account with permissions to add bots

## Step 1: Create Discord Bot

1. Go to https://discord.com/developers/applications
2. Click **"New Application"**
3. Name it (e.g., "K8s Manager Bot")
4. Go to **"Bot"** tab
5. Click **"Reset Token"** and copy the token (save it!)
6. Enable **"MESSAGE CONTENT INTENT"** under Privileged Gateway Intents
7. Go to **"OAuth2" → "URL Generator"**
8. Select scopes: **"bot"** and **"applications.commands"**
9. Select permissions:
   - Send Messages
   - Embed Links
   - Use Slash Commands
10. Copy the generated URL and open in browser
11. Select your Discord server and authorize

## Step 2: Install Bot

```bash
cd /home/filipp/space-goose/k8s-manager/discord

# Run setup script
./setup.sh

# OR manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 3: Configure

```bash
# Copy example config
cp .env.example .env

# Edit config and add your bot token
nano .env
```

Required settings in `.env`:
```env
DISCORD_BOT_TOKEN=your_bot_token_here
K8S_MANAGER_API_URL=http://localhost:8000
MONGO_URI=mongodb://localhost:27017
MONGO_DB=k8s_manager
```

## Step 4: Run Bot

```bash
# Activate venv (if not already active)
source venv/bin/activate

# Run bot
python bot.py
```

You should see:
```
INFO - Loaded cogs.auth_cog
INFO - Loaded cogs.project_cog
INFO - Loaded cogs.session_cog
INFO - Loaded cogs.messaging_cog
INFO - Synced 11 commands
INFO - Logged in as YourBotName#1234
INFO - Bot is ready!
```

## Step 5: Register in Discord

In your Discord server:

```
1. Type: /register user_123
   (replace user_123 with your K8s Manager user_id)

2. Check: /whoami
   (verify you're registered)

3. Create project: /projects-create my-first-project

4. Ask AI: /ask my-first-project "Hello!"
```

## Commands Overview

### Must do first
- `/register <user_id>` - Link your Discord to K8s Manager

### Common commands
- `/projects-list` - See all projects
- `/projects-create <name>` - Make new project
- `/ask <project> <message>` - Talk to AI (auto-creates session)
- `/sessions-list <project>` - See all sessions

### Full list
Run `/` in Discord to see all commands with descriptions!

## Troubleshooting

**Bot doesn't respond:**
- Check bot is online (green dot in Discord)
- Verify bot has permissions in channel
- Check logs for errors

**"Not registered" error:**
- Run `/register <your_user_id>` first
- Verify user_id exists in K8s Manager
- Check user has API key configured

**Commands not showing:**
- Wait 1-2 minutes for Discord to sync
- Try in a different channel
- Restart Discord client

**"Project inactive" error:**
- Run `/projects-activate <project_name>` first
- Wait up to 120 seconds for activation

## Production Deployment

### Using systemd

```bash
# Create service file
sudo nano /etc/systemd/system/k8s-discord-bot.service
```

```ini
[Unit]
Description=K8s Manager Discord Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/filipp/space-goose/k8s-manager/discord
Environment="PATH=/home/filipp/space-goose/k8s-manager/discord/venv/bin"
ExecStart=/home/filipp/space-goose/k8s-manager/discord/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable k8s-discord-bot
sudo systemctl start k8s-discord-bot

# Check status
sudo systemctl status k8s-discord-bot

# View logs
sudo journalctl -u k8s-discord-bot -f
```

## Need Help?

- Check logs: Look at console output for errors
- Verify API: Ensure K8s Manager API is running
- MongoDB: Confirm MongoDB connection works
- Discord: Check bot has correct permissions

## Next Steps

- Read full [README.md](README.md) for detailed documentation
- See [implementation plan](../../docs/discord-bot-implementation-plan.md)
- Check [MVP summary](../../docs/discord-bot-mvp-summary.md)

Enjoy your Discord bot! 🤖
