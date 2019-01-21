import discord, random
from discord.ext import commands

class Crates:

	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=["boxes"], descripiton="Shows your current crates.")
	async def crates(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT crates FROM profile WHERE "user"=%s;', (ctx.message.author.id,))
				except:
					await ctx.send("An error occured when fetching your character's data.")
				ret = await cur.fetchone()
		if not ret:
			await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to make your own character!")
		else:
			crates = ret[0]
			await ctx.send(f"You currently have **{crates}** crates, {ctx.author.mention}! Use `{ctx.prefix}open` to open one!")

	@commands.command(description="Open a crate!", name="open")
	async def _open(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT crates FROM profile WHERE "user"=%s;', (ctx.author.id,))
				except:
					await ctx.send("An error occured when fetching your character's data.")
				ret = await cur.fetchone()
				if len(ret)==0:
					await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to make your own character!")
					return
				elif ret[0]<1:
					await ctx.send("Seems you haven't got a crate yet. Vote me up to get some or earn them!")
				else:
					mytry = random.randint(1,6)
					if mytry==1:
						maximumstat = float(random.randint(20,30))
					elif mytry==2 or mytry==3:
						maximumstat = float(random.randint(10,19))
					else:
						maximumstat = float(random.randint(1,9))
					shieldorsword = random.choice(["Sword", "Shield"])
					names = ["Rare", "Ancient", "Normal", "Legendary", "Famous"]
					itemvalue = random.randint(1,250)
					if shieldorsword == "Sword":
						itemname = random.choice(names)+random.choice([" Sword", " Blade", " Stich"])
						await cur.execute('INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES (%s, %s, %s, %s, %s, %s) RETURNING *;', (ctx.author.id, itemname, itemvalue, "Sword", maximumstat, 0.00))
					elif shieldorsword == "Shield":
						itemname = random.choice(names)+random.choice([" Shield", " Defender", " Aegis"])
						await cur.execute('INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES (%s, %s, %s, %s, %s, %s) RETURNING *;', (ctx.author.id, itemname, itemvalue, "Shield", 0.00, maximumstat))
					item = await cur.fetchone()
					await cur.execute('INSERT INTO inventory ("item", "equipped") VALUES (%s, %s);', (item[0], False))
					await cur.execute('UPDATE profile SET "crates"=%s WHERE "user"=%s;', (ret[0]-1, ctx.author.id))
					embed=discord.Embed(title="You gained an item!", description="You found a new item when opening a crate!", color=0xff0000)
					embed.set_thumbnail(url=ctx.author.avatar_url)
					embed.add_field(name="Name", value=itemname, inline=False)
					embed.add_field(name="Type", value=shieldorsword, inline=False)
					if shieldorsword == "Shield":
						embed.add_field(name="Damage", value="0.00", inline=True)
						embed.add_field(name="Armor", value=f"{maximumstat}0", inline=True)
					else:
						embed.add_field(name="Damage", value=f"{maximumstat}0", inline=True)
						embed.add_field(name="Armor", value="0.00", inline=True)
					embed.add_field(name="Value", value=f"${itemvalue}", inline=False)
					embed.set_footer(text=f"Remaining crates: {ret[0]-1}")
					await ctx.send(embed=embed)

	@commands.command(description="Trades a crate to a user.")
	async def tradecrate(self, ctx, other:discord.Member):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT crates FROM profile WHERE "crates">0 AND "user"=%s;', (ctx.author.id,))
				crates = await cur.fetchone()
				if crates is None:
					await ctx.send("You don't have any crates.")
					return
				else:
					await cur.execute('UPDATE profile SET crates=crates-1 WHERE "user"=%s;', (ctx.author.id,))
					await cur.execute('UPDATE profile SET crates=crates+1 WHERE "user"=%s;', (other.id,))
					await ctx.send(f"Successfully gave 1 crate to {other.mention}.")


def setup(bot):
	bot.add_cog(Crates(bot))

