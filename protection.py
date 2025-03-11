import discord
from discord.ext import commands
import datetime
import re
from collections import defaultdict
import os

TOKEN = os.getenv("TOKEN")


LOG_CHANNEL_ID = 1339590409021685802  

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
status_list = ["Protecting bitshop...."]

config = {
    "NEW_ACCOUNT_AGE_LIMIT": 5,  # Konto musi mieć min. X dni
    "RAID_JOIN_LIMIT": 15,  # Maksymalna liczba dołączeń w krótkim czasie
    "MUTE_DURATION": 600,  # Czas mute (sekundy)
    "WARN_THRESHOLD": 3,  # Po ilu ostrzeżeniach mute
    "BAN_THRESHOLD": 5  # Po ilu ostrzeżeniach ban
}

user_warnings = defaultdict(int)
user_joins = defaultdict(int)

BLOCKED_PATTERNS = [
    r"https?://\S+",  # Linki
    r"discord\.gg/\S+",  # Zaproszenia Discord
    r"(free nitro|nitro hack|gift nitro|steamgift|crypto boost|steam gift card)",  # Scam
    r"(kurw|chuj|jeban|pizd|huj|pizdy|pizda|kurwy|kurwa|jebany|jebana)",  # Przekleństwa
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"  # Adresy IP
]

async def log_violation(title, description, color, user):
    """ Wysyła logi do kanału w embedzie """
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.utcnow())
        embed.set_footer(text=f"ID: {user.id}")
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        await log_channel.send(embed=embed)

async def punish_user(user, reason):
    """ System ostrzeżeń i kar """
    user_warnings[user.id] += 1
    warnings = user_warnings[user.id]

    if warnings >= config["BAN_THRESHOLD"]:
        await user.ban(reason="Przekroczenie limitu ostrzeżeń")
        await log_violation("🚨 BAN!", f"**{user.mention} został zbanowany**", discord.Color.red(), user)
    elif warnings >= config["WARN_THRESHOLD"]:
        await user.timeout(datetime.timedelta(seconds=config["MUTE_DURATION"]), reason="Zbyt wiele ostrzeżeń.")
        await log_violation("⚠️ Mute!", f"**{user.mention} został wyciszony**", discord.Color.orange(), user)
    else:
        await log_violation("🔍 Ostrzeżenie!", f"**{user.mention} otrzymał ostrzeżenie**", discord.Color.yellow(), user)

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user.name} jest online!')

@bot.event
async def on_member_join(member):
    """ Ochrona przed nowymi kontami i rajdami """
    account_age = (datetime.datetime.utcnow() - member.created_at).days
    user_joins[member.id] += 1

    if account_age < config["NEW_ACCOUNT_AGE_LIMIT"]:
        await member.timeout(datetime.timedelta(seconds=config["MUTE_DURATION"]), reason="Nowe konto - ograniczenie pisania.")
        await log_violation("⚠️ Nowe konto!", f"**{member.mention} ma tylko {account_age} dni!**", discord.Color.orange(), member)

    if user_joins[member.id] > config["RAID_JOIN_LIMIT"]:
        await member.ban(reason="Podejrzane dołączanie (RAID)")
        await log_violation("🚨 RAID OCHRONA!", f"**{member.mention} próbował spamować dołączanie!**", discord.Color.red(), member)

@bot.event
async def on_message(message):
    """ Blokowanie linków, IP i przekleństw """
    if message.author.bot or message.author.guild_permissions.administrator:
        return

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, message.content, re.IGNORECASE):
            await message.delete()
            await punish_user(message.author, "Zakazane treści")
            await log_violation("🚨 Zakazane treści!", f"**Treść:** {message.content}", discord.Color.red(), message.author)
            return

    await bot.process_commands(message)

bot.run(TOKEN)
