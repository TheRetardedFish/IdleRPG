import asyncio
import discord

class GlobalEvents:
    def __init__(self, bot):
        self.bot = bot
        self.auth_headers = {"Authorization" : bot.config.dbltoken} # needed for DBL requests
        self.bot_owner = None
        self.status_updates = bot.loop.create_task(self.status_updater()) # Initiate the status updates and save it for the further close

    async def on_ready(self):
        if not self.bot.config.is_beta:
            await self.bot.session.post(f"https://discordbots.org/api/bots/{self.bot.user.id}/stats", data=self.get_dbl_payload(), headers=self.auth_headers)

    async def on_guild_remove(self, guild):
        if self.bot.config.is_beta:
            return
        announce_channel = self.bot.get_channel(self.bot.config.join_channel)
        await announce_channel.send(f"Bye bye **{guild.name}**!")
        await self.bot.session.post(f"https://discordbots.org/api/bots/{self.bot.user.id}/stats", data=self.get_dbl_payload(), headers=self.auth_headers)

    async def on_guild_join(self, guild):
        if not self.bot_owner: # just for performance reasons (+1 API call)
            self.bot_owner = (await self.bot.application_info()).owner

        embed = discord.Embed(title="Thanks for adding me!", colour=0xeec340, description=f"Hi! I am **IdleRPG**, a Discord Bot by `{self.bot_owner}`.\nI simulate" \
        f" a whole Roleplay with everything it needs!\n\nVisit **{self.bot.BASE_URL}** for a documentation on all my commands. :innocent:\nTo get started, type " \
        f"`{self.bot.config.global_prefix}create`.\n\nA tutorial can be found on **{self.bot.BASE_URL}/tutorial-faq**.\n\nDon't like my prefix? `{self.bot.config.global_prefix}" \
        "settings prefix` changes it.\n\nHave fun! :wink:")

        embed.set_image(url=f"{self.bot.BASE_URL}/IdleRPG.png")
        embed.set_footer(text=f"IdleRPG Version {self.bot.version}", icon_url=self.bot.user.avatar_url)
        allchannels = guild.text_channels
        for channel in allchannels:
            if channel.permissions_for(guild.me).send_messages and channel.permissions_for(guild.me).read_messages:
                await channel.send(embed=embed)
                break
        if self.bot.config.is_beta:
            return
        announce_channel = self.bot.get_channel(self.bot.config.join_channel)
        await announce_channel.send(f"Joined a new server! **{guild.name}** with **{len(guild.members)}** members!")
        await self.bot.session.post(f"https://discordbots.org/api/bots/{self.bot.user.id}/stats", data=self.get_dbl_payload(), headers=self.auth_headers)

    async def status_updater(self):
        while not self.bot.is_ready():
            await asyncio.sleep(3) # loop until the bot is ready to avoid empty data in statuses

        while not (self.bot.is_closed() and self.status_updates.cancelled()):
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(self.bot.guilds)} servers"), status=discord.Status.idle)
            await asyncio.sleep(15)
            await self.bot.change_presence(activity=discord.Game(name=f"with {len(self.bot.users)} users"), status=discord.Status.idle)
            await asyncio.sleep(15)
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"{self.bot.config.global_prefix}help" \
            f" and {self.bot.config.global_prefix}create"), status=discord.Status.idle)
            await asyncio.sleep(15)
            await self.bot.change_presence(activity=discord.Game(name=f"{self.bot.BASE_URL}"), status=discord.Status.idle)
            await asyncio.sleep(15)

    def get_dbl_payload(self):
        return {"server_count": len(self.bot.guilds), "shard_count": len(self.bot.shards)}

    def __unload(self):
        self.status_updates.cancel() # Cancel the status updates on unload
    
def setup(bot):
    bot.add_cog(GlobalEvents(bot))
