from datetime import timedelta
import discord
from discord.ext import commands
import Levenshtein as lv

class Errorhandler:
    def __init__(self, bot):
        self.bot = bot
        bot.on_command_error = self._on_command_error

    async def _on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return
        error = getattr(error, 'original', error)
        if isinstance(error, commands.errors.CommandNotFound):
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT "unknown" FROM server WHERE "id"=%s;', (ctx.guild.id,))
                    ret = []
                    async for row in cur:
                        ret.append(row)
                    try:
                        if ret[0][0] == False:
                            return
                    except:
                        return
            nl = "\n"
            matches = []
            for command in list(self.bot.commands):
                if lv.distance(ctx.invoked_with, command.name) < 4:
                    matches.append(command.name)
            if len(matches) == 0:
                matches.append("Oops! I couldn't find any similar Commands!")
            try:
                await ctx.send(f"**`Unknown Command`**\n\nDid you mean:\n{nl.join(matches)}\n\nNot what you meant? Type `{ctx.prefix}help` for a list of commands.")
            except:
                pass
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Oops! You forgot a required argument: `{error.param.name}`")
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send(f"You used a wrong argument!")
        elif isinstance(error, commands.errors.CommandOnCooldown):
            return await ctx.send(f"You are on cooldown. Try again in {timedelta(seconds=int(error.retry_after))}.")
        elif isinstance(error, discord.errors.Forbidden):
            pass
        elif isinstance(error, commands.errors.NotOwner):
            await ctx.send(embed=discord.Embed(title="Permission denied", description=":x: This command is only avaiable for the bot owner.", colour=0xff0000))
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(embed=discord.Embed(title="Permission denied", description=":x: You don't have the permissions to use this command. It is thought for other users.", \
             colour=0xff0000))
        elif isinstance(error, discord.HTTPException):
            await ctx.send(f"There was a error responding to your message:\n`{error.text}`\nCommon issues: Bad Guild Icon or too long response")
        else:
            pass
        try:
            ctx.command.reset_cooldown(ctx)
        except:
            pass

def setup(bot):
	bot.add_cog(Errorhandler(bot))