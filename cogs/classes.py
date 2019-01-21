import discord
from discord.ext import commands
import cogs.rpgtools as rpgtools
import traceback, random
from discord.ext.commands import BucketType


async def genstats(bot, userid, damage, armor):
	async with bot.pool.acquire() as conn:
		async with conn.cursor() as cur:
			await cur.execute('SELECT class FROM profile WHERE "user"=%s;', (userid,))
			uclass = (await cur.fetchone())[0]
			evolves1 = ['Mage', 'Wizard', 'Pyromancer', 'Elementalist', 'Dark Caster']
			evolves2 = ['Thief', 'Rogue', 'Chunin', 'Renegade', 'Assassin']
			evolves3 = ['Warrior', 'Swordsman', 'Knight', 'Warlord', 'Berserker']
			evolves4 = ['Novice', 'Proficient', 'Artisan', 'Master', 'Paragon']
			if uclass in evolves1:
				return (damage + evolves1.index(uclass) + 1, armor)
			elif uclass in evolves3:
				return (damage, armor + evolves3.index(uclass) + 1)
			elif uclass in evolves4:
				return (damage + evolves4.index(uclass) + 1, armor + evolves4.index(uclass) + 1)
			else:
				return (damage, armor)

async def thiefgrade(bot, userid):
	async with bot.pool.acquire() as conn:
		async with conn.cursor() as cur:
			await cur.execute('SELECT class FROM profile WHERE "user"=%s;', (userid,))
			uclass = (await cur.fetchone())[0]
			return ['Thief', 'Rogue', 'Chunin', 'Renegade', 'Assassin'].index(uclass) + 1

async def petlevel(bot, userid):
	async with bot.pool.acquire() as conn:
		async with conn.cursor() as cur:
			await cur.execute('SELECT class FROM profile WHERE "user"=%s;', (userid,))
			uclass = (await cur.fetchone())[0]
			return ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"].index(uclass) + 1


def is_thief():
	async def predicate(ctx):
		async with ctx.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT class FROM profile WHERE "user"=%s;', (ctx.author.id,))
				ret = await cur.fetchone()
				if not ret:
					return False
				else:
					return ret[0] in ['Thief', 'Rogue', 'Chunin', 'Renegade', 'Assassin']
	return commands.check(predicate)


def is_ranger():
	async def predicate(ctx):
		async with ctx.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT class FROM profile WHERE "user"=%s;', (ctx.author.id,))
				ret = await cur.fetchone()
				if not ret:
					return False
				return ret[0] in ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"]
	return commands.check(predicate)


def is_patron(bot, user):
	member = bot.get_guild(430017996304678923).get_member(user.id)  # cross server stuff
	if not member:
		return False
	return discord.utils.get(member.roles, name='Donator') is not None or discord.utils.get(member.roles, name='Administrators') is not None


