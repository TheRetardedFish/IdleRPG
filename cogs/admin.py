import discord
from discord.ext import commands

admins = [356091260429402122, 373797591395205122, 395938979293167617, 270624053809643522, 353978827157929987, 222005168147922944, 147874400836911104, 278269289960833035, 291215916916801536, 213045557181022209]

def is_admin():
	async def predicate(ctx):
		return ctx.author.id in admins
	return commands.check(predicate)

class Admin:

	def __init__(self, bot):
		self.bot = bot

	@is_admin()
	@commands.command(description="Gift money!", hidden=True)
	async def admingive(self, ctx, money: int, other: discord.Member=None):
		if other is None:
			await ctx.send("Uh, you entered no Member! Use a mention!")
			return
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (money, other.id,))
					await ctx.send(f"Successfully gave **${money}** without a loss for you to {other.mention}.")
				except:
					await ctx.send("That person doesn't have a character.")
		channel = self.bot.get_channel(457197748626653184)
		await channel.send(f"{ctx.author.mention} gave **${money}** to **{other}**.")

	@is_admin()
	@commands.command(description="Delete money!", hidden=True)
	async def adminremove(self, ctx, money: int, other: discord.Member=None):
		if other is None:
			await ctx.send("Uh, you entered no Member! Use a mention!")
			return
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (money, other.id))
					await ctx.send(f"Successfully removed **${money}** from {other.mention}.")
				except:
					await ctx.send("That person doesn't have a character.")
		channel = self.bot.get_channel(457197748626653184)
		await channel.send(f"{ctx.author.mention} removed **${money}** from **{other}**.")


	@is_admin()
	@commands.command(description="Deletes a character.", hidden=True)
	async def admindelete(self, ctx, other:discord.Member=None):
		if other is None:
			await ctx.send("Uh, you entered no Member! Use a mention!")
			return
		if other.id in admins:
			return await ctx.send("Very funny...")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM profile WHERE "user"=%s;', (other.id,))
				ret = []
				async for row in cur:
					ret.append(row)
				if ret==[]:
					await ctx.send("That person doesn't have a character.")
				else:
					await cur.execute('DELETE FROM profile WHERE "user"=%s;', (other.id,))
					await ctx.send("Successfully deleted the character.")
		channel = self.bot.get_channel(457197748626653184)
		await channel.send(f"{ctx.author.mention} deleted **{other}**.")


	@is_admin()
	@commands.command(description="Changes a character name")
	async def adminrename(self, ctx, target: discord.User):
		if target.id in admins:
			return await ctx.send("Very funny...")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT * from profile WHERE "user"=%s;', (target.id,))
				except:
					await ctx.send("An error occured when the character's data.")
				ret = []
				async for row in cur:
					ret.append(row)
				if ret==[]:
					await ctx.send("That person hasn't got a character yet.")
				else:
					await ctx.send("What shall the character's name be? (Minimum 3 Characters, Maximum 20)")
					try:
						def mycheck(amsg):
							return amsg.author==ctx.author
						name = await self.bot.wait_for('message', timeout=60, check=mycheck)
						if name is not None:
							name = name.content.strip()
						if len(name)>2 and len(name)<21:
							await cur.execute('UPDATE profile SET "name"=%s WHERE "user"=%s;', (name, target.id,))
							await ctx.send("Character name updated.")
						elif len(name)<3:
							await ctx.send("Character names must be at least 3 characters!")
						elif len(name)>20:
							await ctx.send("Character names mustn't exceed 20 characters!")
						else:
							await ctx.send("An unknown error occured while checking the name. Try again!")
					except:
						await ctx.send(f"Timeout expired. Enter `{ctx.prefix}{ctx.command}` again to retry!")
		channel = self.bot.get_channel(457197748626653184)
		await channel.send(f"{ctx.author.mention} renamed **{target}** to **{name}**.")


def setup(bot):
	bot.add_cog(Admin(bot))
