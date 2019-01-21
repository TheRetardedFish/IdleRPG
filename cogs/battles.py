import discord, asyncio, random
from discord.ext import commands
from discord.ext.commands import BucketType
import traceback

class Battles:

	def __init__(self, bot):
		self.bot = bot


	@commands.cooldown(1,90,BucketType.user)
	@commands.command(pass_context=True, description="Battle yourself for the money you choose.")
	async def battle(self, ctx, money: int, enemy:discord.Member=None):
		if money<0:
			return await ctx.send("Don't scam!")
		if enemy:
			if enemy.id == ctx.author.id:
				return await ctx.send("You can't battle yourself.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT money FROM profile WHERE "user"=%s AND "money">=%s;', (ctx.message.author.id, money))
				ret = await cur.fetchone()
				if not ret:
					return await ctx.send("You don't have that much money!")
		if enemy is None:
			await ctx.send(f"{ctx.author.mention} seeks a battle! Write `join @{str(ctx.author)}` now to duel him! The price is **${money}**.")
		else:
			await ctx.send(f"{ctx.author.mention} seeks a battle with {enemy.mention}! Write `private join @{str(ctx.author)}` now to duel him! The price is **${money}**.")
		seeking = True
		def allcheck(amsg):
			return (amsg.content.strip()==f"join <@{ctx.author.id}>" or amsg.content.strip()==f"join <@!{ctx.author.id}>") and amsg.author.id != ctx.author.id
		def privatecheck(amsg):
			return (amsg.content.strip()==f"private join <@{ctx.author.id}>" or amsg.content.strip()==f"private join <@!{ctx.author.id}>") and amsg.author.id==enemy.id
		while seeking:
			try:
				if enemy is None:
					res = await self.bot.wait_for('message', timeout=60, check=allcheck)
				else:
					res = await self.bot.wait_for('message', timeout=60, check=privatecheck)
				async with self.bot.pool.acquire() as conn:
					async with conn.cursor() as cur:
						await cur.execute('SELECT money FROM profile WHERE "user"=%s AND "money">=%s;', (res.author.id, money))
						othermoney = await cur.fetchone()
						if not othermoney:
							await ctx.send("You don't have enough money to join the battle.")
							continue
				seeking = False
				await ctx.send(f"Battle **{ctx.message.author.name}** vs **{res.author.name}** started! 30 seconds of fighting will now start!")
				await asyncio.sleep(30)
				async with self.bot.pool.acquire() as conn:
					async with conn.cursor() as cur:
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (ctx.author.id,))
						sword1 = await cur.fetchone()
						try:
							sw1 = sword1[5]
						except:
							sw1 = 0
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (ctx.author.id,))
						shield1 = await cur.fetchone()
						try:
							sh1 = shield1[6]
						except:
							sh1 = 0
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (res.author.id,))
						sword2 = await cur.fetchone()
						try:
							sw2 = sword2[5]
						except:
							sw2 = 0
						await cur.execute("SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (res.author.id,))
						shield2 = await cur.fetchone()
						try:
							sh2 = shield2[6]
						except:
							sh2 = 0
						user1 = sw1 + sh1 + random.randint(1, 7)
						user2 = sw2 + sh2 + random.randint(1, 7)
						if user1>user2:
							winner = "user1"
						elif user2>user1:
							winner = "user2"
						else:
							winner = random.choice(["user1", "user2"])
						await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
						money1 = await cur.fetchone()
						await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (res.author.id,))
						money2 = await cur.fetchone()
						if money1[0]<money or money2[0]<money:
							return await ctx.send("One of you can't pay the price for the battle because he spent money in the time of fighting. Please try again later!")
						if winner == "user1":
							await cur.execute('UPDATE profile SET pvpwins=pvpwins+1 WHERE "user"=%s;', (ctx.author.id,))
							await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (money, ctx.author.id))
							await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (money, res.author.id))
							await ctx.send(f"{ctx.author.mention} won the battle vs {res.author.mention}! Congratulations!")
						else:
							await cur.execute('UPDATE profile SET pvpwins=pvpwins+1 WHERE "user"=%s;', (res.author.id,))
							await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (money, ctx.author.id))
							await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (money, res.author.id))
							await ctx.send(f"{res.author.mention} won the battle vs {ctx.author.mention}! Congratulations!")
			except:
				return await ctx.send(f"Noone wanted to join your battle, {ctx.author.mention}. Try again later!")

	@commands.cooldown(1,90,BucketType.user)
	@commands.command(description="Active Battles.", hidden=True)
	async def activebattle(self, ctx, money:int, enemy:discord.Member=None):
		if money<0:
			return await ctx.send("Don't scam!")
		if enemy:
			if enemy.id == ctx.author.id:
				return await ctx.send("You can't battle yourself.")
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
				ret = await cur.fetchone()
				if not ret:
					return await ctx.send(f"You don't have a character yet. Use `{ctx.prefix}create` to start!")
				if ret[0]<money:
					return await ctx.send("You're too poor.")
				if not enemy:
					await ctx.send(f"{ctx.author.mention} seeks an active battle! Write `active join @{str(ctx.author)}` now to duel him! The price is **${money}**.")
				else:
					await ctx.send(f"{ctx.author.mention} seeks an active battle with {enemy.mention}! Write `active private join @{str(ctx.author)}` now to duel him! The price is **${money}**.")
				def allcheck(amsg):
					return (amsg.content.strip()==f"active join <@{ctx.author.id}>" or amsg.content.strip()==f"active join <@!{ctx.author.id}>") and amsg.author.id != ctx.author.id
				def privatecheck(amsg):
					return (amsg.content.strip()==f"active private join <@{ctx.author.id}>" or amsg.content.strip()==f"active private join <@!{ctx.author.id}>") and amsg.author.id==enemy.id
				try:
					if not enemy:
						res = await self.bot.wait_for('message', timeout=60, check=allcheck)
					else:
						res = await self.bot.wait_for('message', timeout=60, check=privatecheck)
				except:
					return await ctx.send(f"Noone wanted to join your battle, {ctx.author.mention}. Try again later!")

				#checks for character
				await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (res.author.id,))
				ret = await cur.fetchone()
				if not ret:
					return await ctx.send(f"You don't have a character yet. Use `{ctx.prefix}create` to start!")
				if ret[0]<money:
					return await ctx.send("You're too poor.")


				PLAYERS = [ctx.author, res.author]
				HP = []
				for p in PLAYERS:
					await cur.execute('SELECT class FROM profile WHERE "user"=%s;', (p.id,))
					c = await cur.fetchone()
					if c[0] in ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"]:
						HP.append(120)
					else:
						HP.append(100)
				DAMAGE = []
				ARMOR = []

				#get damage
				for p in PLAYERS:
					await cur.execute("SELECT ai.damage FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Sword';", (p.id,))
					DAMAGE.append((await cur.fetchone())[0] or 0.00)
					await cur.execute("SELECT ai.armor FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=%s AND type='Shield';", (p.id,))
					ARMOR.append((await cur.fetchone())[0] or 0.00)
		for i in range(2):
			ARMOR[i] = int(ARMOR[i])
			DAMAGE[i] = int(DAMAGE[i])
		def is_valid_move(msg):
			return msg.content.lower() in ["attack", "defend", "recover"] and msg.author in PLAYERS
		while HP[0] > 0 and HP[1] > 0:
			await ctx.send(f"{PLAYERS[0].mention}: **{HP[0]}** HP\n{PLAYERS[1].mention}: **{HP[1]}** HP\nUse `attack`, `defend` or `recover`.")
			MOVES_DONE = {}
			while len(MOVES_DONE) < 2:
				try:
					res = await self.bot.wait_for('message', timeout=30, check=is_valid_move)
				except:
					return await ctx.send("Someone refused to move. Battle stopped.")
				if not res.author in MOVES_DONE.keys():
					MOVES_DONE[res.author] = res.content.lower()
				else:
					await ctx.send(f"{res.author.mention}, you already moved!")
			plz = list(MOVES_DONE.keys())
			for u in plz:
				o = plz[:]
				o = o[1-plz.index(u)]
				idx = PLAYERS.index(u)
				if MOVES_DONE[u] == "recover":
					HP[idx] += 20
					await ctx.send(f"{u.mention} healed himself for **20 HP**.")
				elif MOVES_DONE[u] == "attack" and MOVES_DONE[o] != "defend":
					eff = random.choice([int(DAMAGE[idx]), int(DAMAGE[idx]*0.5), int(DAMAGE[idx]*0.2), int(DAMAGE[idx]*0.8)])
					HP[1-idx] -= eff
					await ctx.send(f"{u.mention} hit {o.mention} for **{eff}** damage.")
				elif MOVES_DONE[u] == "attack" and MOVES_DONE[o] == "defend":
					eff = random.choice([int(DAMAGE[idx]), int(DAMAGE[idx]*0.5), int(DAMAGE[idx]*0.2), int(DAMAGE[idx]*0.8)])
					eff2 = random.choice([int(ARMOR[idx]), int(ARMOR[idx]*0.5), int(ARMOR[idx]*0.2), int(ARMOR[idx]*0.8)])
					if eff-eff2 > 0:
						HP[1-idx] -= eff-eff2
						await ctx.send(f"{u.mention} hit {o.mention} for **{eff-eff2}** damage.")
					else:
						await ctx.send(f"{u.mention}'s attack on {o.mention} failed!")
		if HP[0] <= 0 and HP[1] <= 0:
			return await ctx.send("You both died!")
		idx = HP.index([h for h in HP if h<=0][0])
		winner = PLAYERS[1-idx]
		looser = PLAYERS[idx]
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (winner.id,))
				money1 = await cur.fetchone()
				await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (looser.id,))
				money2 = await cur.fetchone()
				if money1[0]<money or money2[0]<money:
					return await ctx.send("One of you can't pay the price for the battle because he spent money in the time of fighting. Please try again later!")
				await cur.execute('UPDATE profile SET pvpwins=pvpwins+1 WHERE "user"=%s;', (winner.id,))
				await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (money, winner.id))
				await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (money, looser.id))
				await ctx.send(f"{winner.mention} won the active battle vs {looser.mention}! Congratulations!")



def setup(bot):
	bot.add_cog(Battles(bot))
