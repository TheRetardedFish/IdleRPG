import discord, random
import cogs.rpgtools as rpgtools
from cogs.rpgtools import makeadventures
from discord.ext import commands
import functools
import traceback
from cogs.classes import genstats
from discord.ext.commands import BucketType

class Adventure:

	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=["missions", "dungeons"], description="Shows a list of all dungeons with your success rate.")
	async def adventures(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM dungeon ORDER BY "id";')
				alldungeons = []
				async for row in cur:
					alldungeons.append(row)
				if alldungeons == []:
					owner = (await self.bot.application_info()).owner
					return await ctx.send("Either no adventures exist or a serious issue occured. Contact `{owner}` please and tell me what you tried.")
				else:
					await cur.execute('SELECT * FROM profile WHERE "user"=%s;', (ctx.message.author.id,))
					ret = []
					async for row in cur:
						ret.append(row)
					if ret==[]:
						await ctx.send(f"I am not able to display you the dungeon overview because you don't have a character. Use `{ctx.prefix}create` to start your IdleRPG!")
						return
					await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (ctx.author.id,))
					sword = await cur.fetchone()
					await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (ctx.author.id,))
					shield = await cur.fetchone()
					await cur.execute('SELECT xp FROM profile WHERE "user"=%s;', (ctx.author.id,))
					playerxp = await cur.fetchone()
					playerlevel = rpgtools.xptolevel(int(playerxp[0]))
					try:
						swordbonus = sword[5]
					except:
						swordbonus = 0
					try:
						shieldbonus = shield[6]
					except:
						shieldbonus = 0
					chances = []
					msg = await ctx.send("Loading images...")
					for row in alldungeons:
						success = rpgtools.calcchance(swordbonus, shieldbonus, row[2], int(playerlevel), returnsuccess=False)
						chances.append((success[0]-success[2], success[1]+success[2]))
					thing = functools.partial(makeadventures, chances)
					images = await self.bot.loop.run_in_executor(None, thing)
					#for afile in images:
					#	await ctx.send(file=discord.File(fp=afile, filename="Adventure.png"))
					await msg.delete()
					currentpage = 0
					maxpage = len(images)-1
					f = discord.File(images[currentpage], filename="Adventure.png")
					msg = await ctx.send(file=f, embed=discord.Embed().set_image(url="attachment://Adventure.png"))
					await msg.add_reaction("\U000023ee")
					await msg.add_reaction("\U000025c0")
					await msg.add_reaction("\U000025b6")
					await msg.add_reaction("\U000023ed")
					await msg.add_reaction("\U0001f522")
					def reactioncheck(reaction, user):
						return str(reaction.emoji) in ["\U000025c0","\U000025b6", "\U000023ee", "\U000023ed", "\U0001f522"] and reaction.message.id==msg.id and user.id==ctx.author.id
					def msgcheck(amsg):
						return amsg.channel == ctx.channel and not amsg.author.bot
					browsing = True
					while browsing:
						try:
							reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reactioncheck)
							if reaction.emoji == "\U000025c0":
								if currentpage == 0:
									pass
								else:
									currentpage -= 1
									await msg.delete()
									f = discord.File(images[currentpage], filename=f"Adventure.png")
									msg = await ctx.send(file=f, embed=discord.Embed().set_image(url="attachment://Adventure.png"))
								try:
									await msg.remove_reaction(reaction.emoji, user)
								except:
									pass
							elif reaction.emoji == "\U000025b6":
								if currentpage == maxpage:
									pass
								else:
									currentpage += 1
									await msg.delete()
									f = discord.File(images[currentpage], filename="Adventure.png")
									msg = await ctx.send(file=f, embed=discord.Embed().set_image(url="attachment://Adventure.png"))
								try:
									await msg.remove_reaction(reaction.emoji, user)
								except:
									pass
							elif reaction.emoji == "\U000023ed":
								currentpage = maxpage
								await msg.delete()
								f = discord.File(images[currentpage], filename="Adventure.png")
								msg = await ctx.send(file=f, embed=discord.Embed().set_image(url="attachment://Adventure.png"))
								try:
									await msg.remove_reaction(reaction.emoji, user)
								except:
									pass
							elif reaction.emoji == "\U000023ee":
								currentpage = 0
								await msg.delete()
								f = discord.File(images[currentpage], filename="Adventure.png")
								msg = await ctx.send(file=f, embed=discord.Embed().set_image(url="attachment://Adventure.png"))
								try:
									await msg.remove_reaction(reaction.emoji, user)
								except:
									pass
							elif reaction.emoji == "\U0001f522":
								question = await ctx.send(f"Enter a page number from `1` to `{maxpage+1}`")
								num = await self.bot.wait_for('message', timeout=10, check=msgcheck)
								if num is not None:
									try:
										num2 = int(num.content)
										if num2 >= 1 and num2 <= maxpage+1:
											currentpage = num2-1
											await msg.delete()
											f = discord.File(images[currentpage], filename="Adventure.png")
											msg = await ctx.send(file=f, embed=discord.Embed().set_image(url="attachment://Adventure.png"))
										else:
											mymsg = await ctx.send(f"Must be between `1` and `{maxpage+1}`.", delete_after=2)
										try:
											await num.delete()
										except:
											pass
									except:
										mymsg = await ctx.send("That is no number!", delete_after=2)
								await question.delete()
								try:
									await msg.remove_reaction(reaction.emoji, user)
								except:
									pass
							try:
								await msg.add_reaction("\U000023ee")
								await msg.add_reaction("\U000025c0")
								await msg.add_reaction("\U000025b6")
								await msg.add_reaction("\U000023ed")
								await msg.add_reaction("\U0001f522")
							except:
								pass
						except:
							browsing = False
							try:
								await msg.clear_reactions()
							except:
								pass
							finally:
								break



	@commands.command(aliases=["mission", "a", "dungeon"], description="Sends your character on an adventure.")
	async def adventure(self, ctx, dungeonnumber: int):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT * FROM profile WHERE "user"=%s;', (ctx.author.id,))
				except:
					await ctx.send("An error occured when fetching your character's data.")
				ret = []
				async for row in cur:
					ret.append(row)
				if ret==[]:
					await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to make your own character!")
				else:
					if dungeonnumber < 16 and dungeonnumber > 0:
						try:
							await cur.execute('SELECT * FROM mission WHERE "name"=%s;', (ctx.author.id,))
						except:
							await ctx.send("An error occured when fetching your current mission data")
						ret = []
						async for row in cur:
							ret.append(row)
						if ret==[]:
							times = {1: "30m", 2: "1h", 3: "2h", 4: "3h", 5: "4h", 6: "5h", 7: "6h", 8: "7h", 9: "8h", 10: "9h", 11: "10h", 12: "11h", 13: "12h", 14: "13h", 15: "14h"}
							booster_times = {1: "15m", 2: "30m", 3: "1h", 4: "1.5h", 5: "2h", 6: "2.5h", 7: "2.5h", 8: "3.5h", 9: "4h", 10: "4.5h", 11: "5h", 12: "5.5h", 13: "6h", 14: "6.5h", 15: "7h"}
							await cur.execute('SELECT "end" FROM boosters WHERE "user"=%s AND "type"=%s;', (ctx.author.id, 1))
							boostertest = await cur.fetchone()
							await cur.execute('SELECT "end" FROM boosters WHERE "user"=%s AND "type"=%s AND clock_timestamp() < "end";', (ctx.author.id, 1))
							boostertest2 = await cur.fetchone()
							if not boostertest and not boostertest2:
								await cur.execute("SELECT clock_timestamp() + interval %s;", (times[dungeonnumber],))
							elif boostertest and not boostertest2:
								await cur.execute('DELETE FROM boosters WHERE "user"=%s AND "type"=%s;', (ctx.author.id, 1))
								await cur.execute("SELECT clock_timestamp() + interval %s;", (times[dungeonnumber],))
							elif boostertest and boostertest2:
								await cur.execute("SELECT clock_timestamp() + interval %s;", (booster_times[dungeonnumber],))
							end = await cur.fetchone()
							await cur.execute('INSERT INTO mission ("name", "end", "dungeon") VALUES (%s, %s, %s);', (ctx.author.id, end[0], dungeonnumber))
							await ctx.send(f"Successfully sent your character out on an adventure. Use `{ctx.prefix}status` to see the current status of the mission.")
						else:
							await ctx.send(f"Your character is already on a mission! Use `{ctx.prefix}status` to see where and how long it still lasts.")
					else:
						await ctx.send("You entered an invalid Dungeon.")

	@commands.cooldown(1,3600,BucketType.user)
	@commands.command(description="Active Adventures.")
	async def activeadventure(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM profile WHERE "user"=%s;', (ctx.author.id,))
				profile = await cur.fetchone()
				if not profile:
					return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to start playing IdleRPG!")
				await cur.execute('SELECT * FROM mission WHERE "name"=%s;', (ctx.author.id,))
				current = await cur.fetchone()
				if current:
					ctx.command.reset_cooldown(ctx)
					return await ctx.send(f"Your character is already on a mission! Use `{ctx.prefix}status` to see where and how long it still lasts.")
				await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (ctx.author.id,))
				sword = await cur.fetchone()
				await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (ctx.author.id,))
				shield = await cur.fetchone()
		try:
			SWORD = sword[5]
		except:
			SWORD = 0
		try:
			SHIELD = shield[6]
		except:
			SHIELD = 0
			#class test
		SWORD, SHIELD = await genstats(self.bot, ctx.author.id, SWORD, SHIELD)
		SWORD = int(SWORD)
		SHIELD = int(SHIELD)
		HP = 100
		PROGRESS = 0 #percent

		def is_valid_move(msg):
			return msg.content.lower() in ["attack", "defend", "recover"] and msg.author == ctx.author

		ENEMY_HP = 100

		while PROGRESS < 100 and HP > 0:
			await ctx.send(f"""
**{ctx.author.display_name}'s Adventure**
```
Progress: {PROGRESS}%
HP......: {HP}

Enemy
HP......: {ENEMY_HP}

Use attack, defend or recover
```
""")
			try:
				res = await self.bot.wait_for('message', timeout=30, check=is_valid_move)
			except:
				return await ctx.send("Adventure stopped because you refused to move.")
			move = res.content.lower()
			enemymove = random.choice(["attack", "defend", "recover"])
			if move == "recover":
				HP += 20
				await ctx.send("You healed yourself for 20 HP.")
			if enemymove == "recover":
				ENEMY_HP += 20
				await ctx.send(f"The enemy healed himself for 20 HP.")
			if move == "attack" and enemymove == "defend":
				await ctx.send("Your attack was blocked!")
			if move == "defend" and enemymove == "attack":
				await ctx.send("Enemy attack was blocked!")
			if move == "defend" and enemymove == "defend":
				await ctx.send("Noone attacked.")
			if move == "attack" and enemymove == "attack":
				efficiency = random.randint(int(SWORD*0.5), int(SWORD*1.5))
				HP -= efficiency
				ENEMY_HP -= SWORD
				await ctx.send(f"You hit the enemy for **{SWORD}** damage, he hit you for **{efficiency}** damage.")
			elif move == "attack" and enemymove != "defend":
				ENEMY_HP -= SWORD
				await ctx.send(f"You hit the enemy for **{SWORD}** damage.")
			elif enemymove == "attack" and move == "recover":
				efficiency = random.randint(int(SWORD*0.5), int(SWORD*1.5))
				HP -= efficiency
				await ctx.send(f"The enemy hit you for **{efficiency}** damage.")
			if ENEMY_HP < 1:
				await ctx.send("Enemy defeated!")
				PROGRESS += random.randint(10,40)
				ENEMY_HP = 100

		if HP < 1:
			return await ctx.send("You died.")

		if SWORD < 26:
			maximumstat = random.randint(1,SWORD+5)
		else:
			maximumstat = random.randint(1,30)
		shieldorsword = random.choice(["Sword", "Shield"])
		names = ["Rare", "Ancient", "Normal", "Legendary", "Famous"]
		itemvalue = random.randint(1,250)
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				if shieldorsword == "Sword":
					itemname = random.choice(names)+random.choice([" Sword", " Blade", " Stich"])
					await cur.execute('INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES (%s, %s, %s, %s, %s, %s) RETURNING *;', (ctx.author.id, itemname, itemvalue, "Sword", maximumstat, 0.00))
				elif shieldorsword == "Shield":
					itemname = random.choice(names)+random.choice([" Shield", " Defender", " Aegis"])
					await cur.execute('INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES (%s, %s, %s, %s, %s, %s) RETURNING *;', (ctx.author.id, itemname, itemvalue, "Shield", 0.00, maximumstat))
				item = await cur.fetchone()
				await cur.execute('INSERT INTO inventory ("item", "equipped") VALUES (%s, %s);', (item[0], False))
		embed=discord.Embed(title="You gained an item!", description="You found a new item when finishing an active adventure!", color=0xff0000)
		embed.set_thumbnail(url=ctx.author.avatar_url)
		embed.add_field(name="ID", value=item[0], inline=False)
		embed.add_field(name="Name", value=itemname, inline=False)
		embed.add_field(name="Type", value=shieldorsword, inline=False)
		if shieldorsword == "Shield":
			embed.add_field(name="Damage", value="0.00", inline=True)
			embed.add_field(name="Armor", value=f"{maximumstat}.00", inline=True)
		else:
			embed.add_field(name="Damage", value=f"{maximumstat}.00", inline=True)
			embed.add_field(name="Armor", value="0.00", inline=True)
		embed.add_field(name="Value", value=f"${itemvalue}", inline=False)
		embed.set_footer(text=f"Your HP were {HP}")
		await ctx.send(embed=embed)

	@commands.command(aliases=["s"], description="Checks your character's adventure status.")
	async def status(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT * FROM mission WHERE "name"=%s;', (ctx.message.author.id,))
				except:
					await ctx.send("An error occured when fetching your mission data.")
				ret = []
				async for row in cur:
					ret.append(row)
				if ret==[]:
					await ctx.send(f"Either you haven't got a character or you aren't on a mission yet. Use `{ctx.prefix}create` to create a character or `{ctx.prefix}adventure [DungeonID]` to go out on an adventure!")
				else:
					await cur.execute('SELECT * FROM mission WHERE name=%s AND clock_timestamp() > "end";', (ctx.message.author.id,))
					isfinished = await cur.fetchone()
					if isfinished is not None:
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (ctx.author.id,))
						sword = await cur.fetchone()
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (ctx.author.id,))
						shield = await cur.fetchone()
						await cur.execute('SELECT xp FROM profile WHERE "user"=%s;', (ctx.author.id,))
						playerxp = await cur.fetchone()
						playerlevel = rpgtools.xptolevel(int(playerxp[0]))
						try:
							swordbonus = sword[5]
						except:
							swordbonus = 0
						try:
							shieldbonus = shield[6]
						except:
							shieldbonus = 0

						#class test
						swordbonus, shieldbonus = await genstats(self.bot, ctx.author.id, swordbonus, shieldbonus)

						await cur.execute('SELECT "end" FROM boosters WHERE "user"=%s AND "type"=%s;', (ctx.author.id, 2))
						boostertest = await cur.fetchone()
						await cur.execute('SELECT "end" FROM boosters WHERE "user"=%s AND "type"=%s AND clock_timestamp() < "end";', (ctx.author.id, 2))
						boostertest2 = await cur.fetchone()
						if not boostertest and not boostertest2:
							success = rpgtools.calcchance(swordbonus, shieldbonus, isfinished[3], int(playerlevel), returnsuccess=True)
						elif boostertest and not boostertest2:
							await cur.execute('DELETE FROM boosters WHERE "user"=%s AND "type"=%s;', (ctx.author.id, 2))
							success = rpgtools.calcchance(swordbonus, shieldbonus, isfinished[3], int(playerlevel), returnsuccess=True)
						elif boostertest and boostertest2:
							success = rpgtools.calcchance(swordbonus, shieldbonus, isfinished[3], int(playerlevel), returnsuccess=True, booster=True)
						if success:
							if isfinished[3] < 6:
								maximumstat = float(random.randint(1, isfinished[3]*5))
							else:
								maximumstat = float(random.randint(1, 25))
							await cur.execute('SELECT "end" FROM boosters WHERE "user"=%s AND "type"=%s;', (ctx.author.id, 3))
							boostertest = await cur.fetchone()
							await cur.execute('SELECT "end" FROM boosters WHERE "user"=%s AND "type"=%s AND clock_timestamp() < "end";', (ctx.author.id, 3))
							boostertest2 = await cur.fetchone()
							if not boostertest and not boostertest2:
								gold = random.randint(1,30)*isfinished[3]
							elif boostertest and not boostertest2:
								await cur.execute('DELETE FROM boosters WHERE "user"=%s AND "type"=%s;', (ctx.author.id, 3))
								gold = random.randint(1,30)*isfinished[3]
							elif boostertest and boostertest2:
								gold = int(random.randint(1,30)*isfinished[3]*1.25)
							xp = random.randint(200,1000)*isfinished[3]
							shieldorsword = random.choice(["sw", "sh"])
							names = ["Victo's", "Arsandor's", "Nuhulu's", "Legendary", "Vosag's", "Mitoa's", "Scofin's", "Skeeren's", "Ager's", "Hazuro's", "Atarbu's", "Jadea's", "Zosus'", "Thocubra's", "Utrice's", "Lingoad's", "Zlatorpian's"]
							if shieldorsword == "sw":
								await cur.execute('INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES (%s, %s, %s, %s, %s, %s) RETURNING *;', (ctx.author.id, random.choice(names)+random.choice([" Sword", " Blade", " Stich"]), random.randint(1,40)*isfinished[3], "Sword", maximumstat, 0.00))
							if shieldorsword == "sh":
								await cur.execute('INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES (%s, %s, %s, %s, %s, %s) RETURNING *;', (ctx.author.id, random.choice(names)+random.choice([" Shield", " Defender", " Aegis"]), random.randint(1,40)*isfinished[3], "Shield", 0.00, maximumstat))
							item = await cur.fetchone()
							await cur.execute('INSERT INTO inventory ("item", "equipped") VALUES (%s, %s);', (item[0], False))
							#marriage partner should get 50% of the money
							await cur.execute('SELECT marriage FROM profile WHERE "user"=%s;', (ctx.author.id,))
							partner = await cur.fetchone()
							if partner[0] != 0:
								await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (int(gold/2), partner[0]))
							#guild money
							await cur.execute('SELECT guild FROM profile WHERE "user"=%s;', (ctx.author.id,))
							guild = await cur.fetchone()
							await cur.execute('UPDATE guild SET money=money+%s WHERE "id"=%s;', (int(gold/10), guild[0]))
							
							await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (gold, ctx.author.id))
							await cur.execute('UPDATE profile SET xp=xp+%s WHERE "user"=%s;', (xp, ctx.author.id))
							await cur.execute('UPDATE profile SET completed=completed+1 WHERE "user"=%s;', (ctx.author.id,))
							if partner[0] == 0:
								await ctx.send(f"You have completed your dungeon and received **${gold}** as well as a new weapon: **{item[2]}**. Experience gained: **{xp}**.")
							else:
								await ctx.send(f"You have completed your dungeon and received **${gold}** as well as a new weapon: **{item[2]}**. Experience gained: **{xp}**.\nYour partner received **${int(gold/2)}**.")
						else:
							await ctx.send("You died on your mission. Try again!")
							await cur.execute('UPDATE profile SET deaths=deaths+1 WHERE "user"=%s;', (ctx.author.id,))
						await cur.execute('DELETE FROM mission WHERE "name"=%s;', (ctx.author.id,))
					else:
						await cur.execute('SELECT * FROM mission WHERE name=%s AND clock_timestamp() < "end";', (ctx.author.id,))
						mission = await cur.fetchone()
						await cur.execute("SELECT %s-clock_timestamp();", (mission[2],))
						remain = await cur.fetchone()
						await cur.execute("SELECT * FROM dungeon WHERE id=%s;", (mission[3],))
						dungeon = await cur.fetchone()
						await ctx.send(f"You are currently in the adventure with difficulty `{mission[3]}`.\nApproximate end in `{str(remain[0]).split('.')[0]}`\nDungeon Name: `{dungeon[1]}`")

	@commands.command(description="Cancels your current mission.")
	async def cancel(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM mission WHERE "name"=%s;', (ctx.author.id,))
				ret = []
				async for row in cur:
					ret.append(row)
				if ret==[]:
					await ctx.send("You are on no mission.")
				else:
					await cur.execute('DELETE FROM mission WHERE "name"=%s;', (ctx.author.id,))
					await ctx.send(f"Canceled your mission. Use `{ctx.prefix}adventure [missionID]` to start a new one!")


	@commands.command(description="Your death stats.")
	async def deaths(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT deaths, completed FROM profile WHERE "user"=%s;', (ctx.author.id,))
				stats = await cur.fetchone()
				if not stats:
					return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to start playing IdleRPG.")
				deaths, completed = stats
				try:
					rate = round(completed/(deaths+completed)*100, 2)
				except:
					return await ctx.send(f"You died **{deaths}** times.")
				await ctx.send(f"Out of **{deaths+completed}** adventures, you died **{deaths}** times and survived **{completed}** times, which is a success rate of **{rate}%**.")

def setup(bot):
	bot.add_cog(Adventure(bot))

