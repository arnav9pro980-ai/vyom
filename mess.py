import asyncio
import os
import subprocess
import discord
from discord import app_commands
from discord.ext import commands

# ================= CONFIGURATION =================
# REMINDER: Reset your token in the Discord Portal if you haven't already!
BOT_TOKEN = "MTQ4MzAyMzU5NTUyODUyMzkwOA.GRIW5x.v-mF147uzDi796gyJ8l-_HCGfx8mTYBXIdIy-E"

# Optional: Add your Discord User ID (integer) to restrict command requests.
AUTHORIZED_USER_ID = None  # Example: 123456789012345678
# =================================================


class TerminalSession:
    """Manages persistent terminal state (directory, environment variables)."""

    def __init__(self, name: str):
        self.name = name
        self.cwd = os.getcwd()
        self.env = os.environ.copy()

    async def execute(self, command: str) -> str:
        """Executes command while preserving cwd state across calls."""
        if command.strip().startswith("cd "):
            target_dir = command.strip()[3:].strip().strip('"').strip("'")
            new_path = os.path.abspath(os.path.join(self.cwd, target_dir))
            if os.path.exists(new_path) and os.path.isdir(new_path):
                self.cwd = new_path
                return f"Directory changed to: `{self.cwd}`"
            else:
                return f"❌ System Error: Directory not found: `{target_dir}`"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                env=self.env,
            )
            stdout, stderr = await process.communicate()
            output = (
                stdout.decode().strip()
                or stderr.decode().strip()
                or "Command executed successfully (no output returned)."
            )
            return output
        except Exception as e:
            return f"❌ Execution Error: {str(e)}"


# Global Terminal Session Store
TERMINALS = {"default": TerminalSession("default")}
ACTIVE_TERMINAL = "default"


class ApprovalView(discord.ui.View):
    """Interactive Discord buttons for approving or denying commands."""

    def __init__(self, command_str: str, session_name: str, requester: str):
        super().__init__(timeout=120)  # Request expires in 2 minutes
        self.command_str = command_str
        self.session_name = session_name
        self.requester = requester
        self.approved = None

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.approved = True
        self.stop()
        await interaction.response.send_message(
            f"✅ **Command approved by {interaction.user.display_name}.** Executing in terminal `{self.session_name}`..."
        )

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.approved = False
        self.stop()
        await interaction.response.send_message(
            f"❌ **Command denied by {interaction.user.display_name}.**"
        )


class RemoteExecClient(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        print("Syncing slash commands...")
        await self.tree.sync()
        print("Slash commands synced successfully!")


client = RemoteExecClient()


@client.event
async def on_ready():
    print(f"Logged in as {client.user.name} (ID: {client.user.id})")
    print("Agent is running and listening for slash commands.")


@client.tree.command(
    name="run",
    description="Request permission to execute a command on host in the active terminal.",
)

@app_commands.describe(command="The terminal command you want to execute")
async def run_command(interaction: discord.Interaction, command: str):
    global ACTIVE_TERMINAL

    # 1. Defer response immediately to prevent timeout
    await interaction.response.defer()

    # 2. Keep the authorization check (optional: remove if anyone can run commands)
    if AUTHORIZED_USER_ID and interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.followup.send(
            "🚫 You are not authorized to request remote commands.",
            ephemeral=True,
        )
        return

    session = TERMINALS[ACTIVE_TERMINAL]

    # 3. Execute immediately in persistent terminal
    output = await session.execute(command)

    if len(output) > 1900:
        output = output[:1900] + "\n... [Output truncated]"

    # 4. Return output via followup
    await interaction.followup.send(
        f"**Execution Output (`{ACTIVE_TERMINAL}` - `{command}`):**\n```\n{output}\n```"
    )


@client.tree.command(
    name="terminal",
    description="Manage persistent terminal sessions (create, switch, list).",
)
@app_commands.describe(
    action="Action to perform (create, switch, list)",
    name="Terminal name (for create or switch)",
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="create", value="create"),
        app_commands.Choice(name="switch", value="switch"),
    ]
)
async def terminal_cmd(
    interaction: discord.Interaction, action: str, name: str = None
):
    global ACTIVE_TERMINAL, TERMINALS

    if AUTHORIZED_USER_ID and interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message(
            "🚫 You are not authorized.", ephemeral=True
        )
        return

    if action == "list":
        term_list = "\n".join(
            [
                f"• **{t_name}** {'*(Active)*' if t_name == ACTIVE_TERMINAL else ''} — `{term.cwd}`"
                for t_name, term in TERMINALS.items()
            ]
        )
        embed = discord.Embed(
            title="💻 Active Terminal Sessions",
            description=term_list,
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed)

    elif action == "create":
        if not name:
            await interaction.response.send_message(
                "❌ Please specify a terminal name: `/terminal action:create name:<name>`",
                ephemeral=True,
            )
            return

        clean_name = name.lower().strip()
        if clean_name in TERMINALS:
            await interaction.response.send_message(
                f"⚠️ Terminal `{clean_name}` already exists.", ephemeral=True
            )
            return

        TERMINALS[clean_name] = TerminalSession(clean_name)
        ACTIVE_TERMINAL = clean_name
        await interaction.response.send_message(
            f"✅ Created new terminal session **`{clean_name}`** and set as active.\nCurrent Directory: `{TERMINALS[clean_name].cwd}`"
        )

    elif action == "switch":
        if not name:
            await interaction.response.send_message(
                "❌ Please specify a terminal name to switch to: `/terminal action:switch name:<name>`",
                ephemeral=True,
            )
            return

        clean_name = name.lower().strip()
        if clean_name not in TERMINALS:
            await interaction.response.send_message(
                f"❌ Terminal `{clean_name}` does not exist. Use `/terminal action:list` to see available terminals.",
                ephemeral=True,
            )
            return

        ACTIVE_TERMINAL = clean_name
        await interaction.response.send_message(
            f"🔄 Switched active terminal to **`{ACTIVE_TERMINAL}`**.\nCurrent Directory: `{TERMINALS[ACTIVE_TERMINAL].cwd}`"
        )


