import discord, traceback, operator
from discord.ext import commands

def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(l), n):
		yield l[i:i + n]

async def makeembed(bot, pages, thecurrentpage):
	mymax = len(pages)+1
	if thecurrentpage is not 0:
		embed = discord.Embed(title="IdleRPG Help", colour=discord.Colour(0xffbc00), url=bot.BASE_URL, description=f"**{pages[thecurrentpage-1][0]} Commands**")
		embed.set_footer(text=f"IdleRPG Version {bot.version} | Page {thecurrentpage+1} of {mymax}", icon_url=bot.user.avatar_url)
		for acommand in pages[thecurrentpage-1]:
			if acommand == pages[thecurrentpage-1][0]:
				continue
			mydesc = acommand.description
			if mydesc is None or mydesc == "":
				mydesc = "No description set"
			embed.add_field(name=f"{acommand.signature}", value=mydesc, inline=False)
		return embed
	else:
		embed = discord.Embed(title="IdleRPG Help", colour=discord.Colour(0xffbc00), url=bot.BASE_URL, description="**Welcome to the IdleRPG help. Use the arrows to move.\nFor more help, join the support server at https://discord.gg/MSBatf6.**")
		embed.set_image(url=f"{bot.BASE_URL}/IdleRPG.png")
		embed.set_footer(text=f"IdleRPG Version {bot.version}", icon_url=bot.user.avatar_url)
		return embed


class Help:

	def __init__(self, bot):
		self.bot = bot

	@commands.command(description="Sends a link to the official documentation.", aliases=["docs"])
	async def documentation(self, ctx):
		await ctx.send(f"<:blackcheck:441826948919066625> **Check {self.bot.BASE_URL} for a list of commands**")

	@commands.command(description="Tutorial link.")
	async def tutorial(self, ctx):
		await ctx.send(f"<:blackcheck:441826948919066625> **Check {self.bot.BASE_URL}/tutorial-faq for a tutorial**")

	@commands.command(description="Link to the FAQ.")
	async def faq(self, ctx):
		await ctx.send(f"<:blackcheck:441826948919066625> **Check {self.bot.BASE_URL}/tutorial-faq for the official FAQ**")

	@commands.command(description="Need help? Gotcha!")
	async def helpme(self, ctx, *, text:str):
		try:
			inv = await ctx.channel.create_invite()
		except:
			return await ctx.send("Error when creating Invite.")
		c = self.bot.get_channel(453551307249418254)
		em = discord.Embed(title="Help Request", colour=0xff0000)
		em.add_field(name="Requested by", value=f"{ctx.author}")
		em.add_field(name="Requested in", value=f"#{ctx.channel}")
		em.add_field(name="Content", value=text)
		em.add_field(name="Invite", value=inv)

		await c.send(embed=em)
		await ctx.send("Support team has been notified and will join as soon as possible!")

	@commands.command(description="Get some help.")
	async def help(self, ctx, command=None):
		if command is not None:
			pages = await ctx.bot.formatter.format_help_for(ctx, self.bot.get_command(str(command)))
			if not pages[0].split("\n")[2].endswith("for more info on a command."):
				for page in pages:
					await ctx.send(page)
			else:
				await ctx.send(f"```There is no command named {command}.```")
			return

		commands = []
		for cog in self.bot.cogs:
			if cog == "Admin" or cog == "Owner" or cog == "Chess":
				continue
			for l in list(chunks(list(self.bot.get_cog_commands(cog)), 10)):
				commands.append([l[0].cog_name]+l)

		maxpages = len(commands)+1
		currentpage = 0
		browsing = True
		myembed = await makeembed(self.bot, commands, currentpage)
		msg = await ctx.send(embed=myembed)
		await msg.add_reaction("\U000023ee")
		await msg.add_reaction("\U000025c0")
		await msg.add_reaction("\U000025b6")
		await msg.add_reaction("\U000023ed")
		await msg.add_reaction("\U0001f522")
		def reactioncheck(reaction, user):
			return str(reaction.emoji) in ["\U000025c0","\U000025b6", "\U000023ee", "\U000023ed", "\U0001f522"] and reaction.message.id==msg.id and user.id==ctx.author.id
		def msgcheck(amsg):
			return amsg.channel == ctx.channel and not amsg.author.bot
		while browsing:
			try:
				reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reactioncheck)
				if reaction.emoji == "\U000025c0":
					if currentpage == 0:
						pass
					else:
						currentpage -= 1
						myembed = await makeembed(self.bot, commands, currentpage)
						await msg.edit(embed=myembed)
						try:
							await msg.remove_reaction(reaction.emoji, user)
						except:
							pass
				elif reaction.emoji == "\U000025b6":
					if currentpage == maxpages-1:
						pass
					else:
						currentpage += 1
						myembed = await makeembed(self.bot, commands, currentpage)
						await msg.edit(embed=myembed)
						try:
							await msg.remove_reaction(reaction.emoji, user)
						except:
							pass
				elif reaction.emoji == "\U000023ed":
					currentpage = maxpages-1
					myembed = await makeembed(self.bot, commands, currentpage)
					await msg.edit(embed=myembed)
					try:
						await msg.remove_reaction(reaction.emoji, user)
					except:
						pass
				elif reaction.emoji == "\U000023ee":
					currentpage = 0
					myembed = await makeembed(self.bot, commands, currentpage)
					await msg.edit(embed=myembed)
					try:
						await msg.remove_reaction(reaction.emoji, user)
					except:
						pass
				elif reaction.emoji == "\U0001f522":
					question = await ctx.send(f"Enter a page number from `1` to `{maxpages}`")
					num = await self.bot.wait_for('message', timeout=10, check=msgcheck)
					if num is not None:
						try:
							num2 = int(num.content)
							if num2 >= 1 and num2 <= maxpages:
								currentpage = num2-1
								myembed = await makeembed(self.bot, commands, currentpage)
								await msg.edit(embed=myembed)
								try:
									await num.delete()
								except:
									pass
							else:
								mymsg = await ctx.send(f"Must be between `1` and `{maxpages}`.", delete_after=2)
								try:
									await num.delete()
								except:
									pass
						except:
							mymsg = await ctx.send("That is no number!", delete_after=2)
					await question.delete()
					try:
						await msg.remove_reaction(reaction.emoji, user)
					except:
						pass
			except:
				browsing = False
				try:
					await msg.clear_reactions()
				except:
					pass
				finally:
					break







def setup(bot):
	bot.add_cog(Help(bot))
