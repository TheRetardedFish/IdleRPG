import discord
from discord.ext import commands
import cogs.rpgtools as rpgtools
from discord.ext.commands import BucketType
import random
import traceback

class Marriage:

	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=["marry"], description="Propose for a marriage!")
	async def propose(self, ctx, partner:discord.Member):
		if partner.id == ctx.author.id:
			await ctx.send("You should have a better friend than only yourself.")
			return
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM profile WHERE "user"=%s AND "marriage"=%s;', (ctx.author.id, 0))
				check1 = await cur.fetchone()
				await cur.execute('SELECT * FROM profile WHERE "user"=%s AND "marriage"=%s;', (partner.id, 0))
				check2 = await cur.fetchone()
				if check1 and check2:
					msg = await ctx.send(embed=discord.Embed(title=f"{ctx.author.name} has proposed for a marriage!", description=f"{ctx.author.mention} wants to marry you, {partner.mention}! React with :heart: to marry him/her!", colour=0xff0000).set_image(url=ctx.author.avatar_url).set_thumbnail(url="http://www.maasbach.com/wp-content/uploads/The-heart.png"))
					await msg.add_reaction("\U00002764")
					waiting = True
					def reactioncheck(reaction, user):
						return str(reaction.emoji) == "\U00002764" and reaction.message.id==msg.id and user.id==partner.id
					while waiting:
						try:
							reaction, user = await self.bot.wait_for('reaction_add', timeout=120.0, check=reactioncheck)
							#check if someone married in the meantime
							await cur.execute('SELECT * FROM profile WHERE "user"=%s AND "marriage"=%s;', (ctx.author.id, 0))
							check1 = await cur.fetchone()
							await cur.execute('SELECT * FROM profile WHERE "user"=%s AND "marriage"=%s;', (partner.id, 0))
							check2 = await cur.fetchone()
							if check1 and check2:
								await cur.execute('UPDATE profile SET "marriage"=%s WHERE "user"=%s;', (partner.id, ctx.author.id))
								await cur.execute('UPDATE profile SET "marriage"=%s WHERE "user"=%s;', (ctx.author.id, partner.id))
								await ctx.send(f"Owwwwwww! :heart: {ctx.author.mention} and {partner.mention} are now married!")
							else:
								await ctx.send(f"Either you or he/she married in the meantime, {ctx.author.mention}... :broken_heart:")
							waiting = False
							try:
								await msg.clear_reactions()
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

				else:
					await ctx.send("One of you both doesn't have a character or is already married... :broken_heart:")

	@commands.command(description="Divorce from your partner.")
	async def divorce(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT marriage FROM profile WHERE "user"=%s;', (ctx.author.id,))
				test = await cur.fetchone()
				if not test:
					await ctx.send(f"You don't have a character yet. Use `{ctx.prefix}create` to make one.")
				elif test[0]==0:
					await ctx.send("You are not married yet.")
				else:
					await cur.execute('UPDATE profile SET "marriage"=0 WHERE "user"=%s;', (ctx.author.id,))
					await cur.execute('UPDATE profile SET "marriage"=0 WHERE "user"=%s;', (test[0],))
					await cur.execute('DELETE FROM children WHERE "father"=%s OR "mother"=%s;', (ctx.author.id, ctx.author.id))
					await ctx.send("You are now divorced.")

	@commands.command(description="View your marriage status.")
	async def relationship(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT marriage FROM profile WHERE "user"=%s;', (ctx.author.id,))
				marriage = await cur.fetchone()
				if not marriage:
					await ctx.send(f"You don't have a character yet. Use `{ctx.prefix}create` to make one.")
				elif marriage[0]==0:
					await ctx.send("You are not married yet.")
				else:
					partner = await rpgtools.lookup(self.bot, marriage[0])
					await ctx.send(f"You are currently married to **{partner}**.")

	@commands.cooldown(1,3600,BucketType.user)
	@commands.command(description="Make a child!", aliases=["fuck", "sex", "breed"])
	async def child(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT marriage FROM profile WHERE "user"=%s;', (ctx.author.id,))
				marriage = await cur.fetchone()
				await cur.execute('SELECT count(*) FROM children WHERE "mother"=%s OR "father"=%s;', (ctx.author.id, ctx.author.id))
				count = await cur.fetchone()
				await cur.execute('SELECT name FROM children WHERE "mother"=%s OR "father"=%s;', (ctx.author.id, ctx.author.id))
				names = []
				async for row in cur:
					names.append(row)
				if not marriage:
					return await ctx.send(f"You don't have a character yet. Use `{ctx.prefix}create` to make one.")
				elif marriage[0]==0:
					return await ctx.send("You are not married yet.")
				elif count[0] >= 10:
					return await ctx.send("You already have 10 children.")
		msg = await ctx.send(f"Asking <@{marriage[0]}> for a night...\nDo you want to make a child with {ctx.author.mention}? Type `I do`")
		def check(msg):
			return msg.author.id == marriage[0] and msg.content.lower() == "i do"
		try:
			msg = await self.bot.wait_for('message', check=check, timeout=30)
		except:
			return await ctx.send(f"They didn't want to have a child :(")
		if random.randint(1,2) == 1:
			return await ctx.send("You were unsuccessful at making a child.")
		gender = random.choice(["m", "f"])
		if gender == "m":
			await ctx.send("It's a boy! Your night of love was successful! Please enter a name for your child.")
		elif gender == "f":
			await ctx.send("It's a girl! Your night of love was successful! Please enter a name for your child.")
		def check(msg):
			return msg.author.id in [ctx.author.id, marriage[0]] and len(msg.content) <= 20 and msg.content not in names
		try:
			msg = await self.bot.wait_for('message', check=check, timeout=30)
		except:
			return await ctx.send("You didn't enter a name.")
		name = msg.content
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('INSERT INTO children ("mother", "father", "name", "age", "gender") VALUES (%s, %s, %s, %s, %s);', (ctx.author.id, marriage[0], name, 0, gender))
		await ctx.send(f"{name} was born.")


	@commands.command(description="View your children.")
	async def family(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT marriage FROM profile WHERE "user"=%s;', (ctx.author.id,))
				marriage = await cur.fetchone()
				if not marriage:
					return await ctx.send(f"You don't have a character yet. Use `{ctx.prefix}create` to make one.")
				elif marriage[0]==0:
					return await ctx.send("You are not married yet.")
				await cur.execute('SELECT * FROM children WHERE "mother"=%s OR "father"=%s;', (ctx.author.id, ctx.author.id))
				children = []
				async for row in cur:
					children.append(row)
				em = discord.Embed(title="Your family", description=f"Family of {ctx.author.mention} and <@{marriage[0]}>")
				if children == []:
					em.add_field(name="No children yet", value=f"Use {ctx.prefix}child to make one!")
				for child in children:
					em.add_field(name=child[2], value=f"Gender: {child[4]}, Age: {child[3]}", inline=False)
				em.set_thumbnail(url=ctx.author.avatar_url)
				await ctx.send(embed=em)

	@commands.cooldown(1,1800,BucketType.user)
	@commands.command(description="Events happening to your family.")
	async def familyevent(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT marriage FROM profile WHERE "user"=%s;', (ctx.author.id,))
				marriage = await cur.fetchone()
				if not marriage:
					return await ctx.send(f"You don't have a character yet. Use `{ctx.prefix}create` to make one.")
				elif marriage[0]==0:
					return await ctx.send("You are not married yet.")
				await cur.execute('SELECT * FROM children WHERE "mother"=%s OR "father"=%s;', (ctx.author.id, ctx.author.id))
				children = []
				async for row in cur:
					children.append(row)
				if children == []:
					return await ctx.send("You don't have kids yet.")
				target = random.choice(children)
				event = random.choice(["death"] + ["age"] * 7 + ["namechange"] * 2)
				if event == "death":
					await cur.execute('DELETE FROM children WHERE "name"=%s AND ("mother"=%s OR "father"=%s);', (target[2], ctx.author.id, ctx.author.id))
					return await ctx.send(f"{target[2]} died at the age of {target[3]}! Poor kiddo!")
				elif event == "age":
					await cur.execute('UPDATE children SET age=age+1 WHERE "name"=%s AND ("mother"=%s OR "father"=%s);', (target[2], ctx.author.id, ctx.author.id))
					return await ctx.send(f"{target[2]} is now {target[3]+1} years old.")
				elif event == "namechange":
					await ctx.send(f"{target[2]} can be renamed! Enter a new name:")
					def check(msg):
						return msg.author.id in [ctx.author.id, marriage[0]] and len(msg.content) <= 20
					try:
						msg = await self.bot.wait_for('message', check=check, timeout=30)
					except:
						return await ctx.send("You didn't enter a name.")
					name = msg.content
					await cur.execute('UPDATE children SET "name"=%s WHERE "name"=%s AND ("mother"=%s OR "father"=%s);', (name, target[2], ctx.author.id, ctx.author.id))
					return await ctx.send(f"{target[2]} is now called {name}.")


def setup(bot):
	bot.add_cog(Marriage(bot))
