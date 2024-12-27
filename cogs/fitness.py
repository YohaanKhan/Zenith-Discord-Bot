import discord
from discord.ext import commands
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

# Fitness Cog
class Fitness(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.setup_database())

    #sets up the database with the required access credentials 
    async def setup_database(self):
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_name = os.getenv('DB_NAME')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT')
        
        # Connect to Neon PostgreSQL database
        self.pool = await asyncpg.create_pool(
            user=db_user,
            password=db_password,
            database=db_name,
            host=db_host,
            port=db_port
        )

        # Create the leveling table if it doesn't exist
        async with self.pool.acquire() as conn:
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS leveling (
                user_id BIGINT PRIMARY KEY,
                powerlevel INTEGER NOT NULL,
                strength INTEGER NOT NULL,
                pushup INTEGER DEFAULT 0,
                pullup INTEGER DEFAULT 0,
                run INTEGER DEFAULT 0,
                situp INTEGER DEFAULT 0
            )
            ''')

    # a function that allows the program to add xp to the user's profile on completion of certain activities
    async def add_xp(self, user_id, xp_to_add):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT strength, powerlevel FROM leveling WHERE user_id = $1",
                user_id
            )

            if result is None:
                strength, powerlevel = xp_to_add, 1
                await conn.execute(
                    "INSERT INTO leveling (user_id, strength, powerlevel) VALUES ($1, $2, $3)",
                    user_id, strength, powerlevel
                )
            else:
                strength, powerlevel = result['strength'], result['powerlevel']
                strength += xp_to_add
                level_up_threshold = 100 * powerlevel

                if strength >= level_up_threshold:
                    powerlevel += 1
                    strength -= level_up_threshold
                    channel_id = os.getenv('CHANNEL')
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await channel.send(f"<@{user_id}> leveled up to level {powerlevel}!")

                await conn.execute(
                    "UPDATE leveling SET strength = $1, powerlevel = $2 WHERE user_id = $3",
                    strength, powerlevel, user_id
                )

    #updates the user stats, like the count of exercise and stores it in the database
    async def update_user_stats(self, user_id, xp_to_add, pushup_add=0, pullup_add=0, run_add=0, situp_add=0):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT pushup, pullup, run, situp, strength, powerlevel FROM leveling WHERE user_id = $1",
                user_id
            )

            if result is None:
                await conn.execute(
                    "INSERT INTO leveling (user_id, pushup, pullup, run, situp, strength, powerlevel) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    user_id, pushup_add, pullup_add, run_add, situp_add, xp_to_add, 1
                )
            else:
                pushup, pullup, run, situp, strength, powerlevel = (
                    result['pushup'], result['pullup'], result['run'], 
                    result['situp'], result['strength'], result['powerlevel']
                )

                pushup += pushup_add
                pullup += pullup_add
                run += run_add
                situp += situp_add
                strength += xp_to_add

                await conn.execute(
                    "UPDATE leveling SET pushup = $1, pullup = $2, run = $3, situp = $4, strength = $5, powerlevel = $6 WHERE user_id = $7",
                    pushup, pullup, run, situp, strength, powerlevel, user_id
                )

    #displays the overall fitness stats of the user, remember that the database is stored in neon tech postgreSQL
    @commands.command(name="fitness_stats")
    async def fitness_stats(self, ctx, member: discord.Member = None):
        """displays the users fitness stats"""
        member = member or ctx.author

        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM leveling WHERE user_id = $1",
                member.id
            )

        if result is None:
            if member == ctx.author:
                await ctx.send("You don't have any fitness data yet. Use the fitness form to log your activities!")
            else:
                await ctx.send(f"{member.display_name} doesn't have any fitness data yet.")
            return

        embed = discord.Embed(
            title=f"{member.display_name}'s Fitness Stats",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(name="Power Level", value=result['powerlevel'], inline=False)
        embed.add_field(name="Strength", value=result['strength'], inline=False)
        embed.add_field(name="Push-ups", value=result['pushup'], inline=True)
        embed.add_field(name="Pull-ups", value=result['pullup'], inline=True)
        embed.add_field(name="Running (Km)", value=result['run'], inline=True)
        embed.add_field(name="Sit-ups", value=result['situp'], inline=True)
        embed.set_footer(text="Keep up the great work!")

        await ctx.send(embed=embed)

    @commands.command(name="fitness_form")
    async def fitness_form(self, ctx):
        """generates a form that allows you to enter your exercise cycle for the day"""
        view = FitnessFormButton(self)
        await ctx.send("Click the button below to fill out the fitness form:", view=view)

# Fitness Form Modal
class FitnessForm(discord.ui.Modal):
    def __init__(self, cog):
        super().__init__(title="Fitness Input Form")
        self.cog = cog

        self.pushups = discord.ui.TextInput(
            label="How many pushups did you do?",
            placeholder="Enter a number",
            style=discord.TextStyle.short
        )
        self.add_item(self.pushups)

        self.situps = discord.ui.TextInput(
            label="How many sit-ups did you do?",
            placeholder="Enter a number",
            style=discord.TextStyle.short
        )
        self.add_item(self.situps)

        self.pullups = discord.ui.TextInput(
            label="How many pull-ups did you do?",
            placeholder="Enter a number",
            style=discord.TextStyle.short
        )
        self.add_item(self.pullups)

        self.run = discord.ui.TextInput(
            label="How many Kms did you run?",
            placeholder="Enter the distance",
            style=discord.TextStyle.short
        )
        self.add_item(self.run)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            pushups = int(self.pushups.value)
            situps = int(self.situps.value)
            pullups = int(self.pullups.value)
            run = int(self.run.value)

            pushup_points = pushups * 2
            situp_points = situps * 1
            pullup_points = pullups * 3
            run_points = run * 10
            total_points = pushup_points + situp_points + pullup_points + run_points

            await self.cog.update_user_stats(
                user_id=interaction.user.id,
                xp_to_add=total_points,
                pushup_add=pushups,
                pullup_add=pullups,
                run_add=run,
                situp_add=situps
            )

            await interaction.response.send_message(
                f"Great job! You earned {pushup_points} points for pushups, {pullup_points} points for pullups, "
                f"{situp_points} points for sit-ups, and {run_points} for running. Total: {total_points} points!",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "Invalid input. Please enter numeric values only.",
                ephemeral=True
            )

# Fitness Form Button
class FitnessFormButton(discord.ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        button = discord.ui.Button(label="Open Fitness Form", style=discord.ButtonStyle.primary)
        button.callback = self.open_form
        self.add_item(button)

    async def open_form(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FitnessForm(self.cog))

# Add the cog to the bot
async def setup(bot):
    await bot.add_cog(Fitness(bot))
