import discord, functools, traceback
from discord.ext import commands
from cogs.rpgtools import profile_image
import cogs.rpgtools as rpgtools
from cogs.help import chunks
from discord.ext.commands import BucketType
from io import BytesIO, StringIO
from PIL import Image, ImageFont, ImageDraw
import io
from cogs.classes import genstats
from pathlib import Path



class Profile:

	def __init__(self, bot):
		self.bot = bot

	@commands.cooldown(1,3600,BucketType.user)
	@commands.command(aliases=["new", "c", "start"], description="Creates a new character.")
	async def create(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT user from profile WHERE "user"=%s;', (ctx.author.id,))
				except:
					return await ctx.send("An error occured while checking your profile in the database.")
				check = await cur.fetchone()
		if check:
			return await ctx.send(f"You already own a character. Use `{ctx.prefix}profile` to view them!")
		await ctx.send("What shall your character's name be? (Minimum 3 Characters, Maximum 20)")
		def mycheck(amsg):
			return amsg.author==ctx.author
		try:
			name = await self.bot.wait_for('message', timeout=60, check=mycheck)
		except:
			ctx.command.reset_cooldown(ctx)
			return await ctx.send(f"Timeout expired. Enter `{ctx.prefix}{ctx.command}` again to retry!")
		name = name.content.strip()
		if len(name)>2 and len(name)<21:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					await cur.execute("INSERT INTO profile VALUES (%s, %s, %s, %s);", (ctx.author.id, name, 100, 0))
					await cur.execute("INSERT INTO allitems (owner, name, value, type, damage, armor) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;", (ctx.author.id, "Starter Sword", 0, "Sword", 3.0, 0.0))
					itemid = (await cur.fetchone())[0]
					await cur.execute("INSERT INTO inventory (item, equipped) VALUES (%s, %s);", (itemid, True))
					await cur.execute("INSERT INTO allitems (owner, name, value, type, damage, armor) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;", (ctx.author.id, "Starter Shield", 0, "Shield", 0.0, 3.0))
					itemid = (await cur.fetchone())[0]
					await cur.execute("INSERT INTO inventory (item, equipped) VALUES (%s, %s);", (itemid, True))
					await ctx.send(f"Successfully added your character **{name}**! Now use `{ctx.prefix}profile` to view your character!")
		elif len(name)<3:
			await ctx.send("Character names must be at least 3 characters!")
			ctx.command.reset_cooldown(ctx)
		elif len(name)>20:
			await ctx.send("Character names mustn't exceed 20 characters!")
			ctx.command.reset_cooldown(ctx)
		else:
			await ctx.send("An unknown error occured while checking your name. Try again!")



	@commands.command(aliases=["me", "p"], description="View your or a different user's profile.")
	async def profile(self, ctx, person: discord.User=None):
		await ctx.trigger_typing()
		person = person or ctx.author
		targetid = person.id
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					ranks = []
					await cur.execute('SELECT colour FROM profile WHERE "user"=%s;', (targetid,))
					color = (await cur.fetchone())[0]
					await cur.execute('SELECT * FROM profile WHERE "user"=%s;', (targetid,))
					profile = await cur.fetchone()
					await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (targetid,))
					sword = await cur.fetchone()
					await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (targetid,))
					shield = await cur.fetchone()
					await cur.execute("SELECT position FROM (SELECT profile.*, ROW_NUMBER() OVER(ORDER BY profile.money DESC) AS position FROM profile) s WHERE s.user = %s;", (targetid,))
					async for row in cur:
						ranks.append(row[0])
					await cur.execute("SELECT position FROM (SELECT profile.*, ROW_NUMBER() OVER(ORDER BY profile.xp DESC) AS position FROM profile) s WHERE s.user = %s;", (targetid,))
					async for row in cur:
						ranks.append(row[0])
					await cur.execute('SELECT * FROM mission WHERE "name"=%s;', (targetid,))
					mission = await cur.fetchone()
					await cur.execute('SELECT name FROM guild WHERE "id"=%s;', (profile[12],))
					guild = await cur.fetchone()
					if not mission:
						mission = []
					missionend = []
					if mission != []:
						await cur.execute('SELECT %s-clock_timestamp();', (mission[2],))
						missionend = (await cur.fetchone())[0]
					await cur.execute('SELECT background FROM profile WHERE "user"=%s;', (targetid,))
					background = (await cur.fetchone())[0]
					if background == "0":
						background = "Profile.png"
					else:
						async with self.bot.session.get(background) as r:
							background = BytesIO(await r.read())
							background.seek(0)
					if str(profile[9]) != "0":
						marriage = (await rpgtools.lookup(self.bot, profile[9])).split("#")[0]
					else:
						marriage = "Not married"

					try:
						sword = [sword[2], sword[5]]
					except:
						sword = ["None equipped", 0.00]
					try:
						shield = [shield[2], shield[6]]
					except:
						shield = ["None equipped", 0.00]

					damage, armor = await genstats(self.bot, targetid, sword[1], shield[1])
					damage -= sword[1]
					armor -= shield[1]
					extras = (damage, armor)

				except:
					pass
		if not profile:
			return await ctx.send("No character data found.")
		thing = functools.partial(profile_image, profile, sword, shield, mission, missionend, ranks, color, background, marriage, guild, extras)
		output_buffer = await self.bot.loop.run_in_executor(None, thing)
		await ctx.send(file=discord.File(fp=output_buffer, filename="Profile.png"))



	@commands.command(aliases=["money", "e"], description="Shows your current balance.")
	async def economy(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
				except:
					await ctx.send("An error occured when fetching your character's data.")
				money = await cur.fetchone()
		if not money:
			return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to make your own character!")
		await ctx.send(f"You currently have **${money[0]}**, {ctx.author.mention}!")

	@commands.command(description="Shows your current XP count.")
	async def xp(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT xp FROM profile WHERE "user"=%s;', (ctx.author.id,))
				except:
					await ctx.send("An error occured when fetching your character's data.")
				points = await cur.fetchone()
		if not points:
			return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to make your own character!")
		points = points[0]
		await ctx.send(f"You currently have **{points} XP**, which means you are on Level **{rpgtools.xptolevel(points)}**. Missing to next level: **{rpgtools.xptonextlevel(points)}**")

	async def invembed(self, ret):
		result = discord.Embed(title="Your inventory includes", colour=discord.Colour.blurple())
		for weapon in ret:
			if weapon[7] == True:
				eq = "(**Equipped**)"
			else:
				eq = ""
			result.add_field(name=f"{weapon[2]} {eq}", value=f"ID: `{weapon[0]}`, Type: `{weapon[4]}` with Damage: `{weapon[5]}` and Armor: `{weapon[6]}`. Value is **${weapon[3]}**")
		return result

	@commands.command(aliases=["inv", "i"], description="Shows your current inventory.")
	async def inventory(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute("SELECT ai.*, i.equipped FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE p.user=%s ORDER BY i.equipped DESC;", (ctx.author.id,))
				except:
					await ctx.send("An error occured when fetching your profile")
				ret = []
				async for row in cur:
					ret.append(row)
		if ret==[]:
			await ctx.send(f"Either your inventory is empty or no character has been created yet. Use `{ctx.prefix}create` to be the first one!")
		else:
			allitems = list(chunks(ret, 5))
			currentpage = 0
			maxpage = len(allitems)-1
			result = await self.invembed(allitems[currentpage])
			result.set_footer(text=f"Page {currentpage+1} of {maxpage+1}")
			msg = await ctx.send(embed=result)
			if maxpage == 0:
				return
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
							result = await self.invembed(allitems[currentpage])
							result.set_footer(text=f"Page {currentpage+1} of {maxpage+1}")
							await msg.edit(embed=result)
						try:
							await msg.remove_reaction(reaction.emoji, user)
						except:
							pass
					elif reaction.emoji == "\U000025b6":
						if currentpage == maxpage:
							pass
						else:
							currentpage += 1
							result = await self.invembed(allitems[currentpage])
							result.set_footer(text=f"Page {currentpage+1} of {maxpage+1}")
							await msg.edit(embed=result)
						try:
							await msg.remove_reaction(reaction.emoji, user)
						except:
							pass
					elif reaction.emoji == "\U000023ed":
						currentpage = maxpage
						result = await self.invembed(allitems[currentpage])
						result.set_footer(text=f"Page {currentpage+1} of {maxpage+1}")
						await msg.edit(embed=result)
						try:
							await msg.remove_reaction(reaction.emoji, user)
						except:
							pass
					elif reaction.emoji == "\U000023ee":
						currentpage = 0
						result = await self.invembed(allitems[currentpage])
						result.set_footer(text=f"Page {currentpage+1} of {maxpage+1}")
						await msg.edit(embed=result)
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
									result = await self.invembed(allitems[currentpage])
									result.set_footer(text=f"Page {currentpage+1} of {maxpage+1}")
									await msg.edit(embed=result)
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
				except:
					browsing = False
					try:
						await msg.clear_reactions()
					except:
						pass
					finally:
						break


	@commands.command(aliases=["use"], description="Equips the item with the given ID.")
	async def equip(self, ctx, itemid: int):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.owner=%s;', (ctx.author.id,))
				ret = []
				async for row in cur:
					ret.append(row)
				if ret==[]:
					await ctx.send(f"Either you haven't got a character or your inventory is empty. Use `{ctx.prefix}create` to create a new character.")
				else:
					ids = []
					for item in ret:
						ids.append(item[1])
					if itemid in ids:
						await cur.execute('SELECT type FROM allitems WHERE "id"=%s;', (itemid,))
						itemtype = await cur.fetchone()
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type=%s;", (ctx.author.id, itemtype))
						olditem = await cur.fetchone()
						if olditem is not None:
							await cur.execute('UPDATE inventory SET "equipped"=False WHERE "item"=%s;', (olditem[0],))
						await cur.execute('UPDATE inventory SET "equipped"=True WHERE "item"=%s;', (itemid,))
						if olditem is not None:
							await ctx.send(f"Successfully equipped item `{itemid}` and put off item `{olditem[0]}`.")
						else:
							await ctx.send(f"Successfully equipped item `{itemid}`.")
					else:
						await ctx.send(f"You don't own an item with the ID `{itemid}`.")

	@commands.cooldown(1,60,BucketType.user)
	@commands.command(aliases=["upgrade"], description="Upgrades an item's stat by 1.")
	async def upgradeweapon(self, ctx, itemid: int):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM allitems WHERE "id"=%s AND "owner"=%s;', (itemid, ctx.author.id))
				item = await cur.fetchone()
				if not item:
					return await ctx.send(f"You don't own an item with the ID `{itemid}`.")
				if item[4] == "Sword":
					stattoupgrade = "damage"
					statid = 5
					pricetopay = int(item[5] * 250)
				elif item[4] == "Shield":
					stattoupgrade = "armor"
					statid = 6
					pricetopay = int(item[6] * 250)
				if int(item[statid]) > 40:
					return await ctx.send("Your weapon already reached the maximum upgrade level.")
				await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
				usermoney = (await cur.fetchone())[0]
		if usermoney < pricetopay:
			return await ctx.send(f"You are too poor to upgrade this item. The upgrade costs **${pricetopay}**, but you only have **${usermoney}**.")
		def check(m):
			return m.content.lower() == "confirm" and m.author == ctx.author
		await ctx.send(f"Are you sure? Type `confirm` to improve your weapon for **${pricetopay}**")
		try:
			await self.bot.wait_for('message', check=check, timeout=30)
		except:
			ctx.command.reset_cooldown(ctx)
			return await ctx.send("Weapon upgrade cancelled.")
		ctx.command.reset_cooldown(ctx)
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute(f'UPDATE allitems SET {stattoupgrade}={stattoupgrade}+1 WHERE "id"=%s;', (itemid,))
				await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (pricetopay, ctx.author.id))
		await ctx.send(f'The {stattoupgrade} of your **{item[2]}** is now **{int(item[statid])+1}**. **${pricetopay}** has been taken off your balance.') 


	@commands.command(description="Gift money!")
	async def give(self, ctx, money: int, other: discord.Member=None):
		if money < 0:
			await ctx.send("Don't scam!")
			return
		if other is None:
			await ctx.send("Uh, you entered no Member! Use a mention!")
			return
		if other == ctx.author:
			await ctx.send("No cheating!")
			return
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
					money1 = await cur.fetchone()
					if money1[0]<money:
						await ctx.send("You are too poor.")
						return
					await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (money, ctx.author.id))
					await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (money, other.id))
					await ctx.send(f"Successfully gave **${money}** to {other.mention}.")
				except:
					await ctx.send("Either you or the other person don't have a character.")

	@commands.command(description="Changes your character name")
	async def rename(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute('SELECT * from profile WHERE "user"=%s;', (ctx.author.id,))
				except:
					await ctx.send("An error occured when fetching your character's data.")
				check = await cur.fetchone()
		if not check:
			return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to make your own character!")
		await ctx.send("What shall your character's name be? (Minimum 3 Characters, Maximum 20)")
		try:
			def mycheck(amsg):
				return amsg.author==ctx.author
			name = await self.bot.wait_for('message', timeout=60, check=mycheck)
			name = name.content.strip()
			if len(name)>2 and len(name) < 21:
				async with self.bot.pool.acquire() as conn:
					async with conn.cursor() as cur:
						await cur.execute('UPDATE profile SET "name"=%s WHERE "user"=%s;', (name, ctx.author.id,))
				await ctx.send("Character name updated.")
			elif len(name) < 3:
				await ctx.send("Character names must be at least 3 characters!")
			elif len(name) > 20:
				await ctx.send("Character names mustn't exceed 20 characters!")
			else:
				await ctx.send("An unknown error occured while checking your name. Try again!")
		except:
			await ctx.send(f"Timeout expired. Enter `{ctx.prefix}{ctx.command}` again to retry!")

	@commands.command(aliases=["rm", "del"], description="Deletes your character.")
	async def delete(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM profile WHERE "user"=%s;', (ctx.author.id,))
				check = await cur.fetchone()
		if not check:
			return await ctx.send(f"You haven't got a character yet. Use `{ctx.prefix}create` to create a new character.")
		def mycheck(amsg):
			return amsg.content.strip()=="deletion confirm" and amsg.author==ctx.author
		await ctx.send("Are you sure? Type `deletion confirm` in the next 15 seconds to confirm.")
		try:
			res = await self.bot.wait_for('message', timeout=15, check=mycheck)
		except:
			return await ctx.send("Cancelled deletion of your character.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('DELETE FROM profile WHERE "user"=%s;', (ctx.author.id,))
		await ctx.send("Successfully deleted your character. Sorry to see you go :frowning:")

	@commands.command(aliases=["color"], description="Set your default text colour for the profile command.")
	async def colour(self, ctx, colour: str):
		if len(colour) != 7 or not colour.startswith("#"):
			return await ctx.send("Format for colour is `#RRGGBB`.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('UPDATE profile SET "colour"=%s WHERE "user"=%s;', (colour, ctx.author.id))
		await ctx.send(f"Successfully set your profile colour to `{colour}`.")

def setup(bot):
	bot.add_cog(Profile(bot))
