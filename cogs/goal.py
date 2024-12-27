import discord
from discord.ext import commands
import asyncpg
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

class GoalManagement(commands.Cog):
    def __init__(self, bot, db_pool):
        self.bot = bot
        self.db_pool = db_pool

    @commands.Cog.listener()
    async def on_ready(self):
        # Ensure the table exists and has the 'completed' column
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS goals (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    name TEXT NOT NULL,
                    deadline DATE NOT NULL,
                    priority TEXT NOT NULL,
                    progress INTEGER DEFAULT 0,
                    completed BOOLEAN DEFAULT FALSE
                )
            ''')

    @commands.command(name='set_goal')
    async def set_goal(self, ctx, goal_name: str, deadline: str, priority: str):
        """allows you to set a goal"""
        try:
            deadline_date = datetime.strptime(deadline, "%d-%m-%Y").date()
            user_id = ctx.author.id

            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO goals (user_id, name, deadline, priority, progress, completed)
                    VALUES ($1, $2, $3, $4, $5, $6)
                ''', user_id, goal_name, deadline_date, priority, 0, False)

            await ctx.send(f"Goal '{goal_name}' added successfully with deadline {deadline} and priority {priority}.")
        except Exception as e:
            await ctx.send("An error occurred while setting the goal.")
            print(e)

    @commands.command(name='view_goals')
    async def view_goals(self, ctx):
        """displays the list of all the goals and its progress"""
        user_id = ctx.author.id

        async with self.db_pool.acquire() as conn:
            goals = await conn.fetch('''
                SELECT name, deadline, priority, progress
                FROM goals
                WHERE user_id = $1 AND completed = FALSE
                ORDER BY priority, deadline
            ''', user_id)

        if not goals:
            await ctx.send("You have no active goals.")
            return

        embed = discord.Embed(title="Your Goals", color=discord.Color.blue())
        for goal in goals:
            progress_bar = self.create_progress_bar(goal['progress'])
            deadline_str = goal['deadline'].strftime('%d-%m-%Y')
            embed.add_field(
                name=f"{goal['name']} (Priority: {goal['priority']})",
                value=(f"Progress: {progress_bar} ({goal['progress']}%)\n"
                       f"Deadline: 🔴 {deadline_str}"),
                inline=False
            )
        await ctx.send(embed=embed)

    def create_progress_bar(self, progress):
        total_blocks = 20
        filled_blocks = int((progress / 100) * total_blocks)
        empty_blocks = total_blocks - filled_blocks
        return f"[{filled_blocks * '█'}{empty_blocks * '░'}]"

    @commands.command(name='update_goal')
    async def update_goal(self, ctx, goal_name: str, field: str, value):
        """updates the specified parameter of the goal"""
        user_id = ctx.author.id

        async with self.db_pool.acquire() as conn:
            goal = await conn.fetchrow('''SELECT * FROM goals WHERE user_id = $1 AND name = $2''', user_id, goal_name)

            if not goal:
                await ctx.send(f"Goal '{goal_name}' not found.")
                return

            if field == 'progress':
                progress = int(value)
                await conn.execute('''UPDATE goals SET progress = $1 WHERE user_id = $2 AND name = $3''', progress, user_id, goal_name)

                # If the progress reaches 100%, mark the goal as completed
                if progress == 100:
                    await conn.execute('''UPDATE goals SET completed = TRUE WHERE user_id = $1 AND name = $2''', user_id, goal_name)
                    await ctx.send(f"Goal '{goal_name}' has been marked as completed.")
                else:
                    await ctx.send(f"Progress for goal '{goal_name}' updated to {progress}%.")
            elif field == 'deadline':
                new_deadline = datetime.strptime(value, "%d-%m-%Y").date()
                await conn.execute('''UPDATE goals SET deadline = $1 WHERE user_id = $2 AND name = $3''', new_deadline, user_id, goal_name)
                await ctx.send(f"Deadline for goal '{goal_name}' updated to {value}.")
            elif field == 'priority':
                await conn.execute('''UPDATE goals SET priority = $1 WHERE user_id = $2 AND name = $3''', value, user_id, goal_name)
                await ctx.send(f"Priority for goal '{goal_name}' updated to {value}.")
            else:
                await ctx.send("Invalid field. You can update 'progress', 'deadline', or 'priority'.")

    @commands.command(name='delete_goal')
    async def delete_goal(self, ctx, goal_name: str):
        """deletes the specified goal"""
        user_id = ctx.author.id

        async with self.db_pool.acquire() as conn:
            result = await conn.execute('''DELETE FROM goals WHERE user_id = $1 AND name = $2''', user_id, goal_name)

            if result == "DELETE 0":
                await ctx.send(f"Goal '{goal_name}' not found.")
            else:
                await ctx.send(f"Goal '{goal_name}' deleted successfully.")

    @commands.command(name='view_completed_goals')
    async def view_completed_goals(self, ctx):
        """returns the list of completed user goals"""
        user_id = ctx.author.id

        async with self.db_pool.acquire() as conn:
            completed_goals = await conn.fetch('''
                SELECT name, deadline, priority, progress
                FROM goals
                WHERE user_id = $1 AND completed = TRUE
                ORDER BY deadline
            ''', user_id)

        if not completed_goals:
            await ctx.send("You have no completed goals.")
            return

        embed = discord.Embed(title="Completed Goals", color=discord.Color.green())
        for goal in completed_goals:
            deadline_str = goal['deadline'].strftime('%d-%m-%Y')
            embed.add_field(
                name=f"{goal['name']} (Priority: {goal['priority']})",
                value=(f"Progress: 100%\n"
                       f"Deadline: ✅ {deadline_str}"),
                inline=False
            )
        await ctx.send(embed=embed)

# Add this cog to the bot
async def setup(bot):
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    
    db_pool = await asyncpg.create_pool(
        user=db_user,
        password=db_password,
        database=db_name,
        host=db_host,
        port=db_port
    )
    await bot.add_cog(GoalManagement(bot, db_pool))
