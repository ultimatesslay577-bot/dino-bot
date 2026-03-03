import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from flask import Flask
from threading import Thread

# ---------------- CONFIG ----------------
SCOREBOARD = {"name": "dinosaurs", "scoreboard_file": "dinosaurs_scoreboard.json", "channel_id": 1440123400524791921}
ALLOWED_ROLES = ["admin", "captains"]
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN_DINOSAURS")  # Environment variable for this bot's token

if not DISCORD_TOKEN:
    raise Exception("DISCORD_TOKEN_DINOSAURS is missing!")

# ---------------- FLASK KEEP-ALIVE ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Dinosaurs bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    thread = Thread(target=run_flask)
    thread.daemon = True
    thread.start()

keep_alive()

# ---------------- BOT ----------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=None, intents=intents)
tree = bot.tree

# ---------------- LOAD SCOREBOARD ----------------
scoreboard_path = os.path.join(DATA_DIR, SCOREBOARD["scoreboard_file"])

if not os.path.exists(scoreboard_path):
    with open(scoreboard_path, "w") as f:
        json.dump({"wins":0,"losses":0,"map_wins":0,"map_losses":0}, f)

def load_scoreboard():
    with open(scoreboard_path, "r") as f:
        return json.load(f)

def save_scoreboard():
    with open(scoreboard_path, "w") as f:
        json.dump(scoreboard_data, f)

scoreboard_data = load_scoreboard()
scoreboard_message_id = None

# ---------------- UTILITY FUNCTIONS ----------------
def get_ratio(w,l):
    if l==0: return f"{w:.2f}" if w>0 else "0"
    return f"{w/l:.2f}"

def get_map_win_percent(mw,ml):
    t = mw + ml
    return "0%" if t == 0 else f"{(mw/t) * 100:.1f}%"

def has_role(member):
    return any(role.name.lower() in ALLOWED_ROLES for role in member.roles)

def is_admin(member):
    return any(role.name.lower() == "admin" for role in member.roles)

def generate_scoreboard():
    return (
        f"**🏆 UGT {SCOREBOARD['name'].capitalize()}'s Scoreboard**\n"
        f"Wins: {scoreboard_data['wins']}\n"
        f"Losses: {scoreboard_data['losses']}\n"
        f"W/L Ratio: {get_ratio(scoreboard_data['wins'],scoreboard_data['losses'])}\n"
        f"Map Wins: {scoreboard_data['map_wins']}\n"
        f"Map Losses: {scoreboard_data['map_losses']}\n"
        f"Map Win%: {get_map_win_percent(scoreboard_data['map_wins'],scoreboard_data['map_losses'])}\n"
        f"@everyone"
    )

# Keep track of scoreboard messages
scoreboard_message_id = None

# ---------------- BOT EVENTS ----------------
@bot.event
async def on_ready():
    global scoreboard_message_id
    print(f"✅ {bot.user} is online!")

    channel = bot.get_channel(SCOREBOARD["channel_id"])
    if channel is None:
        print(f"❌ Channel not found for {SCOREBOARD['name']}")
        return

    # Look for existing message
    async for msg in channel.history(limit=10):
        if msg.author == bot.user and f"**🏆 UGT {SCOREBOARD['name'].capitalize()}'s Scoreboard**" in msg.content:
            scoreboard_message_id = msg.id
            break
    if scoreboard_message_id is None:
        msg = await channel.send(generate_scoreboard())
        scoreboard_message_id = msg.id

    await tree.sync()
    print(f"✅ Slash commands synced")

# ---------------- COMMANDS ----------------
@bot.command(name="add_maps")
async def add_maps(ctx, map_wins: int, map_losses: int):
    if not has_role(ctx.author):
        await ctx.send("❌ No permission", delete_after=5)
        return
    scoreboard_data["map_wins"] += map_wins
    scoreboard_data["map_losses"] += map_losses
    scoreboard_data["wins"] += map_wins > map_losses
    scoreboard_data["losses"] += map_wins < map_losses
    save_scoreboard()

    # Update message
    channel = bot.get_channel(SCOREBOARD["channel_id"])
    if channel:
        try:
            msg = await channel.fetch_message(scoreboard_message_id)
            await msg.edit(content=generate_scoreboard())
        except:
            pass

    await ctx.send("✅ Match added", delete_after=5)

@bot.command(name="reset")
async def reset_scoreboard(ctx):
    if not is_admin(ctx.author):
        await ctx.send("❌ Only admins can reset the scoreboard.", delete_after=5)
        return
    scoreboard_data.update({"wins": 0, "losses": 0, "map_wins": 0, "map_losses": 0})
    save_scoreboard()

    # Update message
    channel = bot.get_channel(SCOREBOARD["channel_id"])
    if channel:
        try:
            msg = await channel.fetch_message(scoreboard_message_id)
            await msg.edit(content=generate_scoreboard())
        except:
            pass

    await ctx.send("🧹 Scoreboard reset", delete_after=5)

# ---------------- START BOT ----------------
bot.run(DISCORD_TOKEN)