import discord, traceback, asyncio, random
from discord.ext import commands
import cogs.rpgtools as rpgtools
from discord.ext.commands import BucketType

def is_patron(bot, user):
	member = bot.get_guild(430017996304678923).get_member(user.id)  # cross server stuff
	if not member:
		return False
	return discord.utils.get(member.roles, name='Donator') is not None

class Guild:

	def __init__(self, bot):
		self.bot = bot
	

	@commands.group(invoke_without_command=True, description="A command containing various other ones. Try the help on this command.")
	async def guild(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT g.* FROM profile p JOIN guild g ON (p.guild=g.id) WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
		if not guild:
			await ctx.send("You are in no guild yet.")
		else:
			await ctx.invoke(self.bot.get_command("guild info"), name=guild[1])

	@guild.command(description="Views a guild.", hidden=True)
	async def info(self, ctx, *, name:str):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM guild WHERE "name"=%s;', (name,))
				guild = await cur.fetchone()
				if not guild:
					return await ctx.send("No guild found.")
				await cur.execute('SELECT * FROM profile WHERE "guild"=%s;', (guild[0],))
				membercount = []
				async for row in cur:
					membercount.append(row)

		embed = discord.Embed(title=guild[1], description="Information about a guild.")
		embed.add_field(name="Current Member Count", value=f"{len(membercount)}/{guild[2]} Members")
		leader = await rpgtools.lookup(self.bot, guild[3])
		embed.add_field(name="Leader", value=f"{leader}")
		embed.add_field(name="Guild Bank", value=f"**${guild[5]}** / **${guild[7]}**")
		embed.set_thumbnail(url=guild[4])
		try:
			await ctx.send(embed=embed)
		except:
			await ctx.send(f"Your guild icon seems to be a bad URL. Use `{ctx.prefix}guild icon` to fix this.")

	@guild.command(description="Guild GvG Ladder")
	async def ladder(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM guild ORDER BY wins DESC LIMIT 10;')
				ret = []
				async for row in cur:
					ret.append(row)
		result = ""
		for guild in ret:
			number = ret.index(guild)+1
			leader = await rpgtools.lookup(self.bot, guild[3])
			result += f"{number}. {guild[1]}, a guild by `{leader}` with **{guild[6]}** GvG Wins and **${guild[5]}**\n"
		result = discord.Embed(title=f"The Best GvG Guilds", description=result, colour=0xe7ca01)
		await ctx.send(embed=result)


	@guild.command(description="A member list of your guild.")
	async def members(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT g.* FROM profile p JOIN guild g ON (p.guild=g.id) WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if not guild:
					return await ctx.send("You are in no guild yet.")
				await cur.execute('SELECT * FROM profile WHERE "guild"=%s;', (guild[0],))
				members = []
				async for row in cur:
					members.append(row[0])
		leader = await rpgtools.lookup(self.bot, guild[3])
		members = [await rpgtools.lookup(self.bot, m) for m in members]
		embed = discord.Embed(title=guild[1], description="\n".join(members))
		embed.add_field(name="Leader", value=f"{leader}")
		embed.set_thumbnail(url=guild[4])
		try:
			await ctx.send(embed=embed)
		except:
			await ctx.send(f"Your guild icon seems to be a bad URL. Use `{ctx.prefix}guild icon` to fix this.")

	@guild.command(description="Creates a guild.")
	async def create(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if not guild:
					return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to start playing IdleRPG!")
				if guild[0]!=0:
					return await ctx.send("You are already in a guild.")
		def mycheck(amsg):
			return amsg.author==ctx.author
		await ctx.send("Enter a name for your guild. Maximum lenght is 20 characters.")
		try:
			name = await self.bot.wait_for('message', timeout=60, check=mycheck)
		except:
			return await ctx.send("Cancelled guild creation.")
		name = name.content
		if len(name)>20:
			return await ctx.send("Guild names musn't exceed 20 characters.")
		await ctx.send("Send a link to the guild's icon. Maximum lenght is 60 characters.")
		try:
			url = await self.bot.wait_for('message', timeout=60, check=mycheck)
		except:
			return await ctx.send("Cancelled guild creation.")
		url = url.content
		if len(url)>60:
			return await ctx.send("URLs musn't exceed 60 characters.")
		if is_patron(self.bot, ctx.author):
			memberlimit = 100
		else:
			memberlimit = 50
		def check(m):
			return m.content.lower() == "confirm" and m.author == ctx.author
		await ctx.send("Are you sure? Type `confirm` to create a guild for **$10000**")
		try:
			await self.bot.wait_for('message', check=check, timeout=30)
		except:
			return await ctx.send("Guild creation cancelled.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
				usermoney = await cur.fetchone()
				if usermoney[0]<10000:
					return await ctx.send("A guild creation costs **$10000**, you are too poor.")
				await cur.execute('INSERT INTO guild (name, memberlimit, leader, icon) VALUES (%s, %s, %s, %s) RETURNING *;', (name, memberlimit, ctx.author.id, url))
				guild = await cur.fetchone()
				await cur.execute('UPDATE profile SET guild=%s WHERE "user"=%s;', (guild[0], ctx.author.id))
				await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (10000, ctx.author.id))
		await ctx.send(f"Successfully added your guild **{name}** with a member limit of **{memberlimit}**.")

	@guild.command(description="Invite someone to your guild.")
	async def invite(self, ctx, newmember:discord.Member):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT g.* FROM profile p JOIN guild g ON (p.guild=g.id) WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (newmember.id,))
				memberguild = await cur.fetchone()
				if not guild:
					return await ctx.send("You are in no guild yet.")
				if guild[3]!=ctx.author.id:
					return await ctx.send(f"You are not the leader of **{guild[1]}**.")

				if not memberguild:
					return await ctx.send(f"That member hasn't got a character.")
				if memberguild[0]!=0:
					return await ctx.send("That person is already in a guild.")
				await cur.execute('SELECT * FROM profile WHERE "guild"=%s;', (guild[0],))
				membercount = []
				async for row in cur:
					membercount.append(row)
				if len(membercount)>=guild[2]:
					return await ctx.send("Your guild is already at the maximum member count.")
		def mycheck(amsg):
			return amsg.author==newmember and amsg.content.lower() == "invite accept"
		await ctx.send(f"{newmember.mention}, {ctx.author.mention} invites you to join **{guild[1]}**. Type `invite accept` to join the guild.")
		try:
			res = await self.bot.wait_for('message', timeout=60, check=mycheck)
		except:
			return await ctx.send(f"{newmember.mention} didn't want to join your guild, {ctx.author.mention}.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (newmember.id,))
				memberguild = await cur.fetchone()
				await cur.execute('SELECT * FROM profile WHERE "guild"=%s;', (guild[0],))
				membercount = []
				async for row in cur:
					membercount.append(row)
				if len(membercount)>=guild[2]:
					return await ctx.send("Your guild is already at the maximum member count.")
				elif memberguild[0]!=0:
					return await ctx.send("That person joined a guild in the meantime.")
				else:
					await cur.execute('UPDATE profile SET guild=%s WHERE "user"=%s;', (guild[0], newmember.id))
					await ctx.send(f"{newmember.mention} is now a member of **{guild[1]}**. Welcome!")

	@guild.command(description="Leave your current guild.")
	async def leave(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT g.* FROM profile p JOIN guild g ON (p.guild=g.id) WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if not guild:
					return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to start playing IdleRPG!")
				if guild[0]==0:
					return await ctx.send("You are in no guild yet.")
				if guild[3]==ctx.author.id:
					return await ctx.send(f"You are the leader of **{guild[1]}** and cannot leave it.")
				await cur.execute('UPDATE profile SET guild=%s WHERE "user"=%s;', (0, ctx.author.id,))
				await ctx.send(f"You left **{guild[1]}**.")

	@guild.command(description="Kick someone out of your guild.")
	async def kick(self, ctx, user:discord.Member):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT g.* FROM profile p JOIN guild g ON (p.guild=g.id) WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if not guild:
					return await ctx.send("You are in no guild yet.")
				if guild[3]!=ctx.author.id:
					return await ctx.send(f"You are not the leader of **{guild[1]}**.")
				await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (user.id,))
				target = await cur.fetchone()
				if not target:
					return await ctx.send("Target hasn't got a character.")
				if target[0] != guild[0]:
					return await ctx.send("Target isn't in your guild.")
				await cur.execute('UPDATE profile SET guild=%s WHERE "user"=%s;', (0, user.id))
				await ctx.send(f"**{user.display_name}** has been kicked.")

	@guild.command(description="Deletes your guild.")
	async def delete(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT g.* FROM profile p JOIN guild g ON (p.guild=g.id) WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
		if not guild:
			return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to start playing IdleRPG!")
		if guild[0]==0:
			return await ctx.send("You are in no guild yet.")
		if guild[3]!=ctx.author.id:
			return await ctx.send(f"You are not the leader of **{guild[1]}**.")
		def mycheck(amsg):
			return amsg.author==ctx.author and amsg.content.lower() == "guild deletion confirm"
		await ctx.send(f"Are you sure to delete **{guild[1]}**? Type `guild deletion confirm` to confirm the deletion.")
		try:
			res = await self.bot.wait_for('message', timeout=15, check=mycheck)
		except:
			return await ctx.send(f"Cancelled guild deletion.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('DELETE FROM guild WHERE "id"=%s;', (guild[0],))
				await cur.execute('UPDATE profile SET "guild"=%s WHERE "guild"=%s;', (0, guild[0]))
		await ctx.send(f"Successfully deleted your guild **{guild[1]}**.")

	@guild.command(description="Changes your guild icon.")
	async def icon(self, ctx, url:str):
		if len(url)>60:
			return await ctx.send("URLs musn't exceed 60 characters.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT g.* FROM profile p JOIN guild g ON (p.guild=g.id) WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if not guild:
					return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to start playing IdleRPG!")
				if guild[0]==0:
					return await ctx.send("You are in no guild yet.")
				if guild[3]!=ctx.author.id:
					return await ctx.send(f"You are not the leader of **{guild[1]}**.")
				await cur.execute('UPDATE guild SET "icon"=%s WHERE "id"=%s;', (url, guild[0]))
				await ctx.send("Successfully updated the guild icon.")

	@guild.command(description="Shows the richest players in your guild. Maximum 10.")
	async def richest(self, ctx):
		await ctx.trigger_typing()
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT g.* FROM guild g JOIN profile p ON (p.guild=g.id) WHERE p.user=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if not guild:
					return await ctx.send(f"Either you haven't got a character yet or you aren't in a guild yet. Use `{ctx.prefix}create` to create a character.")
				try:
					await cur.execute('SELECT "user", "name", "money" from profile WHERE "guild"=%s ORDER BY "money" DESC LIMIT 10;', (guild[0],))
				except:
					await ctx.send("An error occured when fetching the data.")
				ret = []
				async for row in cur:
					ret.append(row)
		result = ""
		for profile in ret:
			number = ret.index(profile)+1
			charname = await rpgtools.lookup(self.bot, profile[0])
			pstring = f"{number}. {profile[1]}, a character by `{charname}` with **${profile[2]}**\n"
			result += pstring
		result = discord.Embed(title=f"The Richest Players of {guild[1]}", description=result, colour=0xe7ca01)
		await ctx.send(embed=result)

	@guild.command(description="Shows the best players by XP in your guild. Maximum 10.", aliases=["high", "top"])
	async def best(self, ctx):
		await ctx.trigger_typing()
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT g.* FROM guild g JOIN profile p ON (p.guild=g.id) WHERE p.user=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if not guild:
					return await ctx.send(f"Either you haven't got a character yet or you aren't in a guild yet. Use `{ctx.prefix}create` to create a character.")
				try:
					await cur.execute('SELECT "user", "name", "xp" from profile WHERE "guild"=%s ORDER BY "xp" DESC LIMIT 10;', (guild[0],))
				except:
					await ctx.send("An error occured when fetching the data.")
				ret = []
				async for row in cur:
					ret.append(row)
		result = ""
		for profile in ret:
			number = ret.index(profile)+1
			charname = await rpgtools.lookup(self.bot, profile[0])
			pstring = f"{number}. {profile[1]}, a character by `{charname}` with Level **{rpgtools.xptolevel(profile[2])}** (**{profile[2]}** XP)\n"
			result += pstring
		result = discord.Embed(title=f"The Best Players of {guild[1]}", description=result, colour=0xe7ca01)
		await ctx.send(embed=result)

	@guild.command(description="Pay money to your guild's bank.")
	async def invest(self, ctx, amount:int):
		if amount < 0:
			return await ctx.send("Don't scam!")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT money FROM profile WHERE "user"=%s AND "money">=%s;', (ctx.author.id, amount))
				money = await cur.fetchone()
				if not money:
					return await ctx.send(f"Either you haven't got a character yet or you are too poor. Use `{ctx.prefix}create` to create a character.")
				await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if guild[0]==0:
					return await ctx.send("You are in no guild yet.")
				await cur.execute('SELECT money, banklimit FROM guild WHERE "id"=%s;', (guild[0],))
				limit = await cur.fetchone()
				if limit[0] + amount > limit[1]:
					return await ctx.send("The guild bank would be full.")
				await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (amount, ctx.author.id))
				await cur.execute('UPDATE guild SET money=money+%s WHERE "id"=%s;', (amount, guild[0],))
				await ctx.send(f"Successfully added **${amount}** to your guild bank.")

	@guild.command(description="Pay money to a guild member.")
	async def pay(self, ctx, amount:int, member:discord.Member):
		if amount < 0:
			return await ctx.send("Don't scam!")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if guild[0]==0:
					return await ctx.send("You are in no guild yet.")
				await cur.execute('SELECT * FROM guild WHERE "id"=%s;', (guild[0],))
				guild2 = await cur.fetchone()
				if guild2[3]!=ctx.author.id:
					return await ctx.send(f'You are not the leader of **{guild2[1]}**.')
				if guild2[5] < amount:
					return await ctx.send("Your guild is too poor.")
				await cur.execute('UPDATE guild SET money=money-%s WHERE "id"=%s;', (amount, guild[0]))
				await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (amount, member.id))
				await ctx.send(f"Successfully gave **${amount}** from your guild bank to {member.mention}.")

	@guild.command(description="Upgrade your guild bank.")
	async def upgrade(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if guild[0]==0:
					return await ctx.send("You are in no guild yet.")
				await cur.execute('SELECT * FROM guild WHERE "id"=%s;', (guild[0],))
				guild2 = await cur.fetchone()
				if guild2[3]!=ctx.author.id:
					return await ctx.send(f'You are not the leader of **{guild2[1]}**.')
				currentlimit = guild2[7]
				level = int(currentlimit / 250000)
				if level == 4:
					return await ctx.send("Your guild already reached the maximum upgrade.")
				if int(currentlimit/2) > guild2[5]:
					return await ctx.send(f"Your guild is too poor, you got **${guild2[5]}** but it costs **${int(currentlimit/2)}** to upgrade.")
				await cur.execute('UPDATE guild SET banklimit=banklimit+%s WHERE "id"=%s;', (250000, guild[0]))
				await cur.execute('UPDATE guild SET money=money-%s WHERE "id"=%s;', (int(currentlimit/2), guild[0]))
				await ctx.send(f"Your new guild bank limit is now **${currentlimit+250000}**.")

	@guild.command(description="Battle against another guild.")
	async def battle(self, ctx, enemy:discord.Member, amount:int, fightercount:int):
		if amount < 0:
			return await ctx.send("Don't scam!")
		if enemy is ctx.author:
			return await ctx.send("Poor kiddo having no friendos.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (ctx.author.id,))
				guild1 = await cur.fetchone()
				await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (enemy.id,))
				guild2 = await cur.fetchone()
				if guild1[0] == 0 or guild2[0] == 0:
					return await ctx.send("One of you both doesn't have a guild.")
				await cur.execute('SELECT * FROM guild WHERE "id"=%s;', (guild1[0],))
				guild1 = await cur.fetchone()
				await cur.execute('SELECT * FROM guild WHERE "id"=%s;', (guild2[0],))
				guild2 = await cur.fetchone()
				if guild1[3] != ctx.author.id or guild2[3] != enemy.id:
					return await ctx.send("One of you both isn't the leader of his guild.")
				if guild1[5] < amount or guild2[5] < amount:
					return await ctx.send("One of the guilds can't pay the price.")
				#get guild size
				await cur.execute('SELECT user FROM profile WHERE "guild"=%s;', (guild1[0],))
				size1 = len(await cur.fetchall())
				await cur.execute('SELECT user FROM profile WHERE "guild"=%s;', (guild2[0],))
				size2 = len(await cur.fetchall())
				if size1 < fightercount or size2 < fightercount:
					return await ctx.send("One of the guilds is too small.")
				def msgcheck(amsg):
					return amsg.author == enemy and amsg.content.strip() == "guild battle accept"
				await ctx.send(f"{enemy.mention}, {ctx.author.mention} invites you to fight in a guild battle. Type `guild battle accept` to join the battle. You got **1 Minute to accept**.")
				try:
					res = await self.bot.wait_for('message', timeout=60, check=msgcheck)
				except:
					return await ctx.send(f"{enemy.mention} didn't want to join your battle, {ctx.author.mention}.")
				await ctx.send(f"{enemy.mention} accepted the challenge by {ctx.author.mention}. Please now nominate members, {ctx.author.mention}. Use `battle nominate @user` to add someone to your team.")
				team1 = []
				team2 = []
				async def guildcheck(already, guildid, user):
					try:
						member = await commands.UserConverter().convert(ctx, user)
					except:
						return False
					await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (member.id,))
					guild = await cur.fetchone()
					if guild[0] != guildid:
						await ctx.send("That person isn't in your guild.")
						return False
					if member in already:
						return False
					return member

				def simple1(msg):
					return msg.author==ctx.author and msg.content.startswith("battle nominate")

				def simple2(msg):
					return msg.author==enemy and msg.content.startswith("battle nominate")

				while len(team1) != fightercount:
					try:
						res = await self.bot.wait_for('message', timeout=30, check=simple1)
						guild1check = await guildcheck(team1, guild1[0], res.content.split()[-1])
						if guild1check:
							team1.append(guild1check)
							await ctx.send(f'{guild1check} has been added to your team, {ctx.author.mention}.')
						else:
							await ctx.send("User not found.")
							continue
					except:
						return await ctx.send("Took to long to add members. Fight cancelled.")
				await ctx.send(f"Please now nominate members, {enemy.mention}. Use `battle nominate @user` to add someone to your team.")
				while len(team2) != fightercount:
					try:
						res = await self.bot.wait_for('message', timeout=30, check=simple2)
						guild2check = await guildcheck(team2, guild2[0], res.content.split()[-1])
						if guild2check:
							team2.append(guild2check)
							await ctx.send(f'{guild2check} has been added to your team, {enemy.mention}.')
						else:
							await ctx.send("User not found.")
							continue
					except:
						return await ctx.send("Took to long to add members. Fight cancelled.")
				msg = await ctx.send("Fight started!\nGenerating battles...")
				await asyncio.sleep(3)
				await msg.edit(content="Fight started!\nGenerating battles... Done.")
				wins1 = 0
				wins2 = 0
				for user in team1:
					user2 = team2[team1.index(user)]
					msg = await ctx.send(f"Guild Battle Fight **{team1.index(user)+1}** of **{len(team1)}**.\n**{user.name}** vs **{user2.name}**!\nBattle running...")
					await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (user.id,))
					sword1 = await cur.fetchone()
					try:
						sw1 = sword1[5]
					except:
						sw1 = 0
					await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (user.id,))
					shield1 = await cur.fetchone()
					try:
						sh1 = shield1[6]
					except:
						sh1 = 0
					await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (user2.id,))
					sword2 = await cur.fetchone()
					try:
						sw2 = sword2[5]
					except:
						sw2 = 0
					await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (user2.id,))
					shield2 = await cur.fetchone()
					try:
						sh2 = shield2[6]
					except:
						sh2 = 0
					val1 = sw1 + sh1 + random.randint(1, 7)
					val2 = sw2 + sh2 + random.randint(1, 7)
					if val1>val2:
						winner = user
						wins1 += 1
					elif val2>val1:
						winner = user2
						wins2 += 1
					else:
						winner = random.choice(user, user2)
						if winner == user:
							wins1 += 1
						else:
							wins2 += 1
					await asyncio.sleep(5)
					await ctx.send(f"Winner of **{user}** vs **{user2}** is **{winner}**! Current points: **{wins1}** to **{wins2}**.")
				if wins1 > wins2:
					await cur.execute('UPDATE guild SET money=money+%s WHERE "id"=%s;', (amount, guild1[0]))
					await cur.execute('UPDATE guild SET money=money-%s WHERE "id"=%s;', (amount, guild2[0]))
					await cur.execute('UPDATE guild SET wins=wins+1 WHERE "id"=%s;', (guild1[0],))
					await ctx.send(f"{guild1[1]} won the battle! Congratulations!")
				elif wins2 > wins1:
					await cur.execute('UPDATE guild SET money=money+%s WHERE "id"=%s;', (amount, guild2[0]))
					await cur.execute('UPDATE guild SET money=money-%s WHERE "id"=%s;', (amount, guild1[0]))
					await cur.execute('UPDATE guild SET wins=wins+1 WHERE "id"=%s;', (guild2[0],))
					await ctx.send(f"{guild2[1]} won the battle! Congratulations!")
				else:
					await ctx.send("It's a tie!")

	@commands.cooldown(1,3600,BucketType.user)
	@guild.command(description="Starts a guild adventure.")
	async def adventure(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM profile p JOIN guild g ON (p.guild=g.id) WHERE p."user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()

				if not guild:
					return await ctx.send("You haven't got a character yet.")
				if guild[12] == 0:
					return await ctx.send("You are in no guild yet.")
				if guild[19] != ctx.author.id:
					return await ctx.send(f"You are not the leader of **{guild[17]}**. Contact him to start an adventure!")
				await cur.execute('SELECT * FROM guildadventure WHERE "guildid"=%s;', (guild[12],))
				check = await cur.fetchone()
				if check:
					return await ctx.send(f"Your guild is already on an adventure! Use `{ctx.prefix}guild status` to view how long it still lasts.")


		await ctx.send(f"{ctx.author.mention} seeks a guild adventure for **{guild[1]}**! Write `guild adventure join` to join them! Unlimited players can join in the next 30 seconds. The minimum of players required is 3.")

		joined = [ctx.author]
		difficulty = int(rpgtools.xptolevel(guild[3]))
		started = False

		async def is_in_guild(userid, difficulty):
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					await cur.execute('SELECT guild, xp FROM profile WHERE "user"=%s;', (userid,))
					user = await cur.fetchone()
					if user[0] == guild[16]:
						difficulty += int(rpgtools.xptolevel(user[1]))
						return difficulty
					return False

		def apply(msg):
			return msg.content.lower() == "guild adventure join" and not msg.author.bot and msg.author not in joined

		while not started:
			try:
				msg = await self.bot.wait_for('message', check=apply, timeout=30)
				test = await is_in_guild(msg.author.id, difficulty)
				if test:
					difficulty = test
					joined.append(msg.author)
					await ctx.send(f"Alright, {msg.author.mention}, you have been added.")
				else:
					await ctx.send("You aren't in their guild.")
			except:
				if len(joined) < 3:
					return await ctx.send("You didn't get enough other players for the guild adventure.")
				started = True

		time = str(difficulty*0.5)+"h"

		await ctx.send(f"""
Guild adventure for **{guild[17]}** started!
Participants:
{', '.join([m.mention for m in joined])}

Difficulty is **{difficulty}**
Time it will take: **{time}**
""")

		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute("SELECT clock_timestamp() + interval %s;", (time,))
				enddate = await cur.fetchone()
				await cur.execute('INSERT INTO guildadventure ("guildid", "end", "difficulty") VALUES (%s, %s, %s);', (guild[12], enddate[0], difficulty))

	@guild.command(description="Views your guild adventure status.")
	async def status(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (ctx.author.id,))
				guild = await cur.fetchone()
				if not guild:
					return await ctx.send("You haven't got a character yet.")
				if guild[0] == 0:
					return await ctx.send("You didn't join a guild yet.")
				await cur.execute('SELECT * FROM guildadventure WHERE "guildid"=%s;', (guild[0],))
				adventure = await cur.fetchone()

				if not adventure:
					return await ctx.send(f"Your guild isn't on an adventure yet. Ask your guild leader to use `{ctx.prefix}guild adventure` to start one")

				await cur.execute('SELECT * FROM guildadventure WHERE "guildid"=%s AND "end" < clock_timestamp();', (guild[0],))
				finished = await cur.fetchone()

				if finished:
					gold = random.randint(adventure[2]*20, adventure[2]*50)
					await cur.execute('DELETE FROM guildadventure WHERE "guildid"=%s', (guild[0],))
					await cur.execute('UPDATE guild SET money=money+%s WHERE "id"=%s;', (gold, guild[0]))
					await ctx.send(f"Your guild has completed an adventure of difficulty `{adventure[2]}` and **${gold}** has been added to the bank.")
				else:
					await cur.execute("SELECT %s-clock_timestamp();", (adventure[1],))
					remain = await cur.fetchone()
					await ctx.send(f"Your guild is currently in an adventure with difficulty `{adventure[2]}`.\nTime remaining: `{str(remain[0]).split('.')[0]}`")

def setup(bot):
	bot.add_cog(Guild(bot))

