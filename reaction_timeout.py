from discord.ext import tasks, commands


class ReactionTimeout(commands.Cog):
    def __init__(self, bot, member_id, callback):
        self.bot = bot
        self.data = []
        self.count = 1
        self.member_id = member_id
        self.callback = callback
        self.firstRun = True
        self.reaction_timeout.start()

    def cog_unload(self):
        self.reaction_timeout.cancel()

    def increment(self):
        self.count += 1
        self.firstRun = True
        self.reaction_timeout.restart()

    def stop_watching(self):
        self.reaction_timeout.cancel()

    @tasks.loop(seconds=10.0)
    async def reaction_timeout(self):
        if self.firstRun:
            self.firstRun = False
        else:
            self.count = 0
            self.reaction_timeout.cancel()
            self.callback(self.member_id)
