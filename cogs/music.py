"""
Please understand Music bots are complex, and that even this basic example can be daunting to a beginner.
For this reason it's highly advised you familiarize yourself with discord.py, python and asyncio, BEFORE
you attempt to write a music bot.
This example makes use of: Python 3.6
For a more basic voice example please read:
    https://github.com/Rapptz/discord.py/blob/rewrite/examples/basic_voice.py
This is a very basic playlist example, which allows per guild playback of unique queues.
The commands implement very basic logic for basic usage. But allow for expansion. It would be advisable to implement
your own permissions and usage logic for commands.
e.g You might like to implement a vote before skipping the song or only allow admins to stop the player.
Music bots require lots of work, and tuning. Goodluck.
If you find any bugs feel free to ping me on discord. @Eviee#0666
"""
import discord
from discord.ext import commands
from discord.ext.commands import BucketType

import subprocess
import asyncio
import itertools
import sys
import traceback
import json
import datetime
import audioop
import math
from async_timeout import timeout
from functools import partial
from youtube_dl import YoutubeDL


ytdlopts = {
	'format': 'bestaudio/best',
	'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
	'restrictfilenames': True,
	'noplaylist': True,
	'nocheckcertificate': True,
	'ignoreerrors': False,
	'logtostderr': False,
	'quiet': True,
	'no_warnings': True,
	'default_search': 'auto',
	'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
	'before_options': '-nostdin',
	'options': '-vn'
}

ytdl = YoutubeDL(ytdlopts)

def get_duration(url):
	cmd = f'ffprobe -v error -show_format -of json {url}'
	process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = process.communicate()
	data = json.loads(output)
	match = data['format']['duration']
	process.kill()
	return match