class Classes:

	def __init__(self, bot):
		self.bot = bot

	async def has_char(self, userid):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT user FROM profile WHERE "user"=%s;', (userid,))
				return await cur.fetchone()

	async def genstats(self, userid, damage, armor):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT class FROM profile WHERE "user"=%s;', (userid,))
				uclass = (await cur.fetchone())[0]
				evolves1 = ['Wizard', 'Pyromancer', 'Elementalist', 'Dark Caster']
				evolves2 = ['Rogue', 'Chunin', 'Renegade', 'Assassin']
				evolves3 = ['Swordsman', 'Knight', 'Warlord', 'Berserker']
				evolves4 = ['Novice', 'Proficient', 'Artisan', 'Master', 'Paragon']
				if uclass in evolves1:
					return (damage + evolves1.index(uclass) + 2, armor)
				elif uclass in evolves3:
					return (damage, armor + evolves2.index(uclass) + 2)
				elif uclass in evolves4:
					return (damage + evolves4.index(uclass) + 1, armor + evolves4.index(uclass) + 1)
				elif uclass in evolves2:
					return (damage, armor)


	async def get_level(self, userid):
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT xp FROM profile WHERE "user"=%s;', (userid,))
				ret = await cur.fetchone()
				if not ret:
					return ret
				else:
					return rpgtools.xptolevel(ret[0])

	@commands.cooldown(1,86400,BucketType.user)
	@commands.command(name="class", description="Change your class.")
	async def _class(self, ctx, profession:str):
		profession = profession.title()
		if profession not in ["Warrior", "Thief", "Mage", "Paragon", "Ranger"]:
			ctx.command.reset_cooldown(ctx)
			return await ctx.send("Please align as a `Warrior`, `Mage`, `Thief`, `Ranger` or `Paragon` (Patreon Only).")
		if profession == "Paragon" and not is_patron(self.bot, ctx.author):
			return await ctx.send("You have to be a donator to choose this class.")
		if profession == "Paragon":
			profession = "Novice"
		if profession == "Ranger":
			profession = "Caretaker"
		if await self.has_char(ctx.author.id):
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					await cur.execute('SELECT class FROM profile WHERE "user"=%s;', (ctx.author.id,))
					curclass = await cur.fetchone()
					if curclass[0] == "No Class":
						await cur.execute('UPDATE profile SET "class"=%s WHERE "user"=%s;', (profession, ctx.author.id))
						await ctx.send(f"Your new class is now `{profession}`.")
					else:
						await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (ctx.author.id,))
						money = await cur.fetchone()
						if money[0] >= 5000:
							def check(m):
								return m.content.lower() == "confirm" and m.author == ctx.author
							await ctx.send("Are you sure? Type `confirm` to change your class for **$5000**")
							try:
								await self.bot.wait_for('message', check=check, timeout=30)
							except:
								return await ctx.send("Class change cancelled.")
							await cur.execute('UPDATE profile SET "class"=%s WHERE "user"=%s;', (profession, ctx.author.id))
							await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (5000, ctx.author.id))
							await ctx.send(f"Your new class is now `{profession}`. **$5000** was taken off your balance.")
						else:
							await ctx.send(f"You're too poor for a class change, it costs **$5000**, you got **${money[0]}**.")
		else:
			await ctx.send(f"Seems you haven't got a character yet. Use `{ctx.prefix}create` to get started!")

	@commands.command(description="Views your current class and benefits.")
	async def myclass(self, ctx):
		if self.has_char(ctx.author.id):
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					await cur.execute('SELECT class FROM profile WHERE "user"=%s;', (ctx.author.id,))
					userclass = await cur.fetchone()
					if userclass[0] == "No Class":
						await ctx.send("You haven't got a class yet.")
					else:
						try:
							await ctx.send(file=discord.File(f"classes/{userclass[0].lower().replace(' ', '_')}.png"))
						except:
							await ctx.send(f"The image for your class **{userclass[0]}** hasn't been added yet.")
		else:
			await ctx.send(f"Seems you haven't got a character yet. Use `{ctx.prefix}create` to get started!")


	@commands.command(description="Evolve to the next level of your class.")
	async def evolve(self, ctx):
		level = int(await self.get_level(ctx.author.id))
		if not level:
			return await ctx.send(f"Seems you haven't got a character yet. Use `{ctx.prefix}create` to get started!")
		evolves = {"Mage": ['Wizard', 'Pyromancer', 'Elementalist', 'Dark Caster'], "Thief": ['Rogue', 'Chunin', 'Renegade', 'Assassin'], "Warrior": ['Swordsman', 'Knight', 'Warlord', 'Berserker'], "Paragon": ['Proficient', 'Artisan', 'Master', 'Paragon'], "Ranger": ["Trainer", "Bowman", "Hunter","Ranger"]}
		if level<5:
			return await ctx.send("You level isn't high enough to evolve.")
		if level>=5:
			newindex = 0
		if level>=10:
			newindex = 1
		if level>=15:
			newindex = 2
		if level>=20:
			newindex = 3
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute('SELECT class FROM profile WHERE "user"=%s;', (ctx.author.id,))
				curclass = (await cur.fetchone())[0]
				if curclass in ['Mage', 'Wizard', 'Pyromancer', 'Elementalist', 'Dark Caster']:
					newclass = evolves['Mage'][newindex]
				elif curclass in ['Thief', 'Rogue', 'Chunin', 'Renegade', 'Assassin']:
					newclass = evolves['Thief'][newindex]
				elif curclass in ['Warrior', 'Swordsman', 'Knight', 'Warlord', 'Berserker']:
					newclass = evolves['Warrior'][newindex]
				elif curclass in ['Novice', 'Proficient', 'Artisan', 'Master', 'Paragon']:
					newclass = evolves['Paragon'][newindex]
				elif curclass in ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"]:
					newclass = evolves['Ranger'][newindex]
				else:
					return await ctx.send("You don't have a class yet.")
				await cur.execute('UPDATE profile SET "class"=%s WHERE "user"=%s;', (newclass, ctx.author.id))
				await ctx.send(f"You are now a `{newclass}`.")

	@commands.command(description="Evolving tree.")
	async def tree(self, ctx):
		await ctx.send("""```
Level 0   |  Level 5    |  Level 10     | Level 15        |  Level 20
----------------------------------------------------------------------
Warriors ->  Swordsmen ->  Knights     -> Warlords       ->  Berserker
Thieves  ->  Rogues    ->  Chunin      -> Renegades      ->  Assassins
Mage     ->  Wizards   ->  Pyromancers -> Elementalists  ->  Dark Caster
Novice   ->  Proficient->  Artisan     -> Master         ->  Paragon
Caretaker->  Trainer   ->  Bowman      -> Hunter         ->  Ranger
```""")

	@is_thief()
	@commands.guild_only()
	@commands.cooldown(1,3600,BucketType.user)
	@commands.command(description="[Thief Only] Steal money!")
	async def steal(self, ctx):
		grade = await thiefgrade(self.bot, ctx.author.id)
		if random.randint(1,100) in range(1,grade*10+1):
			ppl = ctx.guild.members
			ppl.remove(ctx.author)
			target = random.choice(ppl)
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					await cur.execute('SELECT money FROM profile WHERE "user"=%s;', (target.id,))
					user = await cur.fetchone()
					if not user:
						return await ctx.send(f"You tried to steal **{target}**, but that person doesn't have a character.")
					stolen = int(user[0]*0.1)
					await cur.execute('UPDATE profile SET money=money+%s WHERE "user"=%s;', (stolen, ctx.author.id))
					await cur.execute('UPDATE profile SET money=money-%s WHERE "user"=%s;', (stolen, target.id))
					await ctx.send(f"You stole **${stolen}** from **{target}**.")
		else:
			await ctx.send("Your attempt to steal money wasn't successful.")

	@is_ranger()
	@commands.command(description="[Ranger Only] View your pet!")
	async def pet(self, ctx):
		petlvl = await petlevel(self.bot, ctx.author.id)
		em = discord.Embed(title=f"{ctx.author.display_name}'s pet")
		em.add_field(name="Level", value=petlvl, inline=False)
		em.set_thumbnail(url=ctx.author.avatar_url)
		url = ["https://cdn.discordapp.com/attachments/456433263330852874/458568221189210122/fox.JPG", "https://cdn.discordapp.com/attachments/456433263330852874/458568217770721280/bird_2.jpg", "https://cdn.discordapp.com/attachments/456433263330852874/458568230110363649/hedgehog_2.JPG", "https://cdn.discordapp.com/attachments/456433263330852874/458568231918108673/wolf_2.jpg", "https://cdn.discordapp.com/attachments/456433263330852874/458577751226581024/dragon_2.jpg"][petlvl-1]
		em.set_image(url=url)
		await ctx.send(embed=em)

	@is_ranger()
	@commands.cooldown(1,86400,BucketType.user)
	@commands.command(description="[Ranger Only] Let your pet get a weapon for you!")
	async def hunt(self, ctx):
		petlvl = await petlevel(self.bot, ctx.author.id)
		async with self.bot.pool.acquire() as conn:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					maximumstat = random.randint(1, petlvl * 6)
					shieldorsword = random.choice(["Sword", "Shield"])
					names = ["Broken", "Old", "Tattered", "Forgotten"]
					itemvalue = random.randint(1,250)
					if shieldorsword == "Sword":
						itemname = random.choice(names)+random.choice([" Sword", " Blade", " Stich"])
						await cur.execute('INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES (%s, %s, %s, %s, %s, %s) RETURNING *;', (ctx.author.id, itemname, itemvalue, "Sword", maximumstat, 0.00))
					elif shieldorsword == "Shield":
						itemname = random.choice(names)+random.choice([" Shield", " Defender", " Aegis"])
						await cur.execute('INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES (%s, %s, %s, %s, %s, %s) RETURNING *;', (ctx.author.id, itemname, itemvalue, "Shield", 0.00, maximumstat))
					item = await cur.fetchone()
					await cur.execute('INSERT INTO inventory ("item", "equipped") VALUES (%s, %s);', (item[0], False))
					embed=discord.Embed(title="You gained an item!", description="Your pet found an item!", color=0xff0000)
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
					embed.set_footer(text=f"Your pet needs to recover, wait a day to retry")
					await ctx.send(embed=embed)


def setup(bot):
	bot.add_cog(Classes(bot))
