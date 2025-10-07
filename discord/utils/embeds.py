"""
Discord embed formatters
"""
import discord
from typing import List, Dict, Any


def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create a success embed (green)"""
    embed = discord.Embed(
        title=f"✅ {title}", description=description, color=discord.Color.green()
    )
    return embed


def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create an error embed (red)"""
    embed = discord.Embed(
        title=f"❌ {title}", description=description, color=discord.Color.red()
    )
    return embed


def create_info_embed(title: str, description: str) -> discord.Embed:
    """Create an info embed (blue)"""
    embed = discord.Embed(
        title=f"ℹ️ {title}", description=description, color=discord.Color.blue()
    )
    return embed


def create_projects_embed(projects: List[Dict[str, Any]]) -> discord.Embed:
    """Create an embed showing project list"""
    if not projects:
        return create_info_embed("Projects", "No projects found")

    embed = discord.Embed(title="📂 Your Projects", color=discord.Color.blue())

    for project in projects[:25]:  # Discord limit is 25 fields
        status_emoji = "🟢" if project["status"] == "active" else "🔴"
        endpoint = project.get("endpoint", "N/A")
        value = f"Status: {status_emoji} {project['status']}\nEndpoint: {endpoint}"

        if project.get("has_repository"):
            value += f"\n📦 Repo: {project.get('repo_url', 'N/A')[:50]}"

        embed.add_field(name=project["name"], value=value, inline=False)

    if len(projects) > 25:
        embed.set_footer(text=f"Showing 25 of {len(projects)} projects")

    return embed


def create_project_info_embed(project: Dict[str, Any]) -> discord.Embed:
    """Create detailed project info embed"""
    status_emoji = "🟢" if project["status"] == "active" else "🔴"

    embed = discord.Embed(
        title=f"📂 {project['name']}", color=discord.Color.blue()
    )

    embed.add_field(name="Status", value=f"{status_emoji} {project['status']}", inline=True)
    embed.add_field(name="Project ID", value=project["id"], inline=True)

    if project.get("endpoint"):
        embed.add_field(name="Endpoint", value=project["endpoint"], inline=False)

    if project.get("has_repository"):
        embed.add_field(
            name="Repository",
            value=project.get("repo_url", "N/A"),
            inline=False,
        )

    if project.get("github_key_set"):
        source = project.get("github_key_source", "unknown")
        embed.add_field(name="GitHub Key", value=f"✅ Set ({source})", inline=True)

    sessions = project.get("sessions", [])
    embed.add_field(name="Sessions", value=str(len(sessions)), inline=True)

    if project.get("created_at"):
        embed.add_field(
            name="Created",
            value=project['created_at'],
            inline=True,
        )

    return embed


def create_sessions_embed(
    project_name: str, sessions: List[Dict[str, Any]]
) -> discord.Embed:
    """Create an embed showing session list"""
    if not sessions:
        return create_info_embed(
            f"Sessions in {project_name}", "No sessions found"
        )

    embed = discord.Embed(
        title=f"💬 Sessions in '{project_name}'", color=discord.Color.blue()
    )

    for session in sessions[:25]:  # Discord limit
        msg_count = session.get("message_count", 0)
        created = session.get("created_at", "")
        value = f"Messages: {msg_count}"

        if created:
            value += f"\nCreated: {created}"

        embed.add_field(
            name=session.get("name", session["session_id"]),
            value=value,
            inline=False,
        )

    if len(sessions) > 25:
        embed.set_footer(text=f"Showing 25 of {len(sessions)} sessions")

    return embed