@client.tree.command(
    name="shutdown",
    description="Safely shut down and terminate the remote execution bot process.",
)
async def shutdown_command(interaction: discord.Interaction):
    await interaction.response.defer()

    if AUTHORIZED_USER_ID and interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.followup.send(
            "🚫 You are not authorized.", ephemeral=True
        )
        return

    embed = discord.Embed(
        title="⚠️ Remote Bot Shutdown Requested",
        description=f"**Requester:** {interaction.user.mention}\n\nClick **Approve** to terminate the python script on the host machine.",
        color=discord.Color.red(),
    )

    view = ApprovalView(
        command_str="shutdown",
        session_name=ACTIVE_TERMINAL,
        requester=interaction.user.display_name,
    )

    msg = await interaction.followup.send(embed=embed, view=view)
    await view.wait()

    for item in view.children:
        item.disabled = True

    if view.approved is None:
        await msg.edit(
            content="⏳ **Shutdown request timed out.** Bot remains active.",
            view=view,
        )
        return

    if not view.approved:
        await msg.edit(view=view)
        return

    await msg.edit(view=view)
    await interaction.channel.send(
        "🛑 **Shutting down bot process... Goodbye!**"
    )

    await client.close()
    os._exit(0)


@client.tree.command(
    name="help",
    description="Show instructions and list all available commands.",
)
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Remote Execution Bot — Help Guide",
        description="Run commands on your friend's PC with approval safeguards and persistent terminals.",
        color=discord.Color.green(),
    )

    embed.add_field(
        name="⚡ `/run <command>`",
        value="Requests execution of a command on the host. Posts **Approve** and **Deny** buttons for the host to confirm.",
        inline=False,
    )
    embed.add_field(
        name="💻 `/terminal action:list`",
        value="Lists all active terminal sessions and highlights the current session.",
        inline=False,
    )
    embed.add_field(
        name="➕ `/terminal action:create name:<name>`",
        value="Creates a new independent terminal session with its own path/directory state and switches to it.",
        inline=False,
    )
    embed.add_field(
        name="🔄 `/terminal action:switch name:<name>`",
        value="Switches the active shell context to an existing terminal.",
        inline=False,
    )
    embed.add_field(
        name="🛑 `/shutdown`",
        value="Requests permission to close and exit the Python bot process on the host machine.",
        inline=False,
    )
    embed.add_field(
        name="❓ `/help`",
        value="Displays this help message.",
        inline=False,
    )

    embed.set_footer(
        text=f"Active Terminal: {ACTIVE_TERMINAL} | Total Terminals Open: {len(TERMINALS)}"
    )
    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    client.run(BOT_TOKEN)
