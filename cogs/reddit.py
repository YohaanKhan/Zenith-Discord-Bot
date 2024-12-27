import discord
from discord.ext import commands
from random import choice
import asyncpraw as praw
from dotenv import load_dotenv
import os

load_dotenv()


#Create a class reddit, we can get the client id, secret and user agent from the "https://www.reddit.com/prefs/apps", this website after creating an app.
class Leisure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT")
        )


#This is to check if the thing is actually working or not.
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")


#This creates a command that filters out reddit posts with the tag memes, it will then fetch 30 posts from the reddit API, filter the content using if loops and append the nested lists into the "posts_lists". In the end, we use the random function to output a random meme from the list.
    @commands.command()
    async def meme(self, ctx: commands.Context):
        """generates a random meme from the reddit."""
        subreddit = await self.reddit.subreddit("memes")
        posts_lists = []

        async for post in subreddit.hot(limit=30):
            if not post.over_18 and post.author is not None and any(post.url.endswith(ext) for ext in [".png",".jpg",".jpeg",".gif"]):
                author_name = post.author.name
                posts_lists.append((post.url, author_name))
            if post.author is None:
                posts_lists.append((posts_lists, "N/A"))

        if posts_lists:

            random_post = choice(posts_lists)

            meme_embed = discord.Embed(title="Random Meme", description="Fetches random meme for r/memes", color= discord.Color.random())
            meme_embed.set_author(name=f"Meme requested by {ctx.author.name}", icon_url=ctx.author.avatar)
            meme_embed.set_image(url=random_post[0])
            meme_embed.set_footer(text=f"Post created by {random_post[1]}.", icon_url=None)
            await ctx.send(embed = meme_embed)

        else:
            await ctx.send("Unable to fetch post, try again later.")


    #This command is for Jujutsu kaisen posts
    @commands.command()
    async def jjk(self, ctx: commands.Context):
        """generate a random jujutsu kaisen meme from the reddit."""
        subreddit = await self.reddit.subreddit("memes")
        posts_lists = []

        async for post in subreddit.search("Jujutsu Kaisen", limit=30):
            if not post.over_18 and post.author is not None and any(post.url.endswith(ext) for ext in [".png",".jpg",".jpeg",".gif"]):
                author_name = post.author.name
                posts_lists.append((post.url, author_name))
            if post.author is None:
                posts_lists.append((posts_lists, "N/A"))

        if posts_lists:

            random_post = choice(posts_lists)

            meme_embed = discord.Embed(title="Random Meme", description="Fetches random meme for r/jjk", color= discord.Color.random())
            meme_embed.set_author(name=f"Meme requested by {ctx.author.name}", icon_url=ctx.author.avatar)
            meme_embed.set_image(url=random_post[0])
            meme_embed.set_footer(text=f"Post created by {random_post[1]}.", icon_url=None)
            await ctx.send(embed = meme_embed)

        else:
            await ctx.send("Unable to fetch post, try again later.")


    #This command is for one piece posts
    @commands.command()
    async def one(self, ctx: commands.Context):
        """generate a random one-piece meme from the reddit."""
        subreddit = await self.reddit.subreddit("memes")
        posts_lists = []

        async for post in subreddit.search("One Piece", limit=30):
            if not post.over_18 and post.author is not None and any(post.url.endswith(ext) for ext in [".png",".jpg",".jpeg",".gif"]):
                author_name = post.author.name
                posts_lists.append((post.url, author_name))
            if post.author is None:
                posts_lists.append((posts_lists, "N/A"))

        if posts_lists:

            random_post = choice(posts_lists)

            meme_embed = discord.Embed(title="Random Meme", description="Fetches random meme for r/onepiece", color= discord.Color.random())
            meme_embed.set_author(name=f"Meme requested by {ctx.author.name}", icon_url=ctx.author.avatar)
            meme_embed.set_image(url=random_post[0])
            meme_embed.set_footer(text=f"Post created by {random_post[1]}.", icon_url=None)
            await ctx.send(embed = meme_embed)

        else:
            await ctx.send("Unable to fetch post, try again later.")


    #This command is for one piece posts
    @commands.command()
    async def slayer(self, ctx: commands.Context):
        """generate a random demon slayer meme from the reddit"""
        subreddit = await self.reddit.subreddit("memes")
        posts_lists = []

        async for post in subreddit.search("Demon Slayer", limit=30):
            if not post.over_18 and post.author is not None and any(post.url.endswith(ext) for ext in [".png",".jpg",".jpeg",".gif"]):
                author_name = post.author.name
                posts_lists.append((post.url, author_name))
            if post.author is None:
                posts_lists.append((posts_lists, "N/A"))

        if posts_lists:

            random_post = choice(posts_lists)

            meme_embed = discord.Embed(title="Random Meme", description="Fetches random meme for r/demonslayer", color= discord.Color.random())
            meme_embed.set_author(name=f"Meme requested by {ctx.author.name}", icon_url=ctx.author.avatar)
            meme_embed.set_image(url=random_post[0])
            meme_embed.set_footer(text=f"Post created by {random_post[1]}.", icon_url=None)
            await ctx.send(embed = meme_embed)

        else:
            await ctx.send("Unable to fetch post, try again later.")


    def cog_unload(self):
        self.bot.loop.create_task(self.reddit.close())

async def setup(bot):
    await bot.add_cog(Leisure(bot))