import discord, functools
from io import BytesIO
from discord.ext import commands
from cogs.rpgtools import makebg

def is_patron():
	def predicate(ctx):
		member = ctx.bot.get_guild(430017996304678923).get_member(ctx.author.id)  # cross server stuff
		if not member:
			return False
		return discord.utils.get(member.roles, name='Donator') is not None or discord.utils.get(member.roles, name='Administrators') is not None
	return commands.check(predicate)

class Patreon:

	def __init__(self, bot):
		self.bot = bot

	@is_patron()
	@commands.command(description="[Patreon Only] Changes a weapon name.")
	async def weaponname(self, ctx, itemid: int, *, newname: str):
		if len(newname)>20:
			await ctx.send("Name too long.")
			return
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM allitems WHERE "owner"=%s and "id"=%s;', (ctx.author.id, itemid))
				item = await cur.fetchone()
				if not item:
					await ctx.send(f"You don't own an item with the ID `{itemid}`.")
					return
				await cur.execute('UPDATE allitems SET "name"=%s WHERE "id"=%s;', (newname, itemid))
				await ctx.send(f"The item with the ID `{itemid}` is now called `{newname}`.")

	@is_patron()
	@commands.command(description="[Patreon Only] Changes your profile background.")
	async def background(self, ctx, url: str=None):
		premade = [f"{self.bot.BASE_URL}/profile/premade1.png", f"{self.bot.BASE_URL}/profile/premade2.png", f"{self.bot.BASE_URL}/profile/premade3.png", f"{self.bot.BASE_URL}/profile/premade4.png"]
		if not url:
			return await ctx.send(f"Please specify either a premade background (`1` to `{len(premade)}`), a custom URL or use `reset` to use the standard image.")
		elif url == "reset":
			url = 0
		elif url.startswith("http") and (url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg")):
			url = url
		else:
			try:
				if int(url) in range(1, len(premade)+1):
					url = premade[int(url)-1]
				else:
					return await ctx.send("That is not a valid premade background.")
			except:
				return await ctx.send("I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('UPDATE profile SET "background"=%s WHERE "user"=%s;', (url, ctx.author.id,))
				except:
					return await ctx.send("The URL is too long.")
				if url != 0:
					await ctx.send(f"Your new profile picture is now:\n{url}")
				else:
					await ctx.send("Your profile picture has been resetted.")

	@is_patron()
	@commands.command(description="[Patreon Only] Generates a background image.")
	async def makebackground(self, ctx, url: str, overlaytype: int):
		if overlaytype not in [1,2]:
			return await ctx.send("User either `1` or `2` as the overlay type.")
		if not url.startswith("http") and (url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg")):
			return await ctx.send("I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?")
			async with self.bot.session.get(url) as r:
				background = BytesIO(await r.read())
				background.seek(0)
		thing = functools.partial(makebg, background, overlaytype)
		output_buffer = await self.bot.loop.run_in_executor(None, thing)
		await ctx.send(file=discord.File(fp=output_buffer, filename="GeneratedProfile.png"))


def setup(bot):
	bot.add_cog(Patreon(bot))
