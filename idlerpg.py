import discord, aiohttp, traceback
from discord.ext import commands
import sys, traceback, platform, aiopg, asyncio, idlerpgconfig
import datetime
from discord.ext.commands import BucketType

def get_prefix(bot, message):
	if not message.guild or bot.config.is_beta:
		return bot.config.global_prefix # Use global prefix in DMs and if the bot is beta
	try:
		return commands.when_mentioned_or(bot.all_prefixes[message.guild.id])(bot, message)
	except:
		return commands.when_mentioned_or(bot.config.global_prefix)(bot, message)
	return bot.config.global_prefix

bot = commands.AutoShardedBot(command_prefix=get_prefix, case_insensitive=True, description='The one and only IdleRPG bot for discord')
bot.version = "2.8 stable"
bot.remove_command("help")
bot.config = idlerpgconfig

bot.BASE_URL = "https://idlerpg.fun"

async def create_pool():
	credentials = bot.config.database
	connstring = f"dbname={credentials[0]} user={credentials[1]} password={credentials[2]} host={credentials[3]} port=5432"
	pool = await aiopg.create_pool(connstring)
	return pool

async def start_bot():
	bot.session = aiohttp.ClientSession(loop=bot.loop)
	pool = await create_pool()
	bot.pool = pool
	bot.all_prefixes = {}
	async with bot.pool.acquire() as conn:
		async with conn.cursor() as cur:
			await cur.execute("SELECT id, prefix FROM server;")
			async for row in cur:
				bot.all_prefixes[int(row[0])] = row[1]
	await bot.start(bot.config.token)

map = commands.CooldownMapping.from_cooldown(1, 3, BucketType.user)

@bot.check_once
async def global_cooldown(ctx: commands.Context):
	bucket = map.get_bucket(ctx.message)
	retry_after = bucket.update_rate_limit()

	if retry_after:
		raise commands.CommandOnCooldown(bucket, retry_after)
	else:
		return True

async def handle_vote(bot, msg):
	user = int(msg.content.split("|")[1])
	userobj = bot.get_user(user)
	async with bot.pool.acquire() as conn:
		async with conn.cursor() as cur:
			await cur.execute('UPDATE profile SET crates=crates+1 WHERE "user"=%s;', (user,))
	await userobj.send("Thanks for voting! You have been given a crate!")

@bot.event
async def on_message(message):
	if message.author.discriminator == "0000" and message.channel.id == bot.config.upvote_channel and not bot.config.is_beta:
		await handle_vote(bot, message)
	if message.author.bot:
		return
	await bot.process_commands(message)

@bot.event
async def on_ready():
	print(f"Logged in as {bot.user.name} (ID: {bot.user.id}) | Connected to {len(bot.guilds)} servers | Connected to {len(bot.users)} users")
	print("--------")
	print(f"Current Discord.py Version: {discord.__version__} | Current Python Version: {platform.python_version()}")
	print("--------")
	print(f"You are running IdleRPG Bot {bot.version}")
	owner = (await bot.application_info()).owner
	print(f"Created by {owner}")

if __name__ == '__main__':
	for extension in bot.config.initial_extensions:
		try:
			bot.load_extension(extension)
		except Exception as e:
			print(f'Failed to load extension {extension}.', file=sys.stderr)
			traceback.print_exc()
	loop = asyncio.get_event_loop()
	loop.run_until_complete(start_bot())
