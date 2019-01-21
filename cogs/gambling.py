import discord, random, os
from discord.ext import commands
from discord.ext.commands import BucketType


class Gambling:

	def __init__(self, bot):
		self.bot = bot
	
	@commands.cooldown(1,5,BucketType.user)
	@commands.command(description="Draw a card!", aliases=["card"])
	async def draw(self, ctx):
		await ctx.trigger_typing()
		files = os.listdir("cards")
		await ctx.send(file=discord.File(f"cards/{random.choice(files)}"))

	@commands.cooldown(1,5,BucketType.user)
	@commands.command(description="Flip a coin to win some money!", aliases=["coin"])
	async def flip(self, ctx, side:str="heads", amount:int=0):
		side = side.lower()
		if side != "heads" and side != "tails":
			await ctx.send(f"Use `heads` or `tails` instead of `{side}`.")
			return
		if amount < 0:
			await ctx.send("Invalid money amount. Must be 0 or higher.")
			return
		if amount > 10000:
			return await ctx.send("You will think of a better way to spend this.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT money FROM profile WHERE "user"=%s AND "money">=%s;', (ctx.author.id, amount))
				ret = []
				async for row in cur:
					ret.append(row)
				if ret == []:
					await ctx.send(f"Either you haven't got a character or you don't have enough money. Use `{ctx.prefix}create` to make a new one.")
				else:
					result = random.choice(["heads", "tails"])
					if result == "heads":
						resultemoji = "<:heads:437981551196897281>"
					else:
						resultemoji = "<:tails:437981602518138890>"
					if result == side:
						await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (amount, ctx.author.id))
						await ctx.send(f"{resultemoji} It's **{result}**! You won **${amount}**!")
					else:
						await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (amount, ctx.author.id))
						await ctx.send(f"{resultemoji} It's **{result}**! You lost **${amount}**!")

	@commands.command(description="Roll the dice and win some money!")
	@commands.cooldown(1,5,BucketType.user)
	async def bet(self, ctx, maximum:int=6, tip:int=6, money:int=0):
		if maximum < 2:
			await ctx.send("Invalid Maximum.")
			return
		if tip > maximum or tip < 1:
			await ctx.send(f"Invalid Tip. Must be in the Range of `1` to `{maximum}`.")
			return
		if money < 0:
			await ctx.send("Invalid money amout. Must be 0 or higher.")
			return
		if money > 10000:
			return await ctx.send("Spend it in a better way. C'mon!")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT money FROM profile WHERE "user"=%s AND "money">=%s;', (ctx.author.id, money))
				ret = []
				async for row in cur:
					ret.append(row)
				if ret==[]:
					await ctx.send(f"Either you haven't got a character or you don't have enough money. Use `{ctx.prefix}create` to make a new one.")
				else:
					randomn = random.randint(1, maximum)
					if randomn == tip:
						await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s', (money*(maximum-1), ctx.author.id))
						await ctx.send(f"You won **${money*(maximum-1)}**! The random number was `{randomn}`, you tipped `{tip}`.")
					else:
						await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s', (money, ctx.author.id))
						await ctx.send(f"You lost **${money}**! The random number was `{randomn}`, you tipped `{tip}`.")



def setup(bot):
	bot.add_cog(Gambling(bot))
