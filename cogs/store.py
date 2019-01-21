import discord
from discord.ext import commands
from ast import literal_eval as make_tuple

class Store:

	def __init__(self, bot):
		self.bot = bot

	@commands.command(description="The store. Buy boosters here.")
	async def store(self, ctx):
		shopembed = discord.Embed(title="IdleRPG Store", description=f"Welcome! Use `{ctx.prefix}purchase storeitemid` to buy something.", colour=discord.Colour.blurple())
		shopembed.add_field(name="Boosters", value="`#1` Time Booster\t**$1000**\tBoosts adventure time by 50%\n`#2` Luck Booster\t**$500**\tBoosts adventure luck by 25%\n`#3` Money Booster\t**$1000**\tBoosts adventure money rewards by 25%", inline=False)
		shopembed.set_thumbnail(url=f"{self.bot.BASE_URL}/business.png")
		await ctx.send(embed=shopembed)

	@commands.command(description="Buy an item from the store.")
	async def purchase(self, ctx, item:str, amount:int=1):
		try:
			item = int(item.lstrip("#"))
		except:
			await ctx.send("Enter a valid store item to buy.")
			return
		if item < 1 or item > 3:
			await ctx.send("Enter a valid store item to buy.")
			return
		price = [1000, 500, 1000][item-1] * amount
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT money FROM profile WHERE "money">=%s AND "user"=%s;', (price, ctx.author.id))
				money = await cur.fetchone()
				if not money:
					await ctx.send("You are too poor.")
					return
				else:
					if item == 1: 
						await cur.execute('UPDATE profile SET time_booster=time_booster+%s WHERE "user"=%s;', (amount, ctx.author.id,))
					elif item == 2:
						await cur.execute('UPDATE profile SET luck_booster=luck_booster+%s WHERE "user"=%s;', (amount, ctx.author.id,))
					elif item == 3:
						await cur.execute('UPDATE profile SET money_booster=money_booster+%s WHERE "user"=%s;', (amount, ctx.author.id,))
					await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (price, ctx.author.id))
					await ctx.send(f"Sucessfully bought **{amount}** store item `{item}`. Use `{ctx.prefix}boosters` to view your new boosters.")

	@commands.command(description="View your boosters.")
	async def boosters(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT (time_booster, luck_booster, money_booster) FROM profile WHERE "user"=%s;', (ctx.author.id,))
				boosters = await cur.fetchone()
				if not boosters:
					await ctx.send(f"You don't have a character yet. Use `{ctx.prefix}create` to get started.")
					return
				boosters = make_tuple(boosters[0])
				timeboosters = boosters[0]
				luckboosters = boosters[1]
				moneyboosters = boosters[2]
				active = []
				booster = ["`Time Booster`", "`Luck Booster`", "`Money Booster`"]
				await cur.execute('SELECT "type", "end" FROM boosters WHERE "end" > clock_timestamp() AND "user"=%s;', (ctx.author.id,))
				async for row in cur:
					active.append(row)
				nl = "\n"
				await ctx.send(embed=discord.Embed(title="Your Boosters", description=f"{'**Currently Active**'+nl if active!=[] else ''}{nl.join([booster[row[0]-1]+' until '+row[1].__format__('%A %d. %B %Y at %H:%M:%S') for row in active])}\n\nTime Boosters: `{timeboosters}`\nLuck Boosters: `{luckboosters}`\nMoney Boosters: `{moneyboosters}`", colour=discord.Colour.blurple()).set_footer(text=f"Use {ctx.prefix}activate to activate one"))

	@commands.command(description="Uses a booster.")
	async def activate(self, ctx, boostertype:int):
		if boostertype < 0 or boostertype > 3:
			await ctx.send("That is not a valid booster type. Must be from `1` to `3`.")
			return
		booster = ["time_booster", "luck_booster", "money_booster"][boostertype-1]
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute(f'SELECT {booster} FROM profile WHERE "user"=%s;', (ctx.author.id,))
				res = await cur.fetchone()
				if not res:
					await ctx.send(f"You don't have a character yet. Use `{ctx.prefix}create` to get started.")
					return
				elif res[0]==0:
					await ctx.send("You don't have any of these boosters.")
					return
				else:
					await cur.execute('SELECT * FROM boosters WHERE "type"=%s AND "user"=%s;', (boostertype, ctx.author.id))
					check = await cur.fetchone()
					await cur.execute('SELECT * FROM boosters WHERE "type"=%s AND "user"=%s AND clock_timestamp() > "end";', (boostertype, ctx.author.id))
					check2 = await cur.fetchone()
					if check and not check2:
						await ctx.send(f"You already have one of these boosters active! Use `{ctx.prefix}boosters` to see how long it still lasts.")
						return
					elif check and check2:
						await cur.execute('DELETE FROM boosters WHERE "type"=%s AND "user"=%s;', (boostertype, ctx.author.id))
					await cur.execute(f'UPDATE profile SET {booster}={booster}-1 WHERE "user"=%s;', (ctx.author.id,))
					await cur.execute("SELECT clock_timestamp() + interval %s;", ("1d",))
					end = (await cur.fetchone())[0]
					await cur.execute('INSERT INTO boosters ("user", "type", "end") VALUES (%s, %s, %s);', (ctx.author.id, boostertype, end))
					await ctx.send(f"Successfully activated a **{booster.replace('_', ' ').capitalize()}** for the next **24 hours**!")

def setup(bot):
	bot.add_cog(Store(bot))
