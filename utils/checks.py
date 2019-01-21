import discord
from discord.ext import commands

def has_char():
	async def predicate(ctx):
		async with ctx.bot.pool.acquire() as conn:
			return await conn.fetchrow('SELECT * FROM profile WHERE "user"=$1;', ctx.author.id)
	return commands.check(predicate)

def has_adventure():
	async def predicate(ctx):
		async with ctx.bot.pool.acquire() as conn:
			return await conn.fetchrow('SELECT * FROM mission WHERE "name"=$1;', ctx.author.id)
	return commands.check(predicate)

def has_no_adventure():
	async def predicate(ctx):
		async with ctx.bot.pool.acquire() as conn:
			return not await conn.fetchrow('SELECT * FROM mission WHERE "name"=$1;', ctx.author.id)
	return commands.check(predicate)

async def user_has_char(bot, userid):
	async with bot.pool.acquire() as conn:
		return await conn.fetchrow('SELECT * FROM profile WHERE "user"=$1;', userid)

async def has_money(bot, userid, money):
	async with bot.pool.acquire() as conn:
		return await conn.fetchval('SELECT money FROM profile WHERE "user"=$1 AND "money">=$2;', userid, money)
