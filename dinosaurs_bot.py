import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from flask import Flask
from threading import Thread

# ---------------- CONFIG ----------------
BOTS_CONFIG = [
    {"name": "dinosaurs", "token_env": "DISCORD_TOKEN_DINOSAURS", "scoreboard_file": "dinosaurs_scoreboard.json", "channel_id": 1440123400524791921}
]

ALLOWED_ROLES = ["admin", "captains"]
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- FLASK KEEP-ALIVE ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Dinosaur bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    thread = Thread(target=run_flask)
    thread.daemon = True
    thread.start()

keep_alive()

# ---------------- BOT FACTORY ----------------
def create_bot(config):
    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True
    intents.message_content = True

    bot = commands.Bot(command_prefix=None, intents=intents)
    tree = bot.tree

    scoreboard_path = os.path.join(DATA_DIR, config["scoreboard_file"])
    channel_id = config["channel_id"]
    bot_name = config["name"]

    if not os.path.exists(scoreboard_path):
        with open(scoreboard_path, "w") as f:
            json.dump({"wins": 0, "losses": 0, "map_wins": 0, "map_losses": 0}, f)

    def load_scoreboard():
        with open(scoreboard_path, "r") as f:
            return json.load(f)

    def save_scoreboard():
        with open(scoreboard_path, "w") as f:
            json.dump(scoreboard_data, f)

    scoreboard_data = load_scoreboard()
    scoreboard_message_id = None

    def has_role(member):
        return any(role.name.lower() in ALLOWED_ROLES for role in member.roles)

    def is_admin(member):
        return any(role.name.lower() == "admin" for role in member.roles)

    def get_ratio(w, l):
        if l == 0:
            return f"{w:.2f}" if w > 0 else "0"
        return f"{w / l:.2f}"

    def get_map_win_percent(mw, ml):
        t = mw + ml
        return "0%" if t == 0 else f"{(mw / t) * 100:.1f}%"

    def generate_scoreboard():
        return (
            f"**🏆 UGT {bot_name.capitalize()}'s Scoreboard**\n"
            f"Wins: {scoreboard_data['wins']}\n"
            f"Losses: {scoreboard_data['losses']}\n"
            f"W/L Ratio: {get_ratio(scoreboard_data['wins'], scoreboard_data['losses'])}\n"
            f"Map Wins: {scoreboard_data['map_wins']}\n"
            f"Map Losses: {scoreboard_data['map_losses']}\n"
            f"Map Win%: {get_map_win_percent(scoreboard_data['map_wins'], scoreboard_data['map_losses'])}\n"
            f"@everyone"
        )

    async def update_scoreboard():
        nonlocal scoreboard_message_id
        channel = bot.get_channel(channel_id)
        if channel and scoreboard_message_id:
            try:
                msg = await channel.fetch_message(scoreboard_message_id)
                await msg.edit(content=generate_scoreboard())
            except:
                scoreboard_message_id = None

    @bot.event
    async def on_ready():
        nonlocal scoreboard_message_id
        print(f"✅ {bot.user} is online!")

        # Sync commands only once
        if not synced:
            await tree.sync()
            print(f"✅ Slash commands synced")
            synced = True

        # Optional: Add a delay to prevent rate-limiting
        await asyncio.sleep(3)  # Sleep to space out requests

    # Commands
    group = app_commands.Group(name=bot_name, description=f"{bot_name.capitalize()} scoreboard commands")
    tree.add_command(group)

    @group.command(name="add_maps")
    async def add_maps
