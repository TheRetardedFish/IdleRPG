from datetime import date, timedelta
import discord, os, random, psutil, platform, asyncio
import pkg_resources as pkg
from discord.ext import commands
from discord.ext.commands import BucketType
from cogs.help import chunks
import time

class Miscellaneous:

	def __init__(self, bot):
		self.bot = bot

	@commands.cooldown(1, 86400, BucketType.user)
	@commands.command(description="Get $50 per day.")
	async def daily(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('UPDATE profile SET money=money+50 WHERE "user"=%s;', (ctx.author.id,))
				await ctx.send("You received your daily **$50**!")

	@commands.command(description="Bot's ping.")
	async def ping(self, ctx):
		embed = discord.Embed(title="Pong!", description=f"My current latency is {round(self.bot.latency*1000, 2)}ms", color=0xf1c60c)
		await ctx.send(embed=embed)

	@commands.command(aliases=["donate"], description="Support us!")
	async def patreon(self, ctx):
		await ctx.send(f"This bot has it's own patreon page.\n\n**Why should I donate?**\nThis bot is currently on {len(self.bot.guilds)} servers, and it is growing" \
		" fast.\nHosting this bot for all users is not easy and costs money.\nIf you want to continue using the bot or just help us, please donate a small amount.\nEven"\
		" $1 can help us.\n**Thank you!**\n\n<https://patreon.com/idlerpg>")

	@commands.command(aliases=["invite"], description="Credits!")
	async def credits(self, ctx):
		await ctx.send(f"You are running version **{self.bot.version}** by Adrian.\nInvite me! " \
		f"<https://discordapp.com/oauth2/authorize?client_id={bot.user.id}&scope=bot&permissions=8>")

	@commands.command(description="Get some help!")
	async def support(self, ctx):
		await ctx.send("Got problems or feature requests? Join the support server:\nhttps://discord.gg/MSBatf6")

	@commands.command(aliases=["downtime"], description="Is the bot down?")
	async def down(self, ctx):
		owner = (await self.bot.application_info()).owner
		await ctx.send(f"If this bot is down, please PM me: `{owner}`")

	@commands.command(description="Some statistics.")
	async def stats(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT COUNT(*) FROM profile;')
				characters = await cur.fetchone()
				await cur.execute('SELECT COUNT(*) FROM allitems;')
				items = await cur.fetchone()
		linecount = 0
		with open("idlerpg.py", encoding="utf-8") as f:
			linecount += len(f.readlines())
		for afile in os.listdir("cogs"):
			if os.path.isdir(afile) or not afile.endswith(".py"):
				continue
			with open(f"cogs/{afile}", encoding="utf-8") as f:
				linecount += len(f.readlines())
		total_online = len({m.id for m in self.bot.get_all_members() if m.status is discord.Status.online})
		total_idle = len({m.id for m in self.bot.get_all_members() if m.status is discord.Status.idle})
		total_dnd = len({m.id for m in self.bot.get_all_members() if m.status is discord.Status.dnd})
		total_offline = len({m.id for m in self.bot.get_all_members() if m.status is discord.Status.offline})
		d0 = date(2018, 3, 17)
		d1 = date.today()
		delta = d1 - d0
		myhours = delta.days*3
		sysinfo = platform.linux_distribution()
		owner = (await self.bot.application_info()).owner
		embed = discord.Embed(title="IdleRPG Statistics", colour=0xb8bbff, url=self.bot.BASE_URL, description="Official Support Server Invite: https://discord.gg/MSBatf6")
		embed.set_thumbnail(url=self.bot.user.avatar_url)
		embed.set_footer(text=f"IdleRPG {self.bot.version} | By {owner}", icon_url=self.bot.user.avatar_url)
		embed.add_field(name="General Statistics", value=f"<:online:313956277808005120>{total_online}<:away:313956277220802560>{total_idle}<:dnd:313956276893646850>" \
		 f"{total_dnd}<:offline:313956277237710868>{total_offline}", inline=False)
		embed.add_field(name="Hosting Statistics", value=f"CPU Usage: **{psutil.cpu_percent()}%**\nRAM Usage: **{psutil.virtual_memory().percent}%**\nPython Version" \
		 f" **{platform.python_version()}** <:python:445247273065250817>\ndiscord.py Version **{pkg.get_distribution('discord.py').version}**\nOperating System: " \
		 f"**{sysinfo[0].title()} {sysinfo[1].title()}**", inline=False)
		embed.add_field(name="Bot Statistics", value=f"Code lines written: **{linecount}**\nShards: **{len(self.bot.shards)}**\nServers: **{len(self.bot.guilds)}**\nMembers: " \
		 f"**{len(self.bot.users)}**\nChannels: **{len(set(self.bot.get_all_channels()))}**\nCharacters: **{characters[0]}**\nItems: **{items[0]}**\nAverage hours of work: " \
		 f"**{myhours}**", inline=False)
		await ctx.send(embed=embed)

	@commands.command(description="Rolls a random number. The only argument defines the maximum result")
	async def roll(self, ctx, maximum: int):
		await ctx.send(f":1234: You rolled **{random.randint(0,maximum)}**, {ctx.author.mention}!")

	@commands.command(description="Latest updates.")
	async def changelog(self, ctx):
		await ctx.send("""
**Version 2.8 released!** <:idlerpg:453946311524220949> 

**What's new?**
- `$edgy`, `$invert`, `$oil` -> Image commands for avatar fun
- `$guild kick` to kick people from your guild
- Active adventures! `$activeadventure` -> Item gain, but with cooldown and pretty hard to solve
- We now have a wiki and a new website design! <https://wiki.idlerpg.fun> <https://idlerpg.fun>
- For some reason there is a user specific cooldown of 3 seconds now to avoid bot crashes due to spamming
- `$p2` is depracted and was removed
- `$claim` was removed, the bot now instantly reacts to your votes
- Added transparency to the profile image, patrons may have to regenerate
- You now have to vote for `$skip` and `$stop`
- Guild adventures to get money for the guild bank: `$guild adventure` and `$guild status`
- `$trader` to buy premade items once per hour

**What's fixed?**
- `$delete` and the admin command had database issues which are fixed
- The whole bot used too many database connections, reduced that heavily and will do that more often in the future

**What will come up soon?**
- I will rewrite the bot when I have enough time and also switch to multiple processes, this may take a few weeks
- Some community suggestions I didn't add yet (got many on my to-do list)
""")

	@commands.has_permissions(manage_messages=True)
	@commands.command(description="Clears X messages.")
	async def clear(self, ctx, num: int, target: discord.Member=None):
		if num > 500 or num < 0:
			await ctx.send("Invalid amount. Maximum is 500.")
			return
		def msgcheck(amsg):
			if target:
				return amsg.author.id==target.id
			return True
		await ctx.channel.purge(limit=num, check=msgcheck)
		await ctx.send(f'👍 Deleted **{num}** messages for you.', delete_after=10)

	@commands.command(name="8ball", description="A usual 8ball...")
	async def _ball(self, ctx, *, question: str):
		results = ["It is certain"," It is decidedly so","Without a doubt","Yes, definitely","You may rely on it","As I see it, yes"," Most likely","Outlook good","Yes","Signs point to yes"," Reply hazy try again","Ask again later","Better not tell you now","Cannot predict now","Concentrate and ask again","Don't count on it","My reply is no","My sources say no","Outlook not so good","Very doubtful"]
		await ctx.send(f"The :8ball: says: **{random.choice(results)}**.")

	@commands.command(aliases=["say"], description="Echo! Echo....")
	async def echo(self, ctx, *, shout: str):
		try:
			await ctx.message.delete()
		except:
			pass
		shout = await commands.clean_content().convert(ctx, shout)
		await ctx.send(f"{shout}")

	@commands.command(description="A usual guess...")
	async def choose(sef, ctx, *results: commands.clean_content):
		await ctx.send(f"My choice is: **{random.choice(results)}**.")

	@commands.command(description="A usual love test...")
	async def love(self, ctx, first: discord.Member, second: discord.Member):
		msg = await ctx.send(embed=discord.Embed(description=f"Calculating Love for {first.mention} and {second.mention}...", color=0xff0000))
		await asyncio.sleep(5)
		random.seed(int(str(first.id)+str(second.id)))
		if first == second:
			love = 100.00
		else:
			love = random.randint(1, 10000)/100
		embed=discord.Embed(title="Love Calculation", description=f"Love for {first.mention} and {second.mention} is at **{love}%**! ❤", color=0xff0000)
		await msg.edit(embed=embed)

	@commands.command(description="Fancy Text")
	async def fancy(self, ctx, *, text: str):
		nums = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
		newtext = ""
		for letter in text:
			if letter.lower() in list(map(chr, range(97, 123))):
				newtext += f":regional_indicator_{letter.lower()}:"
			elif letter in [str(anum) for anum in range(10)]:
				newtext += f":{nums[int(letter)]}:"
			else:
				newtext += letter
		await ctx.send(newtext)

	@commands.command(description="Memes :)")
	async def meme(self, ctx):
		async with self.bot.session.get(f"https://some-random-api.ml/meme?lol={random.randint(1,1000000)}") as resp:
			await ctx.send(embed=discord.Embed(color=0x0a00ff).set_image(url=(await resp.json())["url"]))

	@commands.command(description="Roleplay dice. Uses ndx format.")
	async def dice(self, ctx, type: str):
		type = type.lower().split("d")
		if len(type)!=2:
			await ctx.send("Use the ndx format.")
			return
		try:
			type[0] = int(type[0])
			type[1] = int(type[1])
			if type[0] > 100:
				await ctx.send('Too many dices.')
				return
		except:
			await ctx.send("Use the ndx format.")
		results = []
		for i in range(type[0]):
			results.append(random.randint(1, type[1]))
		sumall = 0
		for i in results:
			sumall += i
		average = sumall / len(results)
		nl = "\n"
		results = [str(result) for result in results]
		await ctx.send(f"```Sum: {sumall}\nAverage: {average}\nResults:\n{nl.join(results)}```")

	@commands.command(description="What am I called where?")
	async def randomname(self, ctx):
		g = random.choice([g for g in self.bot.guilds if g.me.display_name != self.bot.user.name])
		info =  (g.me.display_name, g.name)
		await ctx.send(f"In **{info[1]}** I am called **{info[0]}**.")

	@commands.command(description="Cats!")
	async def cat(self, ctx):
		await ctx.send(embed=discord.Embed(title="Meow!", color=ctx.author.color.value).set_image(url=f"http://thecatapi.com/api/images/get?results_per_page=1&anticache={random.randint(1,10000)}"))

	@commands.command(description="Dogs!")
	async def dog(self, ctx):
		async with self.bot.session.get("https://api.thedogapi.com/v1/images/search") as r:
			res = await r.json()
		await ctx.send(embed=discord.Embed(title="Wouff!", color=ctx.author.color.value).set_image(url=res[0]['url']))

	@commands.command(description="Bot uptime.")
	async def uptime(self, ctx):
		p = psutil.Process(os.getpid())
		secs = int(time.time() - p.create_time())
		await ctx.send(f"I am online for **{str(timedelta(seconds=secs))}**.")

	
	@commands.command(hidden=True)
	async def easteregg(self, ctx):
		await ctx.send("Find it!")

	@commands.command(description="Support server notifications.")
	async def notifyme(self, ctx):
		if not ctx.guild.id==430017996304678923:
			return await ctx.send("Support Server Only")
		role = [r for r in ctx.guild.roles if r.name=="Notify"][0]
		await ctx.author.add_roles(role)
		await ctx.send("Notifications triggered.")

	@commands.command(description="Turn off support server notifications.")
	async def unnotifyme(self, ctx):
		if not ctx.guild.id==430017996304678923:
			return await ctx.send("Support Server Only")
		role = [r for r in ctx.guild.roles if r.name=="Notify"][0]
		await ctx.author.remove_roles(role)
		await ctx.send("Notifications disabled.")

	@commands.command(description="Gives a cookie to a user.")
	@commands.guild_only()
	@commands.cooldown(1.0, 20.0, BucketType.user)
	async def cookie(self, ctx, user: discord.Member):
		await ctx.send(f"**{user.display_name}**, you've been given a cookie by **{ctx.author.display_name}**. :cookie:")

	@commands.command(description="Ice Cream!", aliases=["ice-cream"])
	async def ice(self, ctx, other:discord.Member):
		await ctx.send(f"{other.mention}, here is your ice: :ice_cream:!")

	@commands.command(description="Traven!")
	async def traven(self, ctx):
		await ctx.send(random.choice(["He is great!", "He is an asshole!", "Maybe he is cool.", "I like him", "I don't like him.", "He's a god!"]))

def setup(bot):
	bot.add_cog(Miscellaneous(bot))
