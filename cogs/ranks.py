import discord
from discord.ext import commands
import cogs.rpgtools as rpgtools

class Ranks:

	def __init__(self, bot):
		self.bot = bot

	@commands.command(description="Shows the richest players. Maximum 10.")
	async def richest(self, ctx):
		await ctx.trigger_typing()
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT "user", "name", "money" from profile ORDER BY "money" DESC LIMIT 10;')
				except:
					await ctx.send("An error occured when fetching the data.")
				ret = []
				async for row in cur:
					ret.append(row)
		if ret==[]:
			await ctx.send("No character have been created yet. Use `{ctx.prefix}create` to be the first one!")
		else:
			result = ""
			for profile in ret:
				number = ret.index(profile)+1
				charname = await rpgtools.lookup(self.bot, profile[0])
				pstring = f"{number}. {profile[1]}, a character by `{charname}` with **${profile[2]}**\n"
				result += pstring
			result = discord.Embed(title="The Richest Players", description=result, colour=0xe7ca01)
			await ctx.send(embed=result)

	@commands.command(aliases=["best", "high", "top"], description="Shows the best players sorted by XP. Maximum 10.")
	async def highscore(self, ctx):
		await ctx.trigger_typing()
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT "user", "name", "xp" from profile ORDER BY "xp" DESC LIMIT 10;')
				except:
					await ctx.send("An error occured when fetching the data.")
				ret = []
				async for row in cur:
					ret.append(row)
		if ret==[]:
			await ctx.send("No character have been created yet. Use `{ctx.prefix}create` to be the first one!")
		else:
			result = ""
			for profile in ret:
				number = ret.index(profile)+1
				charname = await rpgtools.lookup(self.bot, profile[0])
				pstring = f"{number}. {profile[1]}, a character by `{charname}` with Level **{rpgtools.xptolevel(profile[2])}** (**{profile[2]}** XP)\n"
				result += pstring
			result = discord.Embed(title="The Best Players", description=result, colour=0xe7ca01)
			await ctx.send(embed=result)

	@commands.command(aliases=["pvp", "battles"], description="Shows the best PvP players. Maximum 10.")
	async def pvpstats(self, ctx):
		await ctx.trigger_typing()
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT "user", "name", "pvpwins" from profile ORDER BY "pvpwins" DESC LIMIT 10;')
				except:
					await ctx.send("An error occured when fetching the data.")
				ret = []
				async for row in cur:
					ret.append(row)
		if ret==[]:
			await ctx.send("No character have been created yet. Use `{ctx.prefix}create` to be the first one!")
		else:
			result = ""
			for profile in ret:
				number = ret.index(profile)+1
				charname = await rpgtools.lookup(self.bot, profile[0])
				pstring = f"{number}. {profile[1]}, a character by `{charname}` with **{profile[2]}** wins\n"
				result += pstring
			result = discord.Embed(title="The Best PvPers", description=result, colour=0xe7ca01)
			await ctx.send(embed=result)



def setup(bot):
	bot.add_cog(Ranks(bot))

