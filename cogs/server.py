import discord
from discord.ext import commands
from cogs.help import chunks

def getguilds(bot, user):
	return [guild for guild in bot.guilds if user in guild.members]

class Server:

	def __init__(self, bot):
		self.bot = bot

	@commands.guild_only()
	@commands.command(description="Prints out some information about this server.", aliases=['server'])
	async def serverinfo(self, ctx):
		if ctx.guild.icon_url is not "":
			urltext = f"[Link <:external_link:429288989560930314>]({ctx.guild.icon_url})"
		else:
			urltext = "`No icon has been set yet!`"
		em = discord.Embed(title='Server Information', description='Compact information about this server', colour=0xDEADBF)
		em.add_field(name="Information", value=f"Server: `{str(ctx.guild)}`\nServer Region: `{ctx.guild.region}`\nMembers Total: `{ctx.guild.member_count}`\nID: `{ctx.guild.id}`\nIcon: {urltext}\nOwner: {ctx.guild.owner.mention}\nServer created at: `{ctx.guild.created_at.__format__('%A %d. %B %Y at %H:%M:%S')}`")
		em.add_field(name="Roles", value=f"{', '.join([role.name for role in ctx.guild.roles])}")
		em.add_field(name="Shard", value=f"`{ctx.guild.shard_id + 1}` of `{len(self.bot.shards)}`")
		em.set_thumbnail(url=ctx.guild.icon_url)
		await ctx.send(embed=em)

	@commands.guild_only()
	@commands.command(description="Change the settings.")
	async def settings(self, ctx, setting: str="None", value="None"):
		action = setting.lower()
		if action != "prefix" and action != "unknown":
			await ctx.send(f"Use `{ctx.prefix}settings prefix` or `{ctx.prefix}settings unknown` to change the settings.")
			return
		if not ctx.author.guild_permissions.manage_guild:
			await ctx.send("You need to have `Manage Server` permissions to do this.")
			return
		if action == "prefix" and type(value) != str:
			await ctx.send("Enter a valid prefix.")
			return
		if action == "prefix" and len(value) > 10:
			await ctx.send("Prefix too long.")
			return
		if action == "unknown":
			if value == "True":
				value = True
			elif value == "False":
				value = False
			else:
				await ctx.send("Enter `True` or `False` as the new value.")
				return
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM server WHERE "id"=%s;', (ctx.guild.id,))
				isserver = []
				async for row in cur:
					isserver.append(row)
				if isserver == []:
					if action == "prefix":
						if value == "None":
							await ctx.send("Please specify a prefix.")
							return
						await cur.execute('INSERT INTO server VALUES (%s, %s, %s);', (ctx.guild.id, value, True))
						self.bot.all_prefixes[ctx.guild.id] = value
					else:
						await cur.execute('INSERT INTO server VALUES (%s, %s, %s);', (ctx.guild.id, "$", value))
				else:
					if action == "prefix":
						if value == "None":
							await ctx.send("Please specify a prefix.")
							return
						await cur.execute('UPDATE server SET "prefix"=%s WHERE "id"=%s;', (value, ctx.guild.id))
						self.bot.all_prefixes[ctx.guild.id] = value
					else:
						await cur.execute('UPDATE server SET "unknown"=%s WHERE "id"=%s;', (value, ctx.guild.id))
		await ctx.send("Successfully updated the server settings.")

	@commands.command(description='Information about a user.', aliases=["user", "member", "memberinfo"])
	async def userinfo(self, ctx, member:discord.Member=None):
		ticks={"True":"<:check:314349398811475968>", "False":"<:xmark:314349398824058880>"}
		statuses={"online":"<:online:313956277808005120>", "idle":"<:away:313956277220802560>", "dnd":"<:dnd:313956276893646850>", "offline":"<:offline:313956277237710868>"}
		nl = "\n"
		auser=member
		if not auser:
			auser = ctx.author
		shared = getguilds(self.bot, auser)
		embed = discord.Embed(title=f"{auser}", description=f"`Joined at`: {auser.joined_at}\n`Status...`: {statuses[str(auser.status)]}{str(auser.status).capitalize()}\n`Top Role.`: {auser.top_role.name}\n`Roles....`: {', '.join([role.name for role in auser.roles])}\n`Game.....`: {auser.activity if auser.activity else 'No Game Playing'}", color=auser.color.value)
		embed.add_field(name="Shared Servers", value=f"**{len(shared)}**\n{nl.join([guild.name for guild in shared])}")
		embed.set_thumbnail(url=auser.avatar_url)
		msg = await ctx.send(embed=embed)
		await msg.add_reaction("\U000025c0")
		await msg.add_reaction("\U000025b6")
		def reactioncheck(reaction, user):
			return str(reaction.emoji) in ["\U000025c0","\U000025b6"] and reaction.message.id==msg.id and user.id==ctx.author.id
		waiting = True
		while waiting:
			try:
				reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reactioncheck)
				if reaction.emoji == "\U000025b6":
					em = discord.Embed(title="Permissions", description=f"{nl.join(['`'+value[0].replace('_', ' ').title().ljust(21, '.')+'`'+': '+ticks[str(value[1])] for value in auser.guild_permissions])}", color=auser.color.value).set_thumbnail(url=auser.avatar_url)
					await msg.edit(embed=em)
				elif reaction.emoji == "\U000025c0":
					embed = discord.Embed(title=f"{auser}", description=f"`Joined at`: {auser.joined_at}\n`Status...`: {statuses[str(auser.status)]}{str(auser.status).capitalize()}\n`Top Role.`: {auser.top_role.name}\n`Roles....`: {', '.join([role.name for role in auser.roles])}\n`Game.....`: {auser.activity if auser.activity else 'No Game Playing'}", color=auser.color.value)
					embed.add_field(name="Shared Servers", value=f"**{len(shared)}**\n{nl.join([guild.name for guild in shared])}")
					embed.set_thumbnail(url=auser.avatar_url)
					await msg.edit(embed=embed)
				try:
					await msg.remove_reaction(reaction.emoji, user)
				except:
					pass
			except:
				waiting = False
				try:
					await msg.clear_reactions()
				except:
					pass
			finally:
				break






	@commands.command(description="See your prefix.")
	async def prefix(self, ctx):
		try:
			await ctx.send(f"The prefix for server **{ctx.guild.name}** is `{self.bot.all_prefixes[ctx.guild.id]}`.\n\n`{ctx.prefix}settings prefix` changes it.")
		except:
			await ctx.send(f"The prefix for server **{ctx.guild.name}** is `$`.\n\n`{ctx.prefix}settings prefix` changes it.")

	@commands.command(description="Who uses your discriminator?")
	async def discrim(self, ctx, discrim:str):
		if len(discrim)!=4:
			await ctx.send("A discrim is 4 numbers.")
			return
		all = list(chunks([str(user) for user in self.bot.users if user.discriminator==discrim], 54))
		for i in all:
			await ctx.send("```"+"\n".join(i)+"```")

	@commands.command(description="Steal Avatars.")
	async def avatar(self, ctx, target:discord.Member):
		await ctx.send(embed=discord.Embed(title="Download Link", url=target.avatar_url, color=target.color).set_image(url=target.avatar_url))


def setup(bot):
	bot.add_cog(Server(bot))


