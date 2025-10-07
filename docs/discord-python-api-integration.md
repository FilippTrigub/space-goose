# Discord Python API Integration Guide

## Overview

This document covers how to build Discord integrations for APIs using Python, including both Discord bots and webhooks.

## Table of Contents

1. [Discord Bot with discord.py](#discord-bot-with-discordpy)
2. [Webhooks](#webhooks)
3. [Best Practices](#best-practices)
4. [Code Examples](#code-examples)

---

## Discord Bot with discord.py

### Setup & Installation

1. **Install discord.py**
   ```bash
   python3 -m pip install -U discord.py
   ```

2. **Create Bot Application**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application"
   - Navigate to "Bot" tab
   - Click "Reset Token" and copy the bot token (keep this secret!)
   - Enable required Privileged Gateway Intents:
     - PRESENCE INTENT
     - SERVER MEMBERS INTENT
     - MESSAGE CONTENT INTENT

3. **Invite Bot to Server**
   - Go to OAuth2 → URL Generator
   - Select "bot" scope
   - Select required permissions
   - Copy URL and open in browser to invite bot

### Basic Bot Structure

```python
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

bot.run('YOUR_BOT_TOKEN')
```

### Slash Commands

Discord.py uses `app_commands.CommandTree` for application slash commands.

```python
import discord
from discord import app_commands

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tree.command(name="hello", description="Say hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello!")

@client.event
async def on_ready():
    await tree.sync()  # Sync commands to Discord
    print(f'{client.user} is ready!')

client.run('YOUR_BOT_TOKEN')
```

---

## Connecting to External APIs

### Using aiohttp (Recommended)

**Why aiohttp?** Using `requests` in async functions blocks the entire event loop. Use `aiohttp` for async HTTP requests.

#### Installation

```bash
pip install aiohttp
```

#### Best Practices

1. **Reuse ClientSession** - Create one session and reuse it for all requests
2. **Use Semaphores** - Limit concurrent requests to avoid rate limiting
3. **Handle Exceptions** - Always handle network errors and timeouts
4. **Close on Shutdown** - Properly clean up resources
5. **Defer Replies** - Use `interaction.response.defer()` for slow API calls

#### Example: Bot Calling External API

```python
import discord
from discord import app_commands
import aiohttp
import asyncio

class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.session = None
        self.semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent requests

    async def setup_hook(self):
        # Create persistent session
        self.session = aiohttp.ClientSession()
        await self.tree.sync()

    async def close(self):
        # Clean up on shutdown
        if self.session:
            await self.session.close()
        await super().close()

bot = Bot()

@bot.tree.command(name="api_data", description="Fetch data from API")
async def fetch_api_data(interaction: discord.Interaction, query: str):
    # Defer reply to show "thinking..." state
    await interaction.response.defer()

    try:
        async with bot.semaphore:
            async with bot.session.get(
                f'https://your-api.com/endpoint?query={query}',
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    await interaction.followup.send(f"Result: {data['result']}")
                else:
                    await interaction.followup.send(f"API error: {response.status}")

    except asyncio.TimeoutError:
        await interaction.followup.send("Request timed out")
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")

@bot.event
async def on_ready():
    print(f'{bot.user} is ready!')

bot.run('YOUR_BOT_TOKEN')
```

### Error Handling & Timeouts

```python
import aiohttp

try:
    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=10)
    ) as response:
        if response.status == 200:
            data = await response.json()
        elif response.status == 404:
            # Handle not found
            pass
        else:
            # Handle other errors
            pass
except asyncio.TimeoutError:
    print("Request timed out")
except aiohttp.ClientError as e:
    print(f"Network error: {e}")
```

---

## Webhooks

Webhooks are simpler than bots for one-way communication (sending notifications from your API to Discord).

### Setup Webhook in Discord

1. Go to Server Settings → Integrations → Webhooks
2. Click "Create Webhook"
3. Name it and select channel
4. Click "Copy Webhook URL"

### Python Implementation

#### Method 1: Using requests library

```bash
pip install requests
```

```python
import requests

webhook_url = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"

data = {
    "content": "Hello from my API!",
    "username": "API Bot",
    "embeds": [{
        "title": "Status Update",
        "description": "Service is running",
        "color": 0x00ff00  # Green
    }]
}

response = requests.post(webhook_url, json=data)
if response.status_code == 204:
    print("Message sent successfully")
```

#### Method 2: Using discord-webhook library

```bash
pip install discord-webhook
```

```python
from discord_webhook import DiscordWebhook, DiscordEmbed

webhook = DiscordWebhook(url="YOUR_WEBHOOK_URL")

embed = DiscordEmbed(
    title="API Notification",
    description="New event occurred",
    color='03b2f8'
)
embed.add_embed_field(name="Status", value="Success")
embed.add_embed_field(name="Time", value="2025-10-06 12:00:00")

webhook.add_embed(embed)
response = webhook.execute()
```

#### Method 3: Using discord.py (Async)

```python
import discord
from discord import Webhook
import aiohttp

async def send_webhook():
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(
            'YOUR_WEBHOOK_URL',
            session=session
        )
        await webhook.send('Hello from async webhook!')
```

### Webhook vs Bot

| Feature | Webhook | Bot |
|---------|---------|-----|
| Complexity | Simple | More complex |
| Direction | One-way (to Discord) | Two-way |
| Authentication | URL-based | Token-based |
| Commands | No | Yes |
| API Rate Limits | Lower | Higher |
| Use Case | Notifications, alerts | Interactive features |

---

## External API Triggering Bot Actions

If you need your API to trigger bot actions (not just receive requests from Discord):

### Option 1: HTTP Server in Bot

```python
from aiohttp import web
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

# Create HTTP server
app = web.Application()

async def handle_api_request(request):
    """Endpoint for external API to call"""
    data = await request.json()

    # Verify authentication (JWT, API key, etc.)
    auth_header = request.headers.get('Authorization')
    if auth_header != 'Bearer YOUR_SECRET_TOKEN':
        return web.Response(status=401, text="Unauthorized")

    # Trigger bot action
    channel = bot.get_channel(int(data['channel_id']))
    if channel:
        await channel.send(data['message'])
        return web.Response(status=200, text="Message sent")

    return web.Response(status=404, text="Channel not found")

app.router.add_post('/trigger', handle_api_request)

async def start_web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Web server running on port 8080")

@bot.event
async def on_ready():
    print(f'{bot.user} is ready!')
    await start_web_server()

bot.run('YOUR_BOT_TOKEN')
```

### Option 2: Queue-Based System

Use a message queue (Redis, RabbitMQ) where your API pushes events and the bot consumes them.

---

## Best Practices

### Security

1. **Never expose bot tokens** - Use environment variables
   ```python
   import os
   token = os.getenv('DISCORD_BOT_TOKEN')
   ```

2. **Validate external API responses** - Don't trust data blindly

3. **Secure bot endpoints** - Use JWT or API keys for authentication

4. **Rate limiting** - Respect Discord's rate limits (typically 50 requests/second)

### Performance

1. **Cache frequently accessed data** - Reduce API calls
   ```python
   from functools import lru_cache
   import time

   @lru_cache(maxsize=128)
   def cached_api_call(key, timestamp):
       # timestamp ensures cache expires
       return fetch_from_api(key)

   # Call with current time rounded to 5 minutes
   result = cached_api_call(key, time.time() // 300)
   ```

2. **Use connection pooling** - Reuse aiohttp sessions

3. **Implement semaphores** - Control concurrent requests

4. **Defer slow operations** - Use `interaction.response.defer()`

### Error Handling

1. **Always handle exceptions** - Network errors, API errors, timeouts

2. **Provide user feedback** - Don't leave interactions hanging

3. **Log errors** - Use proper logging for debugging
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger('discord')
   ```

### Code Organization

1. **Use Cogs** - Organize commands into modules
   ```python
   from discord.ext import commands

   class APICog(commands.Cog):
       def __init__(self, bot):
           self.bot = bot

       @commands.command()
       async def fetch(self, ctx):
           await ctx.send("Fetching data...")

   async def setup(bot):
       await bot.add_cog(APICog(bot))
   ```

2. **Environment configuration** - Use .env files
   ```bash
   pip install python-dotenv
   ```

   ```python
   from dotenv import load_dotenv
   import os

   load_dotenv()
   BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
   API_URL = os.getenv('API_URL')
   ```

---

## Code Examples

### Complete Example: K8s Manager Discord Bot

```python
import discord
from discord import app_commands
import aiohttp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

class K8sBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.session = None
        self.api_url = os.getenv('K8S_API_URL', 'http://localhost:8000')
        self.api_token = os.getenv('K8S_API_TOKEN')

    async def setup_hook(self):
        self.session = aiohttp.ClientSession(headers={
            'Authorization': f'Bearer {self.api_token}'
        })
        await self.tree.sync()

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = K8sBot()

@bot.tree.command(name="pods", description="List all pods in a namespace")
async def list_pods(interaction: discord.Interaction, namespace: str = "default"):
    await interaction.response.defer()

    try:
        async with bot.session.get(
            f'{bot.api_url}/api/v1/namespaces/{namespace}/pods',
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                data = await response.json()
                pods = data.get('pods', [])

                if not pods:
                    await interaction.followup.send(f"No pods found in namespace '{namespace}'")
                    return

                # Create embed
                embed = discord.Embed(
                    title=f"Pods in {namespace}",
                    color=discord.Color.blue()
                )

                for pod in pods[:10]:  # Limit to 10
                    embed.add_field(
                        name=pod['name'],
                        value=f"Status: {pod['status']}",
                        inline=False
                    )

                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"API Error: {response.status}")

    except asyncio.TimeoutError:
        await interaction.followup.send("Request timed out")
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")

@bot.tree.command(name="deploy", description="Deploy an application")
async def deploy(interaction: discord.Interaction, app_name: str, namespace: str = "default"):
    await interaction.response.defer()

    try:
        async with bot.session.post(
            f'{bot.api_url}/api/v1/deploy',
            json={'app_name': app_name, 'namespace': namespace},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                data = await response.json()
                await interaction.followup.send(f"✅ Deployed {app_name} to {namespace}")
            else:
                error = await response.text()
                await interaction.followup.send(f"❌ Deployment failed: {error}")

    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")

@bot.event
async def on_ready():
    print(f'{bot.user} is ready!')
    print(f'Connected to {len(bot.guilds)} servers')

if __name__ == '__main__':
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))
```

### Example: Webhook Notifications from API

```python
# In your API/backend code
import requests

def notify_discord(message: str, status: str = "info"):
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    color_map = {
        "success": 0x00ff00,  # Green
        "error": 0xff0000,    # Red
        "warning": 0xffa500,  # Orange
        "info": 0x0099ff      # Blue
    }

    data = {
        "embeds": [{
            "title": "K8s Manager Notification",
            "description": message,
            "color": color_map.get(status, 0x0099ff),
            "timestamp": datetime.utcnow().isoformat()
        }]
    }

    try:
        response = requests.post(webhook_url, json=data)
        return response.status_code == 204
    except Exception as e:
        print(f"Failed to send Discord notification: {e}")
        return False

# Usage in your API
@app.post("/deploy")
async def deploy_app(app_name: str):
    try:
        # ... deployment logic ...
        notify_discord(f"Successfully deployed {app_name}", "success")
        return {"status": "success"}
    except Exception as e:
        notify_discord(f"Deployment failed: {str(e)}", "error")
        raise
```

---

## Resources

- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/docs)
- [aiohttp Documentation](https://docs.aiohttp.org/)
- [Discord Webhook Guide](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
- [Real Python Discord Bot Tutorial](https://realpython.com/how-to-make-a-discord-bot-python/)

---

## Next Steps

1. Create Discord bot application and get token
2. Install required packages: `discord.py`, `aiohttp`, `python-dotenv`
3. Set up environment variables
4. Implement basic bot with slash commands
5. Add API integration using aiohttp
6. Deploy bot (consider using Docker, systemd, or cloud services)
7. Set up webhooks for notifications
8. Implement proper error handling and logging
9. Add rate limiting and caching
10. Monitor bot performance and API usage
