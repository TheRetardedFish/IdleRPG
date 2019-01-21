import discord, aiohttp, random
from discord.ext import commands
from discord.ext.commands import BucketType

dbltoken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQyNDYwNjQ0Nzg2Nzc4OTMxMiIsImJvdCI6dHJ1ZSwiaWF0IjoxNTI2NDQ1NDgzfQ.lEFlm2N9g2mEjfth15TL-a0iGwquuN-0cX_ioouvsGs"
headers = {"Authorization" : dbltoken}

class Vote:

	def __init__(self, bot):
		self.bot = bot

	@commands.command(description="Sends a vote link.")
	async def vote(self, ctx):
		await ctx.send(f"Upvote me for a big thanks! You will be rewarded a few seconds afterwards!\nhttps://discordbots.org/bot/idlerpg")
"""
	@commands.cooldown(1, 86400, BucketType.user)
	@commands.command(description="Receive a crate if you voted the bot up.")
	async def claim(self, ctx):
		async with aiohttp.ClientSession(headers=headers) as cs:
			async with cs.get(f'https://discordbots.org/api/bots/424606447867789312/check?userId={ctx.message.author.id}&anticache={random.randint(1,100000000)}') as r:
				voter = await r.json()
				voter = dict(voter)
				if voter["voted"] == 1:
					async with self.bot.pool.acquire() as conn:
						async with conn.cursor() as cur:
							await cur.execute('UPDATE profile SET crates=crates+1 WHERE "user"=%s', (ctx.author.id,))
							await ctx.send(f"Thanks for voting me up! You got a crate for voting if you had a character. Use `{ctx.prefix}crates` to view your crates count.")
				else:
					await ctx.send("You haven't voted for me yet! Do it here:\nhttps://discordbots.org/bot/idlerpg")
					ctx.command.reset_cooldown(ctx)
"""
def setup(bot):
	bot.add_cog(Vote(bot))
