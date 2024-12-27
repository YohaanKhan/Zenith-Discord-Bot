import discord
from discord.ext import commands, tasks
from itertools import cycle
import requests
import json
import os
import asyncio
import threading
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Define intents
intents = discord.Intents.default()
intents.messages = True  # Allow message reading
intents.message_content = True  # Allow content of messages to be read
intents.guilds = True
intents.members = True

# Initializes the bot
bot = commands.Bot(command_prefix=".", intents=intents)

# This is the collection of the various defined status of the bot
status = cycle([
    "Leveling up in real life 🌟",
    "Your journey to greatness 🚀",
    "The sound of progress 🎧",
    "Turning effort into achievement 🛠️"
])

# Change bot status loop in a specific interval
@tasks.loop(seconds=20)
async def change_status():
    await bot.change_presence(activity=discord.Game(next(status)))

# Prints a message when the bot is ready
@bot.event
async def on_ready():
    print(f"{bot.user} is ready!")
    change_status.start()

# Basic hello command to check the activity of the bot (pre-production)
@bot.command()
async def hello(ctx):
    """a basic function that greets the user"""
    await ctx.send(f"Hey {ctx.author.mention}!!")

#This is a command that makes an api call to the zenquotes api and then loads a random quote from their collection
@bot.command()
async def quote(ctx):
    """generates a random motivational quote"""
    await ctx.send(get_quote())

def get_quote():
    response = requests.get("https://zenquotes.io/api/random")
    json_data = json.loads(response.text)
    quote = f"{json_data[0]['q']} - {json_data[0]['a']}"
    return quote

# Load cogs dynamically
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

# Flask app setup
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

# Function to run Flask in a separate thread
def run_flask():
    app.run(host="0.0.0.0", port=80)

# Main function to run both Flask and Discord bot
async def main():
    # Run Flask server in a separate thread
    threading.Thread(target=run_flask).start()

    async with bot:
        await load_cogs()
        # Get token from the environment variable
        token = os.getenv("DISCORD_TOKEN")
        if token is None:
            print("No token found. Make sure the token is set in the .env file.")
            return
        await bot.start(token)

#runs the main function (classic python style)
if __name__ == "__main__":
    asyncio.run(main())
