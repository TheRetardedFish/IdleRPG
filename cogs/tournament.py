import discord
from discord.ext import commands
from cogs.help import chunks
import math
import random
import asyncio
from discord.ext.commands import BucketType

def is_battle_owner():
	def predicate(ctx):
		member = ctx.bot.get_guild(430017996304678923).get_member(ctx.author.id)  # cross server stuff
		if not member:
			return False
		return discord.utils.get(member.roles, name='Battle Owner') is not None
	return commands.check(predicate)

def hypesquad():
	def predicate(ctx):
		member = ctx.bot.get_guild(430017996304678923).get_member(ctx.author.id)
		if not member:
			return False
		return discord.utils.get(member.roles, name='Hypesquad') is not None
	return commands.check(predicate)

class Tournament:

	def __init__(self, bot):
		self.bot = bot


	@commands.command(description="Take part in a support server battle.")
	async def signup(self, ctx):
		await ctx.author.add_roles(discord.utils.get(ctx.guild.roles, name="Battle Participant"))
		await ctx.send("Welcome to the battles!")

	@is_battle_owner()
	@commands.command(description="[Battle Owner Only] Reset battle participants.")
	async def newbattle(self, ctx):
		for member in ctx.bot.get_guild(430017996304678923).members:
			try:
				await member.remove_roles(discord.utils.get(member.roles, name='Battle Participant'))
				await ctx.send(f"Removed it from {member}.")
			except:
				pass
		await ctx.send("All old participants have been removed.")

	@commands.cooldown(1,1800,BucketType.user)
	@commands.command(description="Start a new tournament with unlimited participants.")
	async def tournament(self, ctx, prize:int):
		if prize<0:
			return await ctx.send("Don't scam!")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
				money = await cur.fetchone()
				if not money:
					return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to get started.")
				elif money[0]<prize:
					return await ctx.send("You can't pay the tournament prize.")
				await ctx.send(f"{ctx.author.mention} started a tournament! Free entries, prize is **${prize}**! Type `tournament join @{ctx.author}` to join!")
				participants = [ctx.author]
				acceptingentries = True

				def simplecheck(msg):
					return (msg.content.strip().lower() == f"tournament join <@{ctx.author.id}>" or msg.content.strip().lower() == f"tournament join <@!{ctx.author.id}>") and msg.author!=ctx.author and msg.author not in participants

				async def has_char(user):
					await cur.execute('SELECT * FROM profile WHERE "user"=%s;', (user.id,))
					return await cur.fetchone() is not None

				while acceptingentries:
					try:
						res = await self.bot.wait_for('message', timeout=30, check=simplecheck)
						if has_char(res.author):
							participants.append(res.author)
							await ctx.send(f"{res.author.mention} joined the tournament.")
						else:
							await ctx.send(f"You don't have a character, {res.author.mention}.")
						continue
					except:
						acceptingentries = False
						if len(participants) < 2:
							return await ctx.send(f"Noone joined your tournament, {ctx.author.mention}.")
						break
				toremove = 2 ** math.floor(math.log2(len(participants)))
				if toremove != len(participants):
					await ctx.send(f"There are **{len(participants)}** entries, due to the fact we need a playable tournament, the last **{len(participants) - toremove}** have been removed.")
					participants = participants[:-(len(participants)-toremove)]
				else:
					await ctx.send(f"Tournament started with **{toremove}** entries.")
				remain = participants
				while len(remain) > 1:
					random.shuffle(remain)
					matches = list(chunks(remain, 2))
					for match in matches:
						await ctx.send(f"{match[0].mention} vs {match[1].mention}")
						await asyncio.sleep(2)
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (match[0].id,))
						sword1 = await cur.fetchone()
						try:
							sw1 = sword1[5]
						except:
							sw1 = 0
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (match[0].id,))
						shield1 = await cur.fetchone()
						try:
							sh1 = shield1[6]
						except:
							sh1 = 0
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (match[1].id,))
						sword2 = await cur.fetchone()
						try:
							sw2 = sword2[5]
						except:
							sw2 = 0
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (match[1].id,))
						shield2 = await cur.fetchone()
						try:
							sh2 = shield2[6]
						except:
							sh2 = 0
						val1 = sw1 + sh1 + random.randint(1, 7)
						val2 = sw2 + sh2 + random.randint(1, 7)
						if val1>val2:
							winner = match[0]
							looser = match[1]
						elif val2>val1:
							winner = match[1]
							looser = match[0]
						remain.remove(looser)
						await ctx.send(f"Winner of this match is {winner.mention}!")
						await asyncio.sleep(2)

					await ctx.send("Round Done!")
				msg = await ctx.send(f"Tournament ended! The winner is {remain[0].mention}.")
				await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
				money = await cur.fetchone()
				if money[0] < prize:
					return await ctx.send("The creator spent money, noone received one!")
				else:
					await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (prize, ctx.author.id))
					await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (prize, remain[0].id))
					await msg.edit(content=f"Tournament ended! The winner is {remain[0].mention}.\nMoney was given!")

def setup(bot):
	bot.add_cog(Tournament(bot))

