import os
import discord
from discord.ext import commands
from discord import Message as DiscordMessage
from dotenv import load_dotenv
import openai

from code_monkey import handle_cm_message
from database import Database
from llm import LLM

# Load the environment variables from the .env file
load_dotenv()

# initialize openai from the env
openai.api_key = os.environ["OPENAI_API_KEY"]

# Load the model into the LLM wrapper
LM = LLM()

# Connect to the database
DB = Database(
    uri=os.environ['DATABASE_URI'], db_name=os.environ['DATABASE_NAME']
)

# Create a new Discord client
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready() -> None:
    print(f"We have logged in as {client.user}", flush=True)


@client.event
async def on_message(message: DiscordMessage) -> None:
    if not client.user.mentioned_in(message):
        return
    res = await message.channel.send("Monkey Thinking...")
    # Start the message handler task in the background
    try:
        client.loop.create_task(handle_cm_message(DB, LM, client.user, message, res))
    except Exception as e:
        await res.edit(content="Monkey dropped the banana...")
        raise e

client.run(os.environ.get("DISCORD_TOKEN"))
