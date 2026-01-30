import asyncio
import os
import random
import discord
from discord.ext import commands
from dotenv import load_dotenv
import time
from datetime import datetime
from keep_alive import keep_alive

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

keep_alive()

# Gemini client (lazy init)
gemini_client = None

def get_gemini_client():
    global gemini_client
    if gemini_client is None and GEMINI_API_KEY:
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "Gemini SDK not installed. Run: pip install google-genai"
            ) from None
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return gemini_client

intents = discord.Intents.default()
intents.message_content = True  # Required for reading message content

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)  # Disable default help

# Storage for quotes, timers, and coordinates
server_quotes = {}
user_timers = {}
server_coordinates = {}  # {guild_id: {name: {lat, long, saved_by, timestamp}}}


@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Aitrik's server"))


# --- Help/Commands List ---
@bot.command(name="cmds", aliases=["commands", "help"])
async def show_commands(ctx):
    """Show all available commands."""
    embed = discord.Embed(
        title="🤖 Bot Commands",
        description="Here are all the commands you can use!",
        color=discord.Color.blue(),
    )
    
    # Basic Commands
    basic = "**!hello** - Say hello\n**!ping** - Check bot latency\n**!yo** - Casual greeting"
    embed.add_field(name="👋 Basic", value=basic, inline=False)
    
    # Fun Commands
    fun = (
        "**!8ball** `<question>` - Ask the magic 8-ball\n"
        "**!roll** `[dice]` - Roll dice (e.g., 2d6, 1d20)\n"
        "**!choose** `<options>` - Pick from comma-separated options\n"
        "**!poll** `<question>` - Create a yes/no poll\n"
        "**!coinflip** - Flip a coin\n"
        "**!rps** `<choice>` - Rock, paper, scissors\n"
        "**!meme** - Get a random meme\n"
        "**!joke** - Get a random joke"
    )
    embed.add_field(name="🎮 Fun & Games", value=fun, inline=False)
    
    # Info Commands
    info = (
        "**!serverinfo** - Show server stats\n"
        "**!avatar** `[@user]` - Show avatar\n"
        "**!userinfo** `[@user]` - Show user info"
    )
    embed.add_field(name="ℹ️ Info", value=info, inline=False)
    
    # Utility Commands
    utility = (
        "**!calc** `<expression>` - Calculate math\n"
        "**!timer** `<seconds>` - Set a countdown timer\n"
        "**!quote save** `<text>` - Save a quote\n"
        "**!quote random** - Show random saved quote\n"
        "**!quote list** - List all quotes\n"
        "**!cords add** `<name> <x> <y> <z> [dimension]` - Save coordinates\n"
        "**!cords** `<name>` - Get specific coordinates\n"
        "**!cords list** - List all saved locations\n"
        "**!cords delete** `<name>` - Delete coordinates"
    )
    embed.add_field(name="🛠️ Utility", value=utility, inline=False)
    
    # AI Commands (if Gemini is configured)
    if GEMINI_API_KEY:
        ai = (
            "**!ask** `<question>` - Ask Gemini AI\n"
            "**!summarize** `<text>` - Summarize text\n"
            "**!rewrite** `<style>` `<text>` - Rewrite in a style\n"
            "**!brainstorm** `<topic>` - Get creative ideas\n"
            "**!story** `<prompt>` - Generate a short story\n"
            "**!explain** `<code>` - Explain code"
        )
        embed.add_field(name="✨ AI Features", value=ai, inline=False)
    
    embed.set_footer(text=f"Use !<command> to run | Requested by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


# --- Basic Commands ---
@bot.command(name="hello")
async def hello(ctx):
    """Say hello to the bot."""
    await ctx.reply(f"Hello, {ctx.author.display_name}! 👋")


@bot.command(name="ping")
async def ping(ctx):
    """Check bot latency."""
    latency_ms = round(bot.latency * 1000)
    await ctx.reply(f"Pong! 🏓 Latency: **{latency_ms}** ms")


@bot.command(name="yo")
async def yo(ctx):
    """Respond in the #yo channel style."""
    await ctx.reply("Yo! What's up? 😎")


# --- Fun & Game Commands ---

EIGHTBALL_ANSWERS = [
    "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes – definitely.",
    "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
    "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
    "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.",
    "Very doubtful.",
]


@bot.command(name="8ball", aliases=["eightball"])
async def eightball(ctx, *, question: str = None):
    """Ask the magic 8ball a yes/no question."""
    if not question:
        await ctx.reply("Ask me something! Example: `!8ball Will I win the lottery?`")
        return
    answer = random.choice(EIGHTBALL_ANSWERS)
    embed = discord.Embed(
        title="🎱 Magic 8 Ball",
        description=f"**Q:** {question}\n**A:** {answer}",
        color=discord.Color.dark_blue(),
    )
    embed.set_footer(text=f"Asked by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


@bot.command(name="roll", aliases=["dice"])
async def roll(ctx, dice: str = "1d6"):
    """Roll dice. Usage: !roll 2d6, !roll 1d20, !roll 4d10"""
    try:
        count, sides = dice.lower().split("d")
        count, sides = int(count), int(sides)
        if count < 1 or count > 20 or sides < 2 or sides > 100:
            await ctx.reply("Use format like `2d6` or `1d20`. Max 20 dice, 2–100 sides.")
            return
    except ValueError:
        await ctx.reply("Use format like `2d6` (2 six-sided dice) or `1d20`.")
        return
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    detail = " + ".join(str(r) for r in rolls)
    if count > 1:
        detail += f" = **{total}**"
    embed = discord.Embed(
        title="🎲 Dice Roll",
        description=f"`{dice}` → {detail}",
        color=discord.Color.green(),
    )
    embed.set_footer(text=f"Rolled by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


@bot.command(name="choose", aliases=["pick"])
async def choose(ctx, *, options: str):
    """Pick randomly from options. Example: !choose pizza, burger, pasta"""
    choices = [o.strip() for o in options.split(",") if o.strip()]
    if len(choices) < 2:
        await ctx.reply("Give me at least 2 options separated by commas!")
        return
    if len(choices) > 20:
        await ctx.reply("Max 20 options.")
        return
    winner = random.choice(choices)
    await ctx.reply(f"**I choose:** {winner} 🎯")


@bot.command(name="poll")
async def poll(ctx, *, question: str):
    """Create a yes/no poll with reactions."""
    embed = discord.Embed(
        title="📊 Poll",
        description=question,
        color=discord.Color.gold(),
    )
    embed.set_footer(text=f"Poll by {ctx.author.display_name}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")


@bot.command(name="coinflip", aliases=["flip", "coin"])
async def coinflip(ctx):
    """Flip a coin - heads or tails."""
    result = random.choice(["Heads", "Tails"])
    emoji = "🪙"
    embed = discord.Embed(
        title=f"{emoji} Coin Flip",
        description=f"The coin landed on: **{result}**!",
        color=discord.Color.orange(),
    )
    embed.set_footer(text=f"Flipped by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


@bot.command(name="rps", aliases=["rockpaperscissors"])
async def rps(ctx, choice: str = None):
    """Play rock, paper, scissors. Usage: !rps rock"""
    if not choice:
        await ctx.reply("Choose rock, paper, or scissors! Example: `!rps rock`")
        return
    
    choice = choice.lower()
    valid_choices = ["rock", "paper", "scissors"]
    
    if choice not in valid_choices:
        await ctx.reply("Invalid choice! Choose: rock, paper, or scissors")
        return
    
    bot_choice = random.choice(valid_choices)
    
    # Determine winner
    if choice == bot_choice:
        result = "It's a tie!"
        color = discord.Color.gold()
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
        color = discord.Color.green()
    else:
        result = "I win! 🤖"
        color = discord.Color.red()
    
    emoji_map = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    
    embed = discord.Embed(
        title="Rock, Paper, Scissors!",
        description=f"You chose: {emoji_map[choice]} **{choice.capitalize()}**\nI chose: {emoji_map[bot_choice]} **{bot_choice.capitalize()}**\n\n{result}",
        color=color,
    )
    embed.set_footer(text=f"Played by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


@bot.command(name="meme")
async def meme(ctx):
    """Get a random meme (placeholder - would need meme API)."""
    meme_texts = [
        "When you finally fix that bug... and create 3 more 🐛",
        "Me: *writes one line of code*\nAlso me: I'm basically a hacker now 😎",
        "Copy code from Stack Overflow ❌\nUnderstand the code ❌\nIt works ✅",
        "Programming is 10% writing code and 90% figuring out why it doesn't work",
        "There are only 10 types of people: those who understand binary and those who don't",
    ]
    meme = random.choice(meme_texts)
    embed = discord.Embed(
        title="😂 Random Meme",
        description=meme,
        color=discord.Color.purple(),
    )
    await ctx.reply(embed=embed)


JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs! 🐛",
    "Why did the developer go broke? Because he used up all his cache! 💰",
    "How many programmers does it take to change a light bulb? None, that's a hardware problem! 💡",
    "Why do Java developers wear glasses? Because they don't C#! 👓",
    "What's a programmer's favorite hangout place? Foo Bar! 🍺",
    "Why did the programmer quit his job? Because he didn't get arrays! 📊",
    "What do you call 8 hobbits? A hobbyte! 🧙‍♂️",
    "Why was the JavaScript developer sad? Because he didn't Node how to Express himself! 😢",
]


@bot.command(name="joke")
async def joke(ctx):
    """Get a random programming joke."""
    selected_joke = random.choice(JOKES)
    embed = discord.Embed(
        title="😄 Random Joke",
        description=selected_joke,
        color=discord.Color.green(),
    )
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


# --- Info Commands ---

@bot.command(name="serverinfo", aliases=["server"])
async def serverinfo(ctx):
    """Show server stats in a nice embed."""
    guild = ctx.guild
    embed = discord.Embed(
        title=guild.name,
        description=guild.description or "No description.",
        color=discord.Color.blue(),
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="🆔 Server ID", value=str(guild.id), inline=True)
    embed.add_field(name="📅 Created", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="👥 Members", value=str(guild.member_count), inline=True)
    embed.add_field(name="📁 Channels", value=str(len(guild.channels)), inline=True)
    embed.add_field(name="😀 Emojis", value=str(len(guild.emojis)), inline=True)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


@bot.command(name="avatar", aliases=["av", "pfp"])
async def avatar(ctx, member: discord.Member = None):
    """Show your or someone else's avatar (click for full size)."""
    member = member or ctx.author
    embed = discord.Embed(
        title=f"{member.display_name}'s avatar",
        color=member.accent_color or discord.Color.blurple(),
    )
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


@bot.command(name="userinfo", aliases=["user", "whois"])
async def userinfo(ctx, member: discord.Member = None):
    """Show information about a user."""
    member = member or ctx.author
    
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    roles_str = ", ".join(roles) if roles else "No roles"
    
    embed = discord.Embed(
        title=f"User Info: {member.display_name}",
        color=member.color,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 Username", value=str(member), inline=True)
    embed.add_field(name="🆔 ID", value=str(member.id), inline=True)
    embed.add_field(name="📅 Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    embed.add_field(name="📆 Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="🎭 Roles", value=roles_str, inline=False)
    
    if member.premium_since:
        embed.add_field(name="💎 Boosting Since", value=f"<t:{int(member.premium_since.timestamp())}:R>", inline=True)
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


# --- Utility Commands ---

@bot.command(name="calc", aliases=["calculate", "math"])
async def calc(ctx, *, expression: str):
    """Calculate a math expression. Example: !calc 5 + 3 * 2"""
    try:
        # Remove any potentially dangerous characters
        allowed_chars = "0123456789+-*/(). "
        cleaned = "".join(c for c in expression if c in allowed_chars)
        
        if not cleaned:
            await ctx.reply("Invalid expression! Use numbers and operators: +, -, *, /, (, )")
            return
        
        result = eval(cleaned)
        
        embed = discord.Embed(
            title="🧮 Calculator",
            description=f"**Expression:** `{expression}`\n**Result:** `{result}`",
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Calculated by {ctx.author.display_name}")
        await ctx.reply(embed=embed)
    except ZeroDivisionError:
        await ctx.reply("❌ Cannot divide by zero!")
    except Exception as e:
        await ctx.reply(f"❌ Invalid expression! Error: {str(e)[:100]}")


@bot.command(name="timer")
async def timer(ctx, seconds: int = None):
    """Set a countdown timer. Example: !timer 60"""
    if seconds is None:
        await ctx.reply("Specify seconds! Example: `!timer 60` for 1 minute")
        return
    
    if seconds < 1 or seconds > 3600:
        await ctx.reply("Timer must be between 1 and 3600 seconds (1 hour)!")
        return
    
    embed = discord.Embed(
        title="⏲️ Timer Started",
        description=f"Timer set for **{seconds}** seconds",
        color=discord.Color.green(),
    )
    msg = await ctx.reply(embed=embed)
    
    await asyncio.sleep(seconds)
    
    embed = discord.Embed(
        title="⏰ Timer Complete!",
        description=f"{ctx.author.mention} Your **{seconds}** second timer is up!",
        color=discord.Color.red(),
    )
    await msg.edit(embed=embed)
    await ctx.send(f"{ctx.author.mention} ⏰ Time's up!")


@bot.group(name="quote", invoke_without_command=True)
async def quote(ctx):
    """Quote system. Use !quote save/random/list"""
    await ctx.reply("Use `!quote save <text>`, `!quote random`, or `!quote list`")


@quote.command(name="save", aliases=["add"])
async def quote_save(ctx, *, text: str):
    """Save a quote to the server."""
    guild_id = ctx.guild.id
    
    if guild_id not in server_quotes:
        server_quotes[guild_id] = []
    
    quote_data = {
        "text": text,
        "author": ctx.author.display_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    server_quotes[guild_id].append(quote_data)
    
    embed = discord.Embed(
        title="💾 Quote Saved!",
        description=f"\"{text}\"",
        color=discord.Color.green(),
    )
    embed.set_footer(text=f"Saved by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


@quote.command(name="random", aliases=["show"])
async def quote_random(ctx):
    """Show a random saved quote."""
    guild_id = ctx.guild.id
    
    if guild_id not in server_quotes or not server_quotes[guild_id]:
        await ctx.reply("No quotes saved yet! Use `!quote save <text>` to add one.")
        return
    
    quote_data = random.choice(server_quotes[guild_id])
    
    embed = discord.Embed(
        title="💬 Random Quote",
        description=f"\"{quote_data['text']}\"",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Saved by", value=quote_data['author'], inline=True)
    embed.add_field(name="Date", value=quote_data['timestamp'], inline=True)
    await ctx.reply(embed=embed)


@quote.command(name="list", aliases=["all"])
async def quote_list(ctx):
    """List all saved quotes."""
    guild_id = ctx.guild.id
    
    if guild_id not in server_quotes or not server_quotes[guild_id]:
        await ctx.reply("No quotes saved yet! Use `!quote save <text>` to add one.")
        return
    
    quotes = server_quotes[guild_id]
    
    embed = discord.Embed(
        title=f"📚 All Quotes ({len(quotes)})",
        color=discord.Color.purple(),
    )
    
    for i, q in enumerate(quotes[:10], 1):  # Show first 10
        embed.add_field(
            name=f"Quote #{i}",
            value=f"\"{q['text'][:100]}{'...' if len(q['text']) > 100 else ''}\"\n*- {q['author']}*",
            inline=False
        )
    
    if len(quotes) > 10:
        embed.set_footer(text=f"Showing 10 of {len(quotes)} quotes")
    
    await ctx.reply(embed=embed)


# --- Coordinates System ---

@bot.group(name="cords", aliases=["coords", "coordinates"], invoke_without_command=True)
async def cords(ctx, *, name: str = None):
    """Coordinate system. Use !cords add/list or !cords <name>"""
    if name is None:
        await ctx.reply("Use `!cords add <name> <x> <y> <z> [dimension]`, `!cords <name>`, or `!cords list`")
        return
    
    # Search for coordinate by name
    guild_id = ctx.guild.id
    
    if guild_id not in server_coordinates or not server_coordinates[guild_id]:
        await ctx.reply("No locations saved yet! Use `!cords add` to save some.")
        return
    
    # Case-insensitive search
    name_lower = name.lower()
    coords = server_coordinates[guild_id]
    
    matching = [k for k in coords.keys() if k.lower() == name_lower]
    
    if not matching:
        await ctx.reply(f"No location found for '{name}'. Use `!cords list` to see all saved locations.")
        return
    
    coord_name = matching[0]
    data = coords[coord_name]
    
    # Create Google Maps link
    maps_link = f"https://www.google.com/maps?q={data['lat']},{data['long']}"
    
    embed = discord.Embed(
        title=f"📍 {coord_name}",
        description=f"**Latitude:** {data['lat']}\n**Longitude:** {data['long']}",
        color=discord.Color.green(),
    )
    embed.add_field(name="Saved by", value=data['saved_by'], inline=True)
    embed.add_field(name="Date", value=data['timestamp'], inline=True)
    
    # Add formatted coordinate string for easy copying
    coord_str = f"`{data['lat']}, {data['long']}`"
    embed.add_field(name="Copy Coords", value=coord_str, inline=False)
    embed.add_field(name="Google Maps", value=f"[View on Maps]({maps_link})", inline=False)
    
    await ctx.reply(embed=embed)



@cords.command(name="add", aliases=["save"])
async def cords_add(ctx, name: str, coords: str):
    """Save coordinates. Example: !cords add kiri 10.89337,26.237237"""
    guild_id = ctx.guild.id
    
    if guild_id not in server_coordinates:
        server_coordinates[guild_id] = {}
    
    # Parse coordinates - expect format: lat,long
    try:
        # Split by comma
        parts = coords.replace(" ", "").split(",")
        
        if len(parts) != 2:
            await ctx.reply("Invalid format! Use: `!cords add <name> <lat>,<long>`\nExample: `!cords add kiri 10.89337,26.237237`")
            return
        
        lat, long = parts[0], parts[1]
        
        # Validate coordinates are numbers
        lat_val = float(lat)
        long_val = float(long)
        
    except (ValueError, IndexError):
        await ctx.reply("Invalid coordinates! Make sure latitude and longitude are numbers.\nExample: `!cords add kiri 10.89337,26.237237`")
        return
    
    # Check if name already exists (case-insensitive)
    name_lower = name.lower()
    existing = [k for k in server_coordinates[guild_id].keys() if k.lower() == name_lower]
    
    if existing:
        await ctx.reply(f"Location '{existing[0]}' already exists! Use `!cords delete {existing[0]}` first to replace it.")
        return
    
    coord_data = {
        "lat": lat,
        "long": long,
        "saved_by": ctx.author.display_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    server_coordinates[guild_id][name] = coord_data
    
    # Create Google Maps link
    maps_link = f"https://www.google.com/maps?q={lat},{long}"
    
    embed = discord.Embed(
        title="📍 Location Saved!",
        description=f"**Location:** {name}\n**Coordinates:** {lat}, {long}",
        color=discord.Color.green(),
    )
    embed.add_field(name="Google Maps", value=f"[View on Maps]({maps_link})", inline=False)
    embed.set_footer(text=f"Saved by {ctx.author.display_name}")
    await ctx.reply(embed=embed)



@cords.command(name="list", aliases=["all", "show"])
async def cords_list(ctx):
    """List all saved locations."""
    guild_id = ctx.guild.id
    
    if guild_id not in server_coordinates or not server_coordinates[guild_id]:
        await ctx.reply("No locations saved yet! Use `!cords add <n> <lat>,<long>` to add some.")
        return
    
    coords = server_coordinates[guild_id]
    
    embed = discord.Embed(
        title=f"📍 All Saved Locations ({len(coords)})",
        color=discord.Color.blue(),
    )
    
    # Sort by name
    sorted_coords = sorted(coords.items(), key=lambda x: x[0].lower())
    
    for name, data in sorted_coords[:15]:  # Show first 15
        coord_str = f"**{data['lat']}, {data['long']}**"
        maps_link = f"https://www.google.com/maps?q={data['lat']},{data['long']}"
        embed.add_field(
            name=f"📌 {name}",
            value=f"{coord_str} • [Maps]({maps_link})",
            inline=False
        )
    
    if len(coords) > 15:
        embed.set_footer(text=f"Showing 15 of {len(coords)} locations. Use !cords <n> for details.")
    else:
        embed.set_footer(text="Use !cords <n> to view details")
    
    await ctx.reply(embed=embed)

@cords.command(name="delete", aliases=["remove", "del"])
async def cords_delete(ctx, *, name: str):
    """Delete saved location. Example: !cords delete kiri"""
    guild_id = ctx.guild.id
    
    if guild_id not in server_coordinates or not server_coordinates[guild_id]:
        await ctx.reply("No locations saved yet!")
        return
    
    # Case-insensitive search
    name_lower = name.lower()
    coords = server_coordinates[guild_id]
    
    matching = [k for k in coords.keys() if k.lower() == name_lower]
    
    if not matching:
        await ctx.reply(f"No location found for '{name}'.")
        return
    
    coord_name = matching[0]
    del server_coordinates[guild_id][coord_name]
    
    embed = discord.Embed(
        title="🗑️ Location Deleted",
        description=f"Removed location **{coord_name}**",
        color=discord.Color.red(),
    )
    embed.set_footer(text=f"Deleted by {ctx.author.display_name}")
    await ctx.reply(embed=embed)


# --- Gemini AI features ---

# Try these in order; first one that works is used (API model names vary by region/key)
GEMINI_MODEL_IDS = ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro")
GEMINI_TIMEOUT = 30
DISCORD_MAX_LEN = 1900  # Leave room for embed overhead

async def _gemini_generate(prompt: str, system_instruction: str = None) -> tuple[str | None, str | None]:
    """Call Gemini API in a thread; returns (text, error_message). One of them is None."""
    client = get_gemini_client()
    if not client:
        return None, "Gemini API key not set."
    last_error = None
    for model_id in GEMINI_MODEL_IDS:
        try:
            kwargs = {"model": model_id, "contents": prompt}
            if system_instruction:
                from google.genai import types
                kwargs["config"] = types.GenerateContentConfig(system_instruction=system_instruction)
            response = await asyncio.wait_for(
                asyncio.to_thread(client.models.generate_content, **kwargs),
                timeout=GEMINI_TIMEOUT,
            )
            text = getattr(response, "text", None)
            if not text and hasattr(response, "candidates") and response.candidates:
                parts = getattr(response.candidates[0].content, "parts", []) or []
                text = " ".join(getattr(p, "text", "") or "" for p in parts)
            if (text or "").strip():
                return (text or "").strip(), None
        except asyncio.TimeoutError:
            return None, "Gemini took too long to respond."
        except Exception as e:
            err_str = str(e)
            last_error = err_str[:200]
            # If model not found (404), try next model
            if "404" in err_str or "NOT_FOUND" in err_str or "not found" in err_str.lower():
                continue
            # Quota exceeded – don't try other models, show friendly message
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                return None, "Quota exceeded. Free tier resets daily – try again later, or check your plan at aistudio.google.com"
            return None, last_error
    return None, last_error or "No model responded."


def _truncate(text: str, max_len: int = DISCORD_MAX_LEN) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "…"


async def _safe_reply(ctx, content: str = None, embed: discord.Embed = None):
    """Reply to ctx; if that fails, try sending plain text."""
    try:
        if embed is not None:
            await ctx.reply(embed=embed)
        else:
            await ctx.reply(content or "Something went wrong.")
    except Exception:
        try:
            await ctx.reply(content or "Response too long or invalid.")
        except Exception:
            pass

@bot.command(name="ask", aliases=["gemini", "ai"])
async def ask(ctx, *, prompt: str):
    """Ask Gemini AI anything. Example: !ask Explain quantum computing in 3 sentences"""
    try:
        if not GEMINI_API_KEY:
            await ctx.reply("Gemini API is not configured. Add `GEMINI_API_KEY` to your `.env` file.")
            return
        await ctx.typing()
        text, err = await _gemini_generate(prompt)
        if not text:
            msg = err or "Could not get a response from Gemini."
            await ctx.reply(f"**Gemini error:** {msg[:500]}")
            return
        embed = discord.Embed(
            title="✨ Gemini",
            description=_truncate(text),
            color=discord.Color.blue(),
        )
        embed.add_field(name="You asked", value=_truncate(prompt, 200), inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.reply(embed=embed)
    except Exception as e:
        await _safe_reply(ctx, f"**Error:** {str(e)[:400]}")


@bot.command(name="summarize", aliases=["tldr"])
async def summarize(ctx, *, text: str):
    """Summarize any text with Gemini. Example: !summarize [paste long text]"""
    try:
        if not GEMINI_API_KEY:
            await ctx.reply("Gemini API is not configured. Add `GEMINI_API_KEY` to your `.env` file.")
            return
        if len(text) > 12000:
            await ctx.reply("Text is too long. Keep it under ~12,000 characters.")
            return
        await ctx.typing()
        prompt = f"Summarize the following in a clear, concise way (a few sentences or bullet points):\n\n{text}"
        result, err = await _gemini_generate(prompt)
        if not result:
            await ctx.reply(f"Could not summarize. {err or 'Try again.'}"[:500])
            return
        embed = discord.Embed(
            title="📋 Summary",
            description=_truncate(result),
            color=discord.Color.teal(),
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.reply(embed=embed)
    except Exception as e:
        await _safe_reply(ctx, f"**Error:** {str(e)[:400]}")


@bot.command(name="rewrite", aliases=["tone"])
async def rewrite(ctx, style: str, *, text: str):
    """Rewrite text in a different style. Example: !rewrite pirate Hello everyone"""
    try:
        if not GEMINI_API_KEY:
            await ctx.reply("Gemini API is not configured. Add `GEMINI_API_KEY` to your `.env` file.")
            return
        if len(text) > 4000:
            await ctx.reply("Text is too long. Keep it under ~4000 characters.")
            return
        await ctx.typing()
        prompt = f"Rewrite the following text in the style of: {style}. Keep the same meaning and length roughly similar. Only output the rewritten text, nothing else.\n\nText:\n{text}"
        result, err = await _gemini_generate(prompt)
        if not result:
            await ctx.reply(f"Could not rewrite. {err or 'Try again.'}"[:500])
            return
        embed = discord.Embed(
            title=f"✏️ Rewrite ({style})",
            description=_truncate(result),
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.reply(embed=embed)
    except Exception as e:
        await _safe_reply(ctx, f"**Error:** {str(e)[:400]}")


@bot.command(name="brainstorm", aliases=["ideas"])
async def brainstorm(ctx, *, topic: str):
    """Get creative ideas from Gemini. Example: !brainstorm names for a coffee shop"""
    try:
        if not GEMINI_API_KEY:
            await ctx.reply("Gemini API is not configured. Add `GEMINI_API_KEY` to your `.env` file.")
            return
        await ctx.typing()
        prompt = f"Give 5–7 creative, varied ideas for: {topic}. Format as a short bullet list. Be concise."
        result, err = await _gemini_generate(prompt)
        if not result:
            await ctx.reply(f"Could not brainstorm. {err or 'Try again.'}"[:500])
            return
        embed = discord.Embed(
            title=f"💡 Ideas: {_truncate(topic, 50)}",
            description=_truncate(result),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.reply(embed=embed)
    except Exception as e:
        await _safe_reply(ctx, f"**Error:** {str(e)[:400]}")


@bot.command(name="story", aliases=["storytime"])
async def story(ctx, *, prompt: str):
    """Generate a short creative story. Example: !story A robot who wants to be a chef"""
    try:
        if not GEMINI_API_KEY:
            await ctx.reply("Gemini API is not configured. Add `GEMINI_API_KEY` to your `.env` file.")
            return
        await ctx.typing()
        full_prompt = f"Write a creative short story (150-300 words) based on this prompt: {prompt}"
        result, err = await _gemini_generate(full_prompt)
        if not result:
            await ctx.reply(f"Could not generate story. {err or 'Try again.'}"[:500])
            return
        embed = discord.Embed(
            title=f"📖 Story: {_truncate(prompt, 50)}",
            description=_truncate(result),
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.reply(embed=embed)
    except Exception as e:
        await _safe_reply(ctx, f"**Error:** {str(e)[:400]}")


@bot.command(name="explain", aliases=["code"])
async def explain(ctx, *, code: str):
    """Explain what a piece of code does. Example: !explain for i in range(10): print(i)"""
    try:
        if not GEMINI_API_KEY:
            await ctx.reply("Gemini API is not configured. Add `GEMINI_API_KEY` to your `.env` file.")
            return
        if len(code) > 2000:
            await ctx.reply("Code is too long. Keep it under ~2000 characters.")
            return
        await ctx.typing()
        # Remove code block formatting if present
        code = code.strip()
        if code.startswith("```") and code.endswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1])
        
        prompt = f"Explain what this code does in simple terms, line by line if necessary:\n\n```\n{code}\n```"
        result, err = await _gemini_generate(prompt)
        if not result:
            await ctx.reply(f"Could not explain code. {err or 'Try again.'}"[:500])
            return
        embed = discord.Embed(
            title="💻 Code Explanation",
            description=_truncate(result),
            color=discord.Color.dark_blue(),
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.reply(embed=embed)
    except Exception as e:
        await _safe_reply(ctx, f"**Error:** {str(e)[:400]}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"Missing argument! Use `!cmds` to see command usage.")
        return
    await ctx.reply(f"Something went wrong: {error}")


if __name__ == "__main__":
    if not TOKEN:
        print("Error: Set DISCORD_TOKEN or BOT_TOKEN in your .env file.")
    else:
        bot.run(TOKEN)