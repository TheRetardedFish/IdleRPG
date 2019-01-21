import discord, traceback
from discord.ext import commands
import cogs.rpgtools as rpgtools
from discord.ext.commands import BucketType
import random

class Trading:

	def __init__(self, bot):
		self.bot = bot

	@commands.command(description="Sells the item with the given ID for the given price.")
	async def sell(self, ctx, itemid: int, price: int):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute("SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=%s AND ai.owner=%s;", (itemid, ctx.author.id))
				ret = await cur.fetchone()
				if not ret:
					return await ctx.send(f"You don't own an item with the ID: {itemid}")
				if int(ret[8])==0 and int(ret[9])<=3:
					return await ctx.send("Your item is either equal to a Starter Item or worse. Noone would buy it.")
				elif int(ret[9])==0 and int(ret[8])<=3:
					return await ctx.send("Your item is either equal to a Starter Item or worse. Noone would buy it.")
				elif price > ret[6]*50:
					return await ctx.send(f"Your price is too high. Try adjusting it to be up to `{ret[6]*50}`.")
				elif price < 1:
					return await ctx.send("You can't sell it for free or a negative price.")
				await cur.execute("DELETE FROM inventory i USING allitems ai WHERE i.item=ai.id AND ai.id=%s AND ai.owner=%s;", (itemid, ctx.author.id))
				await cur.execute("INSERT INTO market (item, price) VALUES (%s, %s);", (itemid, price))
				await ctx.send(f"Successfully added your item to the shop! Use `{ctx.prefix}shop` to view it in the market!")


	@commands.command(aliases=["b"], description="Buys an item with the given ID.")
	async def buy(self, ctx, itemid: int):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute("SELECT * FROM market m JOIN allitems ai ON (m.item=ai.id) WHERE ai.id=%s;", (itemid,))
				item = []
				async for row in cur:
					item.append(row)
				if item==[]:
					await ctx.send(f"There is no item in the shop with the ID: {itemid}")
				else:
					await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
					ret = []
					async for row in cur:
						ret.append(row)
					if ret==[]:
						await ctx.send(f"You don't have a character yet. Use `{ctx.prefix}create` to make one!")
					else:
						if ret[0][0]>item[0][2] or ret[0][0]==item[0][2]:
							await cur.execute("DELETE FROM market m USING allitems ai WHERE m.item=ai.id AND ai.id=%s AND ai.owner=%s RETURNING *;", (itemid, item[0][4]))
							deleted = await cur.fetchone()
							await cur.execute("UPDATE allitems SET owner=%s WHERE id=%s;", (ctx.author.id, deleted[3]))
							await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (deleted[2], deleted[4]))
							await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (deleted[2], ctx.author.id))
							await cur.execute("INSERT INTO inventory (item, equipped) VALUES (%s, %s);", (deleted[3], False))
							await ctx.send(f"Successfully bought item `{deleted[3]}`. Use `{ctx.prefix}inventory` to view your updated inventory.")
						else:
							await ctx.send(f"You don't have enough money. The item costs **${item[0][2]}**, you only have **${ret[0][0]}**!")

	@commands.command(description="Takes an item off the shop.")
	async def remove(self, ctx, itemid):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute("SELECT * FROM market m JOIN allitems ai ON (m.item=ai.id) WHERE ai.id=%s AND ai.owner=%s;", (itemid, ctx.author.id))
				item = await cur.fetchone()
				if not item:
					return await ctx.send(f"You don't have an item of yours in the shop with the ID `{itemid}`.")
				await cur.execute("DELETE FROM market m USING allitems ai WHERE m.item=ai.id AND ai.id=%s AND ai.owner=%s RETURNING *;", (itemid, ctx.author.id))
				deleted = await cur.fetchone()
				await cur.execute("INSERT INTO inventory (item, equipped) VALUES (%s, %s);", (itemid, False))
				await ctx.send(f"Successfully remove item `{itemid}` from the shop and put it in your inventory.")



	@commands.command(aliases=["market", "m"], description="Show the market with all items and prices.")
	async def shop(self, ctx, itemtype:str="All", minstat:float=0.00, highestprice:int=10000):
		itemtype = itemtype.title()
		if itemtype not in ["All", "Sword", "Shield"]:
			return await ctx.send("Use either `all`, `Sword` or `Shield` as a type to filter for.")
		if highestprice < 0:
			return await ctx.send("Price must be minimum 0.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				if itemtype == "All":
					await cur.execute('SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE m."price"<%s AND (ai."damage">=%s OR ai."armor">=%s);', (highestprice, minstat, minstat))
				elif itemtype == "Sword":
					await cur.execute('SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE ai."type"=%s AND ai."damage">=%s AND m."price"<%s;', (itemtype, minstat, highestprice))
				elif itemtype == "Shield":
					await cur.execute('SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE ai."type"=%s AND ai."armor">=%s AND m."price"<%s;', (itemtype, minstat, highestprice))
				ret = []
				async for row in cur:
					ret.append(row)
		if ret==[]:
			await ctx.send("The shop is currently empty.")
		else:
			maxpages = len(ret)
			currentpage = 1
			charname = await rpgtools.lookup(self.bot, ret[currentpage-1][1])
			msg = await ctx.send(f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item.")
			await msg.add_reaction("\U000023ee")
			await msg.add_reaction("\U000025c0")
			await msg.add_reaction("\U000025b6")
			await msg.add_reaction("\U000023ed")
			await msg.add_reaction("\U0001f522")
			shopactive = True
			def reactioncheck(reaction, user):
				return str(reaction.emoji) in ["\U000025c0","\U000025b6", "\U000023ee", "\U000023ed", "\U0001f522"] and reaction.message.id==msg.id and user!=self.bot.user
			def msgcheck(amsg):
				return amsg.channel == ctx.channel and not amsg.author.bot
			while shopactive:
				try:
					reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reactioncheck)
					if reaction.emoji == "\U000025c0":
						if currentpage == 1:
							pass
						else:
							currentpage -= 1
							charname = await rpgtools.lookup(self.bot, ret[currentpage-1][1])
							await msg.edit(content=f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item.")
						try:
							await msg.remove_reaction(reaction.emoji, user)
						except:
							pass
					elif reaction.emoji == "\U000025b6":
						if currentpage == maxpages:
							pass
						else:
							currentpage += 1
							charname = await rpgtools.lookup(self.bot, ret[currentpage-1][1])
							await msg.edit(content=f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item.")
						try:
							await msg.remove_reaction(reaction.emoji, user)
						except:
							pass
					elif reaction.emoji == "\U000023ee":
						currentpage = 1
						charname = await rpgtools.lookup(self.bot, ret[currentpage-1][1])
						await msg.edit(content=f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item.")
						try:
							await msg.remove_reaction(reaction.emoji, user)
						except:
							pass
					elif reaction.emoji == "\U000023ed":
						currentpage = maxpages
						charname = await rpgtools.lookup(self.bot, ret[currentpage-1][1])
						await msg.edit(content=f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item.")
						try:
							await msg.remove_reaction(reaction.emoji, user)
						except:
							pass
					elif reaction.emoji == "\U0001f522":
						question = await ctx.send(f"Enter a page number from `1` to `{maxpages}`")
						num = await self.bot.wait_for('message', timeout=10, check=msgcheck)
						if num == None:
							await question.delete()
						else:
							try:
								num2 = int(num.content)
								if num2 >= 1 and num2 <= maxpages:
									currentpage = num2
									charname = await rpgtools.lookup(self.bot, ret[currentpage-1][1])
									await msg.edit(content=f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item.")
								else:
									mymsg = await ctx.send(f"Must be between `1` and `{maxpages}`.", delete_after=2)
								try:
									await num.delete()
								except:
									pass
							except:
								mymsg = await ctx.send("That is no number!", delete_after=2)
								try:
									await num.delete()
								except:
									pass
						await question.delete()
						try:
							await msg.remove_reaction(reaction.emoji, user)
						except:
							pass
				except:
					shopactive = False
					try:
						await msg.clear_reactions()
					except:
						pass
					finally:
						break

	@commands.cooldown(1,120,BucketType.channel)
	@commands.command(description="Offer an item to a specific user.")
	async def offer(self, ctx, itemid: int, price: int, user:discord.Member=None):
		if price<0:
			return await ctx.send("Don't scam!")
		if not user:
			return await ctx.send("You have to specify a user. Use a mention!")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute("SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=%s AND ai.owner=%s;", (itemid, ctx.author.id))
				ret = []
				async for row in cur:
					ret.append(row)
				if ret==[]:
					await ctx.send(f"You don't have an item with the ID `{itemid}`.")
					return
				if ret[0][2]:
					def check(m):
						return m.content.lower() == "confirm" and m.author == ctx.author
					await ctx.send("Are you sure you want to sell your equipped item? Type `confirm` to sell it")
					try:
						await self.bot.wait_for('message', check=check, timeout=30)
					except:
						return await ctx.send("Item selling cancelled.")

				await ctx.send(f"{user.mention}, {ctx.author.mention} offered you an item! Write `buy @{str(ctx.author)}` to buy it! The price is **${price}**. You have **2 Minutes** to accept the trade or the offer will be canceled.")
				waiting = True
				def msgcheck(amsg):
					return (amsg.content.strip()==f"buy <@{ctx.author.id}>" or amsg.content.strip()==f"buy <@!{ctx.author.id}>") and amsg.author==user
		while waiting:
			try:
				res = await self.bot.wait_for('message', timeout=120, check=msgcheck)
				async with self.bot.pool.acquire() as conn:
					async with conn.cursor() as cur:
						await cur.execute('SELECT money FROM profile WHERE "user"=%s AND "money">=%s;', (user.id, price))
						othermoney = await cur.fetchone()
						if not othermoney:
							await ctx.send("You don't have enough money to buy the item. You still have time left to get some money and buy it!")
							continue
						waiting=False
						await cur.execute("SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=%s AND ai.owner=%s;", (itemid, ctx.author.id))
						ret = []
						async for row in cur:
							ret.append(row)
						if ret==[]:
							return await ctx.send(f"The owner sold the item with the ID `{itemid}` in the meantime.")
						await cur.execute("SELECT * FROM allitems ai WHERE ai.id=%s;", (itemid,))
						item = []
						async for row in cur:
							item.append(row)
						await cur.execute("UPDATE allitems SET owner=%s WHERE id=%s;", (user.id, itemid))
						await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (price, ctx.author.id))
						await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (price, user.id))
						await cur.execute('UPDATE inventory SET "equipped"=%s WHERE "item"=%s;', (False, itemid))
						await ctx.send(f"Successfully bought item `{itemid}`. Use `{ctx.prefix}inventory` to view your updated inventory.")
			except:
				return await ctx.send(f"{user.mention} didn't want to buy your item, {ctx.author.mention}. Try again later!")

	@commands.command(aliases=["merch"], description="Sells an item for its value.")
	async def merchant(self, ctx, itemid: int):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute("SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=%s AND ai.owner=%s;", (itemid, ctx.author.id))
				item = await cur.fetchone()
				if not item:
					await ctx.send(f"You don't own an item with the ID: {itemid}")
				else:
					await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (item[6], ctx.author.id))
					await cur.execute('DELETE FROM allitems WHERE "id"=%s;', (itemid,))
					await ctx.send(f"You received **${item[6]}** when selling item `{itemid}`.")

	@commands.command(description="Views your pending shop items.")
	async def pending(self, ctx):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT * FROM allitems ai JOIN market m ON (m.item=ai.id) WHERE ai."owner"=%s;', (ctx.author.id,))
				ret = []
				async for row in cur:
					ret.append(row)
		if ret == []:
			return await ctx.send("You don't have any pending shop offers.")
		p = "**Your current shop offers**\n"
		for row in ret:
			p += f"A **{row[2]}** (ID: `{row[0]}`) with damage `{row[5]}` and armor `{row[6]}`. Value is **${row[3]}**, market price is **${row[9]}**.\n"
		await ctx.send(p)

	@commands.cooldown(1,3600,BucketType.user)
	@commands.command(description="Buy items at the trader.")
	async def trader(self, ctx):
		# [type, damage, armor, value (0), name, price]
		offers = []
		for i in range(5):
			name = random.choice(["Normal ", "Ugly ", "Useless ", "Premade ", "Handsmith "])
			type = random.choice(["Sword", "Shield"])
			name = name + random.choice(["Blade", "Stich", "Sword"]) if type == "Sword" else name
			name= name + random.choice(["Defender", "Aegis", "Buckler"]) if type == "Shield" else name
			damage = random.randint(1,15) if type == "Sword" else 0
			armor = random.randint(1,15) if type == "Shield" else 0
			price = armor * 50 + damage * 50
			offers.append([type, damage, armor, 0, name, price])
		nl = "\n"
		await ctx.send(f"""
**The trader offers once per hour:**
{nl.join([str(offers.index(w)+1)+") Type: `"+w[0]+"` Damage: `"+str(w[1])+".00` Armor: `"+str(w[2])+".00` Name: `"+w[4]+"` Price: **$"+str(w[5])+"**" for w in offers])}

Type `trader buy offerid` in the next 30 seconds to buy something
""")
		def check(msg):
			return msg.content.lower().startswith("trader buy") and msg.author == ctx.author

		try:
			msg = await self.bot.wait_for("message", check=check, timeout=30)
		except:
			return

		try:
			offerid = int(msg.content.split()[-1])
		except:
			return await ctx.send("Unknown offer")
		if offerid < 1 or offerid > 5:
			return await ctx.send("Unknown offer")
		offerid = offerid -1
		item = offers[offerid]
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
				money = await cur.fetchone()
				if not money:
					return await ctx.send("You haven't got a character yet.")
				elif money[0] < item[5]:
					return await ctx.send(f"The item costs **${item[5]}**, you only have **${money[0]}**.")
				await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (item[5], ctx.author.id))
				await cur.execute('INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES (%s, %s, %s, %s, %s, %s) RETURNING *;', (ctx.author.id, item[4], 0, item[0], item[1], item[2]))
				itemid = (await cur.fetchone())[0]
				await cur.execute('INSERT INTO inventory ("item", "equipped") VALUES (%s, %s);', (itemid, False))
		await ctx.send(f"Successfully bought offer **{offerid+1}**. Use `{ctx.prefix}inventory` to view your updated inventory.")

def setup(bot):
	bot.add_cog(Trading(bot))
