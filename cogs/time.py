import discord
from discord.ext import commands, tasks
import asyncpg
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

class TimeManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.setup_database())
        self.running_timers = {}  # Store active timers: {user_id: (start_time, task_name)}

    async def setup_database(self):
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_name = os.getenv('DB_NAME')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT')
        # Connect to the database
        self.pool = await asyncpg.create_pool(
            user=db_user,
            password=db_password,
            database=db_name,
            host=db_host,
            port=db_port
        )

        # Create necessary tables
        async with self.pool.acquire() as conn:
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS time_management (
                user_id BIGINT PRIMARY KEY,
                timex INTEGER DEFAULT 0,
                daily_goal_complete BOOLEAN DEFAULT FALSE
            )
            ''')

            await conn.execute('''
            CREATE TABLE IF NOT EXISTS timers (
                user_id BIGINT,
                task_name TEXT,
                start_time TIMESTAMP,
                duration INTEGER, -- In minutes
                completed BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (user_id, task_name)
            )
            ''')

            await conn.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                user_id BIGINT,
                schedule_date DATE,
                task_name TEXT,
                task_time TIME,
                is_weekly BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (user_id, schedule_date, task_name)
            )
            ''')

    async def update_timex(self, user_id, points_to_add):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("SELECT timex FROM time_management WHERE user_id = $1", user_id)
            if result is None:
                await conn.execute("INSERT INTO time_management (user_id, timex) VALUES ($1, $2)", user_id, points_to_add)
            else:
                timex = result['timex'] + points_to_add
                await conn.execute("UPDATE time_management SET timex = $1 WHERE user_id = $2", timex, user_id)

    @commands.command(name="start_timer")
    async def start_timer(self, ctx, task_name: str):
        """Start a timer for a specific task."""
        if ctx.author.id in self.running_timers:
            await ctx.send("You already have a running timer. End it before starting a new one.")
            return

        self.running_timers[ctx.author.id] = (datetime.utcnow(), task_name)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO timers (user_id, task_name, start_time) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                ctx.author.id, task_name, datetime.utcnow()
            )

        await ctx.send(f"Timer started for task: `{task_name}`.")

    @commands.command(name="check_timer")
    async def check_timer(self, ctx):
        """Check how much time is left on a task timer."""
        timer = self.running_timers.get(ctx.author.id)
        if not timer:
            await ctx.send("You don't have any running timers.")
            return

        start_time, task_name = timer
        elapsed = datetime.utcnow() - start_time
        minutes_elapsed = elapsed.total_seconds() // 60

        await ctx.send(f"Task `{task_name}` has been running for {minutes_elapsed:.0f} minutes.")

    @commands.command(name="end_timer")
    async def end_timer(self, ctx):
        """End a running timer and calculate Timex points."""
        timer = self.running_timers.pop(ctx.author.id, None)
        if not timer:
            await ctx.send("You don't have any running timers to end.")
            return

        start_time, task_name = timer
        elapsed = datetime.utcnow() - start_time
        minutes_elapsed = int(elapsed.total_seconds() // 60)

        # Calculate Timex points
        points = minutes_elapsed + (10 if minutes_elapsed > 0 else 0) + (5 if minutes_elapsed > 60 else 0)
        await self.update_timex(ctx.author.id, points)

        # Update database
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE timers SET duration = $1, completed = TRUE WHERE user_id = $2 AND task_name = $3",
                minutes_elapsed, ctx.author.id, task_name
            )

        await ctx.send(f"Timer for `{task_name}` ended. You earned {points} Timex!")

    @commands.command(name="set_schedule")
    async def set_schedule(self, ctx, task_name: str, time: str, is_weekly: bool = False):
        """Set a daily or weekly schedule for tasks."""
        task_time = datetime.strptime(time, "%H:%M").time()
        schedule_date = datetime.utcnow().date()

        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO schedules (user_id, schedule_date, task_name, task_time, is_weekly) VALUES ($1, $2, $3, $4, $5)",
                ctx.author.id, schedule_date, task_name, task_time, is_weekly
            )

        await ctx.send(f"Schedule set for `{task_name}` at {time} {'weekly' if is_weekly else 'daily'}.")

    @commands.command(name="view_schedule")
    async def view_schedule(self, ctx):
        """View the user's schedule for the day or week."""
        today = datetime.utcnow().date()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT task_name, task_time, is_weekly FROM schedules WHERE user_id = $1 AND (schedule_date = $2 OR is_weekly = TRUE)",
                ctx.author.id, today
            )

        if not rows:
            await ctx.send("You don't have any scheduled tasks.")
            return

        embed = discord.Embed(title=f"{ctx.author.display_name}'s Schedule", color=discord.Color.blue())
        for row in rows:
            embed.add_field(
                name=row['task_name'],
                value=f"Time: {row['task_time']}, {'Weekly' if row['is_weekly'] else 'Daily'}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="set_reminder")
    async def set_reminder(self, ctx, reminder_text: str, time: str):
        """Set a reminder."""
        reminder_time = datetime.strptime(time, "%H:%M").time()
        now = datetime.utcnow()
        reminder_datetime = datetime.combine(now.date(), reminder_time)
        if reminder_datetime < now:
            reminder_datetime += timedelta(days=1)

        @tasks.loop(seconds=1, count=1)
        async def send_reminder():
            await ctx.send(f"⏰ Reminder: {reminder_text}")

        delay = (reminder_datetime - now).total_seconds()
        send_reminder.change_interval(seconds=delay)
        send_reminder.start()

        await ctx.send(f"Reminder set for `{reminder_text}` at {time}.")

    @commands.command(name="pomodoro")
    async def pomodoro(self, ctx):
        """Start a Pomodoro timer (25 minutes work, 5 minutes break)."""
        await ctx.send("Starting a Pomodoro timer: 25 minutes of work starting now!")

        await asyncio.sleep(25 * 60)
        await ctx.send("Time to take a 5-minute break!")
        await asyncio.sleep(5 * 60)
        await ctx.send("Break over! Ready for the next Pomodoro?")

    @commands.command(name="view_productivity")
    async def view_productivity(self, ctx, period: str = "week"):
        """View productivity report."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT task_name, duration FROM timers WHERE user_id = $1 AND completed = TRUE AND start_time > (NOW() - INTERVAL '1 {period}')",
                ctx.author.id
            )

        if not rows:
            await ctx.send(f"No tasks completed in the past {period}.")
            return

        total_time = sum(row['duration'] for row in rows)
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Productivity ({period})",
            color=discord.Color.green()
        )
        embed.add_field(name="Total Time Spent", value=f"{total_time} minutes", inline=False)
        for row in rows:
            embed.add_field(name=row['task_name'], value=f"{row['duration']} minutes", inline=True)

        await ctx.send(embed=embed)

    @commands.command(name="daily_goal")
    async def daily_goal(self, ctx):
        """Set and reward for daily goal completion."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("SELECT daily_goal_complete FROM time_management WHERE user_id = $1", ctx.author.id)
            if result and result['daily_goal_complete']:
                await ctx.send("You have already completed your daily goal today!")
                return

            await conn.execute(
                "UPDATE time_management SET timex = timex + 50, daily_goal_complete = TRUE WHERE user_id = $1",
                ctx.author.id
            )
        await ctx.send("Congratulations on completing your daily goal! You earned 50 Timex.")

    @commands.command(name="delete_schedule")
    async def delete_schedule(self, ctx, task_name: str, time: str):
        """Delete a schedule by task name and time."""
        try:
            # Convert the string time to datetime object and extract time
            task_time = datetime.strptime(time, "%H:%M").time()

            async with self.pool.acquire() as conn:
                # Delete the schedule from the database where the task_name and task_time match
                result = await conn.execute(
                    "DELETE FROM schedules WHERE user_id = $1 AND task_name = $2 AND task_time = $3",
                    ctx.author.id, task_name, task_time
                )

                if result == "DELETE 0":
                    await ctx.send(f"No schedule found for task '{task_name}' at {time}.")
                else:
                    await ctx.send(f"Schedule for task '{task_name}' at {time} has been deleted.")
        except Exception as e:
            await ctx.send(f"An error occurred while deleting the schedule: {e}")
            print(e)

async def setup(bot):
    await bot.add_cog(TimeManagement(bot))