class VoiceConnectionError(commands.CommandError):
	"""Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
	"""Exception for cases of invalid Voice Channels."""


class YTDLSource(discord.PCMVolumeTransformer):

	def __init__(self, source, *, data, requester):
		super().__init__(source)
		self.requester = requester

		self.title = data.get('title')
		self.web_url = data.get('webpage_url')
		try:
			self.duration = data.get('duration', get_duration(data['url']))
		except:
			self.duration = None
		self.thumbnail = data.get('thumbnail')
		self.frames = 0
		try:
			self.views = data.get('view_count')
			self.pro = data.get('like_count')
			self.con = data.get('dislike_count')
		except:
			self.views = None
			self.pro = None
			self.con = None
		# YTDL info dicts (data) have other useful information you might want
		# https://github.com/rg3/youtube-dl/blob/master/README.md

	def __getitem__(self, item: str):
		"""Allows us to access attributes similar to a dict.
		This is only useful when you are NOT downloading.
		"""
		return self.__getattribute__(item)

	@classmethod
	async def create_source(cls, ctx, search: str, *, loop, download=False):
		loop = loop or asyncio.get_event_loop()

		to_run = partial(ytdl.extract_info, url=search, download=download)
		data = await loop.run_in_executor(None, to_run)

		if 'entries' in data:
			# take first item from a playlist
			data = data['entries'][0]

		await ctx.send(embed=discord.Embed(description=f'Added `{data["title"]}` to the Queue', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/controls.png",text="Music Controller"), delete_after=15)

		if download:
			source = ytdl.prepare_filename(data)
		else:
			return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

		return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

	@classmethod
	async def regather_stream(cls, data, *, loop):
		"""Used for preparing a stream, instead of downloading.
		Since Youtube Streaming links expire."""
		loop = loop or asyncio.get_event_loop()
		requester = data['requester']

		to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
		data = await loop.run_in_executor(None, to_run)

		return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)

	def read(self, volume=None):
		self.frames += 1
		return audioop.mul(super().read(), 2, volume or self.volume)

	@property
	def length(self):
		return self.duration

	@property
	def progress(self):
		return math.floor(self.frames/50)

	@property
	def remaining(self):
		return self.length - self.progress

class MusicPlayer:
	"""A class which is assigned to each guild using the bot for Music.
	This class implements a queue and loop, which allows for different guilds to listen to different playlists
	simultaneously.
	When the bot disconnects from the Voice it's instance will be destroyed.
	"""

	__slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

	def __init__(self, ctx):
		self.bot = ctx.bot
		self._guild = ctx.guild
		self._channel = ctx.channel
		self._cog = ctx.cog

		self.queue = asyncio.Queue()
		self.next = asyncio.Event()

		self.np = None  # Now playing message
		self.volume = .5
		self.current = None

		ctx.bot.loop.create_task(self.player_loop())

	async def player_loop(self):
		"""Our main player loop."""
		await self.bot.wait_until_ready()

		condition = asyncio.Condition()
		fut = condition.wait_for(lambda: len(self._guild.voice_client.channel.members) != 1)
		while not self.bot.is_closed():
			self.next.clear()
			try:
				# Wait for the next song. If we timeout cancel the player and disconnect...
				async with timeout(300):  # 5 minutes...
					source = await self.queue.get()
			except asyncio.TimeoutError:
				return self.destroy(self._guild)
			#try:
			#	await asyncio.wait_for(fut, timeout=3600)
			#except asyncio.TimeoutError:
			#	await self._channel.send(embed=discord.Embed(description='All members left the voice channel', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"))
			#	return self.destroy(self._guild)

			if not isinstance(source, YTDLSource):
				# Source was probably a stream (not downloaded)
				# So we should regather to prevent stream expiration
				try:
					source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
				except Exception as e:
					await self._channel.send(f'There was an error processing your song.\n'
											f'```css\n[{e}]\n```')
					continue

			source.volume = self.volume
			self.current = source

			self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
			self.np = await self._channel.send(embed=discord.Embed(description=f'Now playing - `{source.title}` requested by `{source.requester}`', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"))
			await self.next.wait()

			# Make sure the FFmpeg process is cleaned up.
			source.cleanup()
			self.current = None

			try:
				# We are no longer playing this song...
				await self.np.delete()
			except discord.HTTPException:
				pass

	def destroy(self, guild):
		"""Disconnect and cleanup the player."""
		return self.bot.loop.create_task(self._cog.cleanup(guild))


class Music:
	"""Music related commands."""

	__slots__ = ('bot', 'players')

	def __init__(self, bot):
		self.bot = bot
		self.players = {}

	async def cleanup(self, guild):
		try:
			await guild.voice_client.disconnect()
		except AttributeError:
			pass

		try:
			del self.players[guild.id]
		except KeyError:
			pass

	async def __local_check(self, ctx):
		"""A local check which applies to all commands in this cog."""
		if not ctx.guild:
			raise commands.NoPrivateMessage
		return True

	async def __error(self, ctx, error):
		"""A local error handler for all errors arising from commands in this cog."""
		if isinstance(error, commands.NoPrivateMessage):
			try:
				return await ctx.send('This command can not be used in Private Messages.')
			except discord.HTTPException:
				pass
		elif isinstance(error, InvalidVoiceChannel):
			await ctx.send(embed=discord.Embed(description=f'Error connecting to Voice Channel. Please make sure you are in a valid channel or provide me with one', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"))

		print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
		traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

	def get_player(self, ctx):
		"""Retrieve the guild player, or generate one."""
		try:
			player = self.players[ctx.guild.id]
		except KeyError:
			player = MusicPlayer(ctx)
			self.players[ctx.guild.id] = player

		return player

	@commands.command(name='connect', aliases=['join'], description="Summon the bot to your voice channel.")
	async def connect_(self, ctx):
		"""Connect to voice.
		Parameters
		------------
		channel: discord.VoiceChannel [Optional]
		    The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
		    will be made.
		This command also handles moving the bot to different channels.
		"""
		try:
			channel = ctx.author.voice.channel
		except AttributeError:
			raise InvalidVoiceChannel('No channel to join. Please make sure you are in a voice channel.')

		vc = ctx.voice_client

		if vc:
			if vc.channel.id == channel.id:
				return
			try:
				await vc.move_to(channel)
			except asyncio.TimeoutError:
				raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
		else:
			try:
				await channel.connect()
			except asyncio.TimeoutError:
				raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')

		await ctx.send(embed=discord.Embed(description=f'Connected to `{channel}`', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=20)

	@commands.cooldown(1,10,BucketType.user)
	@commands.command(name='play', aliases=['sing'], description="Plays a song from YouTube, SoundCloud, etc.")
	async def play_(self, ctx, *, search: str):
		"""Request a song and add it to the queue.
		This command attempts to join a valid voice channel if the bot is not already in one.
		Uses YTDL to automatically search and retrieve a song.
		Parameters
		------------
		search: str [Required]
		    The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
		"""
		await ctx.trigger_typing()

		vc = ctx.voice_client

		if not vc:
			await ctx.invoke(self.connect_)

		else:
			if ctx.author not in vc.channel.members:
				return await ctx.send(embed=discord.Embed(description=f'You must be in `{vc.channel}` to request songs', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=30)

		player = self.get_player(ctx)

        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
		try:
			source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False)
		except:
			return await ctx.send(embed=discord.Embed(description=f'There was a download error', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=30)

		await player.queue.put(source)

	@commands.command(name='pause', description="Pauses the currently playing song.")
	async def pause_(self, ctx):
		"""Pause the currently playing song."""
		vc = ctx.voice_client

		if not vc or not vc.is_playing():
			return await ctx.send(embed=discord.Embed(description='I am not currently playing anything', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/pause.png",text="Music Controller"), delete_after=20)
		elif vc.is_paused():
			return
		else:
			if ctx.author not in vc.channel.members:
				return await ctx.send(embed=discord.Embed(description=f'You must be in `{vc.channel}` to pause the song', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/pause.png",text="Music Controller"), delete_after=30)

		vc.pause()
		await ctx.send(embed=discord.Embed(description=f'`{ctx.author}` paused the song', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/pause.png",text="Music Controller"))

	@commands.command(name='resume', description="Resume the currently paused song.")
	async def resume_(self, ctx):
		"""Resume the currently paused song."""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send(embed=discord.Embed(description='I am not currently playing anything', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=20)
		elif not vc.is_paused():
			return
		else:
			if ctx.author not in vc.channel.members:
				return await ctx.send(embed=discord.Embed(description=f'You must be in `{vc.channel}` to pause the song', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=30)

		vc.resume()
		await ctx.send(embed=discord.Embed(description=f'`{ctx.author}` resumed the song', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"))

	@commands.command(name='skip', description="Skip the currently playing song.")
	async def skip_(self, ctx):
		"""Skip the song."""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send(embed=discord.Embed(description='I am not currently playing anything', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/step-forward.png",text="Music Controller"), delete_after=20)

		if vc.is_paused():
			pass
			if ctx.author not in vc.channel.members:
				return await ctx.send(embed=discord.Embed(description=f'You must be in `{vc.channel}` to skip the song', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/step-forward.png",text="Music Controller"), delete_after=30)
		elif not vc.is_playing():
			return
		else:
			if ctx.author not in vc.channel.members:
				return await ctx.send(embed=discord.Embed(description=f'You must be in `{vc.channel}` to skip the song', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/step-forward.png",text="Music Controller"), delete_after=30)


		#vote for skipping
		needed = int((len(vc.channel.members)-1)/2)+1
		msg = await ctx.send(f"{ctx.author.mention} wants to skip the current song! React :track_next: to skip! **{needed}** votes are required!")
		await msg.add_reaction("\U000023ef")
		votes = 0
		voted = []

		def check(reaction, user):
			return reaction.message.id == msg.id and str(reaction.emoji) == "\U000023ef" and user in vc.channel.members and not user.bot and not user in voted

		try:
			while votes < needed:
				reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=10)
				votes += 1
				voted.append(user)
				await ctx.send(f"{user.mention} voted for a skip! **{votes}/{needed}**")
		except asyncio.TimeoutError:
			return await ctx.send("Vote skip declined.")

		vc.stop()
		await ctx.send(embed=discord.Embed(description='Vote skip passed!', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/step-forward.png",text="Music Controller"))

	@commands.command(name='queue', aliases=['q', 'playlist'], description="View the upcoming songs.")
	async def queue_info(self, ctx):
		"""Retrieve a basic queue of upcoming songs."""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send(embed=discord.Embed(description='I am not currently connected to voice!', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=20)

		player = self.get_player(ctx)
		if player.queue.empty():
			return await ctx.send(embed=discord.Embed(description='There are currently no more queued songs', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"))

		# Grab up to 5 entries from the queue...
		upcoming = list(itertools.islice(player.queue._queue, 0, 5))

		fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
		embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt, colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller")

		await ctx.send(embed=embed)

	@commands.command(name='now_playing', aliases=['np', 'current', 'currentsong', 'playing'], description="Shows the music controller with information about the current song.")
	async def now_playing_(self, ctx):
		"""Display information about the currently playing song."""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send(embed=discord.Embed(description='I am not currently connected to voice!', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=20)

		player = self.get_player(ctx)
		if not player.current:
			return await ctx.send(embed=discord.Embed(description='I am not currently playing anything!', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"))

		try:
			# Remove our previous now_playing message.
			await player.np.delete()
		except:
			pass

		embed = discord.Embed(title='Music Controller', description='Currently Playing Song', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller")
		embed.add_field(name="Now Playing", value=f"```{vc.source.title}```", inline=False)
		embed.add_field(name="Requested By", value=f"{vc.source.requester.mention}", inline=False)
		embed.add_field(name="Video URL", value=f"[Click Me!]({vc.source.web_url})", inline=False)
		if vc.source.duration:
			embed.add_field(name="Duration", value=f"{str(datetime.timedelta(seconds=vc.source.length))}")
			embed.add_field(name="Progress", value=f"{str(datetime.timedelta(seconds=vc.source.progress))}")
			embed.add_field(name="Remaining", value=f"{str(datetime.timedelta(seconds=vc.source.remaining))}")
		embed.add_field(name="Volume", value=f"{vc.source.volume*100}%", inline=False)

		if vc.source.views:
			embed.add_field(name="Views", value='{0:,}'.format(vc.source.views), inline=False)
		if vc.source.pro:
			embed.add_field(name="Likes", value='{0:,}'.format(vc.source.pro))
		if vc.source.con:
			embed.add_field(name="Dislikes", value='{0:,}'.format(vc.source.con))

		if player.queue.empty():
			embed.add_field(name="Upcoming", value="No more upcoming songs", inline=False)
		else:
			upcoming = list(itertools.islice(player.queue._queue, 0, 3))
			upcomingtext = '\n'.join([track['title'] for track in upcoming])
			embed.add_field(name=f"Upcoming next {len(upcoming)}", value=upcomingtext, inline=False)

		embed.set_thumbnail(url=vc.source.thumbnail)

		player.np = await ctx.send(embed=embed)

	@commands.command(name='volume', aliases=['vol'], description="Change the music volume.")
	async def change_volume(self, ctx, *, vol: float):
		"""Change the player volume.
		Parameters
		------------
		volume: float or int [Required]
		The volume to set the player to in percentage. This must be between 1 and 100.
		"""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send(embed=discord.Embed(description='I am not currently connected to voice!', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=20)
		else:
			if ctx.author not in vc.channel.members:
				return await ctx.send(embed=discord.Embed(description=f'You must be in `{vc.channel}` to change the value', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=30)

		if not 0 < vol < 101:
			return await ctx.send(embed=discord.Embed(description='Please enter a value between 1 and 100', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"))

		player = self.get_player(ctx)

		if vc.source:
			vc.source.volume = vol / 100

		player.volume = vol / 100
		await ctx.send(embed=discord.Embed(description=f'`{ctx.author}` set the volume to **{vol}**%', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"))

	@commands.command(name='stop', description="Stops the song and the whole music session.")
	async def stop_(self, ctx):
		"""Stop the currently playing song and destroy the player.
		!Warning!
			This will destroy the player assigned to your guild, also deleting any queued songs and settings.
		"""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send(embed=discord.Embed(description='I am not currently playing anything!', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=20)
		elif ctx.author not in vc.channel.members:
			return await ctx.send(embed=discord.Embed(description=f'You must be in `{vc.channel}` to stop the music', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"), delete_after=30)

		#vote for skipping
		needed = int((len(vc.channel.members)-1)/2)+1
		msg = await ctx.send(f"{ctx.author.mention} wants to stop the session! React :stop_button: to stop! **{needed}** votes are required!")
		await msg.add_reaction("\U000023f9")
		votes = 0
		voted = []

		def check(reaction, user):
			return reaction.message.id == msg.id and str(reaction.emoji) == "\U000023f9" and user in vc.channel.members and not user.bot and not user in voted

		try:
			while votes < needed:
				reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=10)
				votes += 1
				voted.append(user)
				await ctx.send(f"{user.mention} voted for a stop! **{votes}/{needed}**")
		except asyncio.TimeoutError:
			return await ctx.send("Session continued, vote declined.")


		await ctx.send(embed=discord.Embed(description=f'`{ctx.author}` stopped the music session', colour=0x0c0b0b).set_footer(icon_url="http://gelbpunkt.troet.org/idlerpg/assets/play.png",text="Music Controller"))

		await self.cleanup(ctx.guild)

def setup(bot):
	bot.add_cog(Music(bot))
