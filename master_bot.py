'''
Created on Jul 15, 2018
@author: yung_messiah
'''
import asyncio
import bs4
import datetime
import discord
import json
import logging
import os
import pymongo
import pytz
import random
import re
import requests
import string
import time
import _thread
import stripe
import names
import twitter
import shopifyy
import solebox
from twilio.rest import Client
# from datetime import datetime
from decimal import Decimal
from discord.ext.commands import Bot
from discord.utils import get
from discord.errors import LoginFailure, HTTPException
from discord.embeds import Embed 
from threading import Thread
from bs4 import BeautifulSoup

server_id = "355178719809372173"
footer_text = 'Powered by FOMO | @FOMO_supply'
member_role = 'Member'
sub_channel = 'subs'
sitelist_link = 'https://goo.gl/b7m6hi'
guide_link = 'https://goo.gl/HhtiYL'
mongo_sms_url = 'mongodb://heroku_lgwq2009:jge233cq5v9ouqv8fajurm3dnm@ds161144.mlab.com:61144/heroku_lgwq2009'
discord_owner_id = '460997994121134082'
icon_img = 'https://i.imgur.com/5fSzax1.jpg'
twitter_consumer_key = 'xl7NGsDQFkEqjBZZlFeevVKNd'
twitter_consumer_secret = 'SEDqpBcG0nSCx7AA5PSAkCxbKsipyNANPzAqoCRBIuP7T0FBDx'
twitter_access_token = '1062494333180485632-JlSb9XCLG2CutesQlGkj6IJXmBEPXU'
twitter_access_secret = 'dTuDD8Czvh131ei2I4xozumvQMTy70PCdaqRIN2iGcB8d'
twilio_from = 'FOMO%20Alerts'
twilio_auth_token = '8cde20027a5a740c8ef291e90f78a25d'
twilio_sid = 'AC351781f47036b9e7a9378e9f035e14e7'
twilio_number = '"+16148108716"'

# Discord command triggers
BOT_PREFIX = ("?", "!")
# General Discord Bot Description
BOT_DESCRIPTION = '''**FOMO Helper** is a general service bot for all your consumer needs.

There are a couple of utility commands which are showcased here, and should serve you well.

To use all commands, precede the keyword by an exclamation mark (!) or a question mark (?).

Example:
    !gmail example@gmail.com
                OR
    ?gmail example@gmail.com
'''

# Token for Discord Bot 
TOKEN = os.environ["FOMO_HELPER_BOT_TOKEN"]
# URI for Mongo/Heroku Database
MONGODB_URI = os.environ["FOMO_HELPER_MONGODB_URI"]

''' Initiliaze Stripe api with correct credential '''
stripe.api_version = "2018-11-08"
FOMO_STRIPE_KEY = "sk_live_L9N3yTtjVRnyySzf0nSn6BRD"
MOREHYPED_STRIPE_KEY = "sk_live_22BhRSioB4It4EgGxPZEM9Wr"

# stripe.api_key = "sk_live_L9N3yTtjVRnyySzf0nSn6BRD"
# Create Discord Bot instance with the given command triggers
client = Bot(command_prefix=BOT_PREFIX)#, description=BOT_DESCRIPTION#)
# Remove the default Discord help command
client.remove_command('help')
# Reference to Mongo/Heroku database
db = None
# Reference to subscriptions collection
subscriptions = None

ebay_used_urls = []
# Stripe class reference
STRIPE = None
# Krispy Kreme class reference
KRISPYKREME = None
SUCCESS_POSTER = None
SMS = None 

# Header to make the requests
headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'}

# ------------------------------------------------------------- #
#                                                               #
#                 Method to make use of TinyURL                 #
#                                                               #   
# ------------------------------------------------------------- #
''' Makes use of TinyURL to shorten the URL for the Shopify items
    
    @param url: URL to be shortened
    @param ctx: Discord information
    @return: The shortened url '''
def tiny(url, ctx):
    URL = "https://tinyurl.com/create.php?source=indexpage&url=" + url + "&submit=Make+TinyURL%21&alias="
    raw_HTML = requests.get(URL, headers=headers, timeout=10)
        
    if raw_HTML.status_code != 200:
        client.send_message(ctx.message.channel, "An error has occurred completing your request")
        return None
    else:
        page = bs4.BeautifulSoup(raw_HTML.text, 'lxml')
        return page.find_all('div', {'class': 'indent'})[1].b.string
    
    
''' Subscribes user to service by adding them to the database and assigning the appropriate role(s).
    @param email: The email to be added to the database
    @param author: User responsible for sending authentication message '''
async def sub_and_assign_roles(email, author):
    # Reference to the FOMO discord server
    discord_server = client.get_server(server_id)

    role = get(discord_server.roles, name=member_role)
    user = discord_server.get_member(author.id)
    await client.add_roles(user, role)

    # Send message on Discord
    await client.send_message(author, "Your subscription has been successfully activated!")
    return True

# ------------------------------------------------------------- #
#                                                               #
#                 All the Discord Bot methods                   #
#                                                               #   
# ------------------------------------------------------------- #
''' Discord event, triggered upon successful Login '''
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.change_presence(game=discord.Game(name='!help'), status=None,afk=False)
    
    
''' Method triggered by server event when a member leaves the Discord group 
    @param member: User leaving the server. '''
@client.event
async def on_member_remove(member):
    # Search for user data in database
    data = subscriptions.find_one({"discord_id": f"{member.id}"})
    # Take no actions if no data found in database
    if data == None:
        pass
    else:
        # Switch user's subscription status
        status = data["status"]
        
        if status == "disabled":
            pass
        else:
            for role in member.roles:
                if member_role in role.name:
                    result = subscriptions.update_one({
                        "discord_id": member.id
                    }, {
                        "$set": {
                            "status": "disabled"
                        }
                    }, upsert=False)
    
''' Method triggered by server event when a member sends a message in the Discord group
    
    @param message: Message sent by the user in the server '''
@client.event
async def on_message(message):
    # Don't want the bot to reply to itself
    if message.author == client.user:
        return 
    
    if message.channel.name == sub_channel:
        await STRIPE.process_payment(message)
    
    if message.channel.name == "success":
        author = str(message.author) 
        author = author[:-5]
        attachment_count = len(message.attachments)
        if attachment_count > 0:
            for attachment in message.attachments:
                image = attachment["url"]
                SUCCESS_POSTER.success_poster(author, image)
    
    if message.content.startswith('sms!help'):
        await SMS.sms_help(message)
    elif message.content.startswith('sms!send'):
        await SMS.send_sms(message)
    elif message.content.startswith('sms!stop'):
        await SMS.remove_user(message)
    elif message.content.startswith('sms!update'):
        number = str(message.content)
        number = number.replace("sms!update ","")
        await SMS.update_user(message, number)
    elif message.content.startswith('sms!check'):
        await SMS.check_user(message)
    elif message.content.startswith('sms!add'):
        number = str(message.content)
        number = number.replace("sms!add ","")
        await SMS.add_user(message, number)
    
    # Make sure the message sent is not a command
    if not message.content.startswith('!') and not message.content.startswith('?'):
        # Automate responses by displaying specific output based on user message if necessary

        if re.search('fomo', message.content, re.IGNORECASE):
            if re.search('guide|how\s+to|works|work|tutorial', message.content, re.IGNORECASE):
                embed=discord.Embed(title="FOMO GUIDE", 
                                    description="[CLICK HERE]({})".format(guide_link),
                                    colour=discord.Colour(0xffffff))
                embed.set_thumbnail(url=icon_img)
                embed.set_footer(icon_url=icon_img, text=footer_text)
                await client.send_message(message.channel, embed=embed)

        
            elif re.search('sitelist|list|droplist', message.content, re.IGNORECASE):
                embed=discord.Embed(title="FOMO SITELIST", 
                                    description="[CLICK HERE]({})".format(sitelist_link),
                                    colour=discord.Colour(0xffffff))
                embed.set_thumbnail(url=icon_img)
                embed.set_footer(icon_url=icon_img, text=footer_text)
                await client.send_message(message.channel, embed=embed)
    else:
        # If it's a command that was sent, process the command normally
        await client.process_commands(message)


''' Discord custom help command, formatted differently from the default help command
    @param ctx: Discord information
    @param *command: List of arguments passed with the command '''  
@client.command(name='help',
                description='Help message to guide the user through using the bot.',
                pass_context=True)
async def custom_help(ctx, *command):
    author = ctx.message.author
    
    if len(command) == 0:
        embed = Embed(
            color = 0xffffff,
            description = BOT_DESCRIPTION
        )
        
        keywords = '*!address* \n*!gmail* \n*!atc* \n*!isshopify* \n*!fee* \n*!activate* \n*!cancel* \n*sms!help* \n*!donutuk* \n*!shopify* \n*!solebox* \n*!ebayviews* \n*!ebaywatch* \n*!delay*'
        keyword_descriptions = 'Jig your home address\n'
        keyword_descriptions += 'Jig your gmail address\n'
        keyword_descriptions += 'Generate ATC for a shopify URL\n'
        keyword_descriptions += 'Checks if a website is Shopify\n'
        keyword_descriptions += 'Calculates seller profits after fees on all websites.\n'
        keyword_descriptions += 'Authenticates members and assigns correct role\n'
        keyword_descriptions += 'Cancel your current subscription\n'
        keyword_descriptions += 'Signup, change, or remove your number from SMS alerts\n'
        keyword_descriptions += 'Get a Krispy Kreme doughnut using your Gmail prefix!\n'
        keyword_descriptions += 'Generate accounts on Shopify\n'
        keyword_descriptions += 'Generate accounts on Solebox\n'
        keyword_descriptions += 'Generate views on your eBay listing\n'
        keyword_descriptions += 'Generate watchers on your eBay listing\n'
        keyword_descriptions += 'Get the perfect delay to use on Shopify websites.'
          
        embed.add_field(name='Keywords:', value=keywords, inline=True)
        embed.add_field(name='Brief:', value=keyword_descriptions, inline=True)
        embed.add_field(name='More Info', value="For more information on a keyword, type **!help keyword**", inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)    
    elif (len(command) > 0 and (command[0] == 'gmail' or command[0] == 'mail' or command[0] == 'email')):
        desc =  'This command manipulates any gmail address passed to it as a parameter.'
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ gmail | mail | email ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'address' or command[0] == 'adr' or command[0] == 'addr')):
        desc = 'This command manipulates any residential address passed to it as a parameter.'
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ address | addr | adr ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'atc')):
        desc = 'Add To Cart command for any Shopify website. Generates a link leading the user '
        desc += 'straight to the payment page. Takes in the item\'s URL as a parameter'
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ atc ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'isshopify')):
        desc = 'This command uses a given URL in order to determine whether '
        desc += 'a website is a shopify site or not.'
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ isshopify ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'fee')):
        desc = "Calculates the seller fees applied by different websites."
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ fee ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'activate')):
        desc = "Activate your subscription in our server and get access to all our content."
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ activate ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'cancel')):
        desc = "Cancel your subscription in our server by passing the email used to subscribe as a parameter."
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ cancel ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'donutuk')):
        desc = "Get yourself a free Krispy Kreme doughnut by passing your email prefix as a parameter.\nExample: if your Gmail is john@gmail.com, say `!donutuk john` to get a free donut!"
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ donutuk ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)

    elif (len(command) > 0 and (command[0] == 'shopify')):
        desc = "Generate an account on any Shopify website using your Gmail address."
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ shopify ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'solebox')):
        desc = "Generate an account on Solebox using your catchall domain."
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ solebox ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'ebayviews')):
        desc = "Generate 200 views on your eBay listing."
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ ebayviews ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'ebaywatch')):
        desc = "Generate watchers on your eBay listing.\nFormat: `!ebaywatch link watchers`\nExample: `!ebaywatch https://www.ebay.com/itm/MYITEM 5` will add 5 watchers to your listng.\nMaximum is 10!"
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ ebaywatch ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'delay')):
        desc = "Calculate the perfect delay to use when botting Shopify. The delay calculated here will **never** get you banned!"
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ delay ]', inline=False)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)


@client.command(name='calendar', pass_context=True)
async def post_calendar(ctx):
    author = ctx.message.author
    channel = '534057583426797568'

    await client.send_message(author, 'PASSWORD?')
    password = await client.wait_for_message(author=author)
    password = str(password.content).lower()
    
    if password != 'saopaulo321':
        return await client.send_message(author, 'You do not have permissions to use this command.')

    elif password == 'saopaulo321':

        #JORDAN 1 CRIMSON START
        embed=discord.Embed(title='__**AIR JORDAN 1 RETRO HIGH HYPER CRIMSON**__', description="***JANUARY 24TH***", color=0xffffff)
        embed.set_thumbnail(url="https://stockx-360.imgix.net/Air-Jordan-1-Retro-High-Neutral-Grey-Hyper-Crimson/Images/Air-Jordan-1-Retro-High-Neutral-Grey-Hyper-Crimson/Lv2/img01.jpg")
        
        embed.add_field(name="RETAIL:", value="USD $160", inline=True)
        embed.add_field(name="RESELL:", value="USD $200-250", inline=True)
        embed.add_field(name="STOCK LEVEL:", value="HIGH", inline=True)
        embed.add_field(name="MONEY SIZES:", value="SMALLER/BAE SIZES", inline=True)
        embed.add_field(name="STYLE CODE:", value="555088-018", inline=True)
        embed.add_field(name="MARKET:", value="[CLICK HERE](https://web.suplexed.com/555088-018/jordan-1-retro-high-neutral-grey-hyper-crimson)", inline=True)
        embed.set_footer(icon_url="https://i.imgur.com/5fSzax1.jpg", text="Powered by FOMO | @FOMO_supply | Information Subject to Change!")
        await client.send_message(author, 'SAMPLE MESSAGE, SAY ANYTHING TO CONTINUE.\nSAY "CANCEL" AT ANYTIME TO CANCEL', embed=embed)
        ready = await client.wait_for_message(author=author)
        ready = str(ready.content).upper()
        if 'CANCEL' in ready:
            return await client.send_message(author, 'CANCELLED')
        #JORDAN 1 CRIMSON END
        await client.send_message(author, 'ENTER THE PRODUCT TITLE')
        title = await client.wait_for_message(author=author)
        title = str(title.content).upper()
        title = "__**" + title + "**__"
        if 'CANCEL' in title:
            return await client.send_message(author, 'CANCELLED')
        await client.send_message(author, 'ENTER THE PRODUCT RELEASE DATE, FOLLOW THE FORMAT IN THE EXAMPLE')
        reldate = await client.wait_for_message(author=author)
        reldate = str(reldate.content).upper()
        reldate = "***" + reldate + "***"
        if 'CANCEL' in reldate:
            return await client.send_message(author, 'CANCELLED')
        await client.send_message(author, 'RETAIL (IN USD WITH $, FOLLOW THE FORMAT IN THE EXAMPLE)')
        retail = await client.wait_for_message(author=author)
        retail = str(retail.content).upper()
        if 'CANCEL' in retail:
            return await client.send_message(author, 'CANCELLED')
        await client.send_message(author, 'ESTIAMTED RESELL VALUE (IN USD WITH $, FOLLOW THE FORMAT IN THE EXAMPLE)')
        resell = await client.wait_for_message(author=author)
        resell = str(resell.content).upper()
        if 'CANCEL' in resell:
            return await client.send_message(author, 'CANCELLED')
        await client.send_message(author, 'STOCK LEVEL (LOW-MEDIUM-HIGH):')
        levels = await client.wait_for_message(author=author)
        levels = str(levels.content).upper()
        if 'CANCEL' in levels:
            return await client.send_message(author, 'CANCELLED')
        await client.send_message(author, 'MONEY SIZE RANGE (SPECIFY SIZES IN US, OR JUST SAY BAE SIZES FOR EXAMPLE):')
        bestsizes = await client.wait_for_message(author=author)
        bestsizes = str(bestsizes.content).upper()
        if 'CANCEL' in bestsizes:
            return await client.send_message(author, 'CANCELLED')
        await client.send_message(author, 'STYLE CODE (PLEASE DOULBE CHECK):')
        stylecode = await client.wait_for_message(author=author)
        stylecode = str(stylecode.content).upper()
        if 'CANCEL' in stylecode:
            return await client.send_message(author, 'CANCELLED')
        await client.send_message(author, 'SUPLEXED LINK:')
        suplink = await client.wait_for_message(author=author)
        suplink = str(suplink.content).lower()
        if 'CANCEL' in suplink:
            return await client.send_message(author, 'CANCELLED')
        await client.send_message(author, 'IMAGE URL (MAKE SURE URL ENDS IN .JPG OR .PNG FOR EXAMPLE):')
        imgurl  = await client.wait_for_message(author=author)
        imgurl = str(imgurl.content).lower()


        embed=discord.Embed(title=title, description=reldate, color=0xffffff)
        embed.set_thumbnail(url=imgurl)
        
        embed.add_field(name="RETAIL:", value=str(retail), inline=True)
        embed.add_field(name="RESELL:", value=str(resell), inline=True)
        embed.add_field(name="STOCK LEVEL:", value=str(levels), inline=True)
        embed.add_field(name="MONEY SIZES:", value=str(bestsizes), inline=True)
        embed.add_field(name="STYLE CODE:", value=str(stylecode), inline=True)
        embed.add_field(name="MARKET:", value="[CLICK HERE]({})".format(imgurl), inline=True)
        embed.set_footer(icon_url="https://i.imgur.com/5fSzax1.jpg", text="Powered by FOMO | @FOMO_supply | Information is Subject to Change!")


        await client.send_message(author, "LOOKING GOOD?", embed=embed)
        await client.send_message(author, "Say `Yes` or `Y` if you are done, and `N` or `no` if you aren't.")
        response  = await client.wait_for_message(author=author)

        if 'y' in str(response.content).lower():
            await client.send_message(client.get_channel(channel), embed=embed)
            await client.send_message(author, 'MESSAGE POSTED')
        else:
            return await client.send_message(author, 'Please try again by saying `!calendar`')


@client.command(name='delay',
                pass_context=True)
async def delay_calc(ctx):
    author = ctx.message.author
    embed = discord.Embed(title="UNBANNABLE SHOPIFY MONITOR DELAY CALCULATOR", description="How many proxies do you have?", color=0xffffff)
    embed.set_footer(icon_url=icon_img, text=footer_text)
    await client.send_message(author, embed=embed)  
    proxies = await client.wait_for_message(author=author)
    proxies = proxies.content
    embed = discord.Embed(title="UNBANNABLE SHOPIFY MONITOR DELAY CALCULATOR", description="How many tasks do you have?", color=0xffffff)
    embed.set_footer(icon_url=icon_img, text=footer_text)
    await client.send_message(author, embed=embed) 
    tasks = await client.wait_for_message(author=author)
    tasks = tasks.content
    tasks = int(tasks)
    proxies = int(proxies)
    delay = str(3500/(proxies/tasks))
    embed = discord.Embed(title="UNBANNABLE SHOPIFY MONITOR DELAY CALCULATOR", description="Delay to never get banned: {} ms".format(delay), color=0xffffff)
    embed.set_footer(icon_url=icon_img, text=footer_text)
    await client.send_message(author, embed=embed) 




@client.command(name='chargedaily',
                pass_context=True)
async def charge_daily(ctx):
    await STRIPE.recurring_charges()    


''' Function for personal use; check if any other Discord server got access to FOMO Helper,
    and prevent them from freely using our bot 
    
    @param ctx: Discord information '''
@client.command(name='connectedservers',
                description='Displays a list of servers the bot is connected to.',
                pass_context=True)
async def servers_list(ctx):
    author = ctx.message.author
    servers = client.servers
    message = "The connected servers are:\n"
    for server in servers:
        message += f"\t- {server.name}: {server.id}\n"
        
    await client.send_message(author, message)

@client.command(name='shopify', pass_context=True)
async def shopifyyy(ctx):
    author = ctx.message.author
    embed = discord.Embed(title="SHOPIFY ACCOUNTE GENERATOR", description="Generate accounts on any Shopify website.", color=0xffffff)
    embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/social-media-2092/100/social-35-512.png')
    embed.add_field(name="PLEASE ENTER A SHOPIFY STORE URL", value='FOR EXAMPLE: `https://kith.com/`')
    await client.send_message(author, embed=embed)
    url = await client.wait_for_message(author=author)
    url = url.content
    check = shopifyy.shopify_check(url)

    if check == False:
        embed = discord.Embed(title="SHOPIFY ACCOUNTE GENERATOR", description="Generate accounts on any Shopify website.", color=0xffffff)
        embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/social-media-2092/100/social-35-512.png')
        embed.add_field(name="INVALID SHOPIFY URL", value="Make sure you enter a valid Shopify URL.\nIf the Shopify store has a password page up, or if the given URL isn't a Shopify URL, no account will be generated.")
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)
        return


    embed = discord.Embed(title="ENTER YOUR CATCHALL DOMAIN", description="If you are not sure what this is, please watch [this video](https://www.youtube.com/watch?v=tx4-LNKK5d8)", color=0xffffff)
    await client.send_message(author, embed=embed)
    
    catchall = await client.wait_for_message(author=author)
    catchall = catchall.content

    embed = discord.Embed(title="ACCOUNT IS BEING GENERATED", description="Please allow up to 2 minutes.", color=0xffffff)
    
    edit_this = await client.send_message(author, embed=embed)
    credentials = shopifyy.shopify_gen(url,catchall)
    username, password = credentials.split(':')

    embed = discord.Embed(title="ACCOUNT GENERATED!", description="Generated on: `%s`" % url, color=0xffffff)
    embed.add_field(name="EMAIL:", value=username)
    embed.add_field(name="PASSWORD:", value=password, inline=False)
    embed.set_footer(icon_url=icon_img, text=footer_text)
    await client.edit_message(edit_this, embed=embed)    

@client.command(name='solebox', pass_context=True)
async def add_user2(ctx):
    author = ctx.message.author


    embed = discord.Embed(title="SOLEBOX ACCOUNTE GENERATOR", description="Generate accounts on [Solebox](https://solebox.com).", color=0xffffff)
    embed.set_thumbnail(url='https://i.imgur.com/GoEB99v.jpg')
    embed.add_field(name="PLEASE ENTER YOUR CATCHALL DOMAIN", value="If you are not sure what this is, please watch [this video](https://www.youtube.com/watch?v=tx4-LNKK5d8)")
    await client.send_message(author, embed=embed)

    catchall = await client.wait_for_message(author=author)
    catchall = catchall.content

    embed = discord.Embed(title="ACCOUNT IS BEING GENERATED", description="Please allow up to 2 minutes.", color=0xffffff)
    edit_this = await client.send_message(author, embed=embed)
    credentials = solebox.solebox_gen(catchall)
    username, password = credentials.split(':')

    embed = discord.Embed(title="ACCOUNT GENERATED!", color=0xffffff)
    embed.add_field(name="EMAIL:", value=username)
    embed.add_field(name="PASSWORD:", value=password, inline=False)
    embed.set_footer(icon_url=icon_img, text=footer_text)
    await client.edit_message(edit_this, embed=embed)  
    



''' Complement to connectedservers command. Removes FOMO Helper from any unauthorized servers
    using the bot. 
    
    @param ctx: Discord information
    @param *args: Developer email and unauthorized server id to remove bot service from  '''
@client.command(name='unauthorizeserver',
                description='Removes bot from any unauthorized servers.',
                pass_context=True)
async def remove_from_server(ctx, *args):
    author = ctx.message.author
    
    if len(args) < 2:
        await client.send_message(author, "Command is missing an argument")
    elif len(args) > 2: 
        await client.send_message(author, "Command has extra argument(s).")
    else:
        email = args[0]
        id = args[1]
        
        if email == "macewandu@hotmail.com":
            server_to_leave = client.get_server(str(id))
            await client.leave_server(server_to_leave)
            await client.send_message(author, "Successfully left the server")
        else:
            await client.send_message(author, "Invalid argument passed")



@client.command(name='donutuk', 
                pass_context=True)
async def donut_message(ctx, gmail):
    author = ctx.message.author
    server = client.get_server(server_id)
    user = server.get_member(author.id)
    await client.send_message(author, ":hourglass: Please wait, we are working on your free doughnut...")
    
    kk_acc = KRISPYKREME.krispykreme_uk(gmail) 
    kk_acc = str(kk_acc) 
    acc_email = kk_acc.replace("('", "")
    acc_email = kk_acc.replace("')", "")
    acc_pw = 'MyPassword123'
    
    embed = Embed(title='YOUR KRISPY KREME ACCOUNT', 
                  description="LOGIN TO THIS ACCOUNT VIA THE KRISPY KREME APP", 
                  color=0xffffff)
    embed.set_thumbnail(url="http://pngimg.com/uploads/donut/donut_PNG98.png")
    embed.add_field(name="EMAIL:", value=acc_email, inline=True)
    embed.add_field(name="PASSWORD:", value=acc_pw, inline=True)
    embed.add_field(name="APP DOWNLOAD LINK:", 
                    value=" [APP STORE](https://itunes.apple.com/us/app/krispy-kreme/id482752836?mt=8)\n[GOOGLE PLAY](https://play.google.com/store/apps/details?id=com.krispykreme.HotLights&hl=en)", 
                    inline=False)
    embed.add_field(name="HOW TO REDEEM:",
                    value="Download the **Krispy Kreme App** on your device. Login with the above credentials and show the cashier the barcode found in the app and she will hand you a free doughnut!",
                    inline=False)
    await client.send_message(author, embed=embed)
    
    
# ''' Command used by admins to grant user's permission to resubscribe to the Discord group
#     if their subscription was previously cancelled (NOTE - cancelled subscription is different,
#     from a disabled subscription.) 
#     
#     @param ctx: Discord information 
#     @param *args: Email and subscription type passed by user '''
# @client.command(name='resub',
#                 description='Gives a member back his subscription if they had their subscription canceled',
#                 pass_context=True)
# async def resub(ctx, *args):
#     # Message author
#     author = ctx.message.author 
#     # FOMO Discord server reference
#     discord_server = client.get_server(server_id)
#     # Member reference for user 
#     member = discord_server.get_member(author.id)
#     
#     # Make sure message is a private message to FOMO Helper
#     if isinstance(ctx.message.channel, discord.PrivateChannel):
#         # Make sure an admin is using the command
#         if "Admin" or "Dev" in [role.name for role in member.roles]:
#             # Check for correct number of parameters passed
#             if len(args) < 1:
#                 await client.send_message(author, "Command is missing an argument. Make sure you provide the purchase email")
#             elif len(args) > 1:
#                 await client.send_message(author, "Command has extra argument(s). Make sure you provide the purchase email only.")
#             else:
#                 # Email passed as a parameter
#                 email = args[0]
#                 
#                 # Find user information on database if it exists
#                 data = subscriptions.find_one({"email": f"{email}"})
#                 if data == None:
#                     await client.send_message(author, "Could not find the provided email. Please check that it is correct and try again.")
#                 else:
#                     subscriptions.update_one({
#                         "email": email
#                     }, {
#                         "$set": {
#                             "status": "pending",
#                             "error_count": 0
#                         }
#                     }, upsert=False)
# 
#                     await client.send_message(author, "User has been given permission to reactivate their account. Get in touch with them and let them know!")
#         else:
#             await client.send_message(author, "This command is for admins only")
        

''' Cancels a user's subscription and updates the database 
    @param ctx: Discord information
    @param email: Email associated to acount to cancel subscription for'''
@client.command(name='cancel',
                description='Cancel a user\'s subscription',
                pass_context=True)
async def cancel(ctx, email):
    # FOMO Discord server reference
    discord_server = client.get_server(server_id)
    # Message author
    author = ctx.message.author 
    # Discord member reference based on user id
    member = discord_server.get_member(author.id)
    
    # If message is a private message 
    if isinstance(ctx.message.channel, discord.PrivateChannel):
        # Check if member is an admin
        data = subscriptions.find_one({"email": f"{email}"})
        if data == None:
                await client.send_message(author, "Could not find the provided email. Please check that it is correct and try again.")
        else:
            subscriptions.update_one({
                "email": email
            }, {
                "$set": {
                    "status": "disabled"
                }
            })
                
            await client.send_message(author, "User subscription successfully canceled") 



''' Command responsible for authenticating users premium subscription on Discord and 
    assigning correct role '''
@client.command(name='activate',
                description='Activate your subscription to be assigned the appropriate roles',
                pass_context=True)
async def activate(ctx, email):
    # Discord message author  
    author = ctx.message.author
    # FOMO Discord server reference 
    discord_server = client.get_server(server_id)
      
    # Check if message is a private message
    if isinstance(ctx.message.channel, discord.PrivateChannel):
        try:
            await STRIPE.check_membership(ctx, email.lower())
        except requests.Timeout as error:
            print("There was a timeout error")
            print(str(error))
        except requests.ConnectionError as error:
            print("A connection error has occurred. The details are below.\n")
            print(str(error))
        except requests.RequestException as error:
            print("An error occurred making the internet request.")
            print(str(error))
        
        
        
''' Discord command to calculate the fees that are applied to sale products on multiple websites.
    @param ctx: Discord information
    @param sale_price: Price for which to make the calculations'''
@client.command(name='fee',
                description='Calculates the seller fees applied by different websites',
                pass_context=True)
async def fee_calculator(ctx, sale_price):
    # List of websites 
    sites = []
    # Discord channel on which command was called
    channel = ctx.message.channel
    
    # Simple check for a monetary value
    if re.match('^\d+(\.\d*)*$', sale_price) == None:
        await client.send_message(channel, 'The value given is not a proper monetary value')
    else:
        price = Decimal(sale_price)
        price = round(price, 2)
        
        # Tuple format
        #    - site title
        #    - fee percentage
        #    - fixed fee (0 if none)
        ebay = ('eBay', 0.129, 0.00)
        grailed = ('Grailed', 0.089, 0.30)
        paypal = ('PayPal', 0.029, 0.30)
        goat = ('Goat', 0.095, 5.00)
        stockx = ('StockX', 0.120, 0.00)
        shopify = ('Basic Shopify', 0.029, 0.30)
        sites.append(ebay)
        sites.append(grailed)
        sites.append(paypal)
        sites.append(goat)
        sites.append(stockx)
        sites.append(shopify)
        
        websites = ''
        fees = ''
        profits = ''
        # For each site, format information for display on Discord
        for i in sites:
            websites += i[0] + '\n'
            fee = round(price * Decimal(i[1]), 2)
            fees += '$' + str(round(fee + Decimal(i[2]), 2)) + '\n'
            after_fee = round(price - fee - Decimal(i[2]), 2)
            profits += '$' + str(after_fee) + '\n'
            
        embed = Embed(color = 0x008f00)
        embed.add_field(name='Website', value=websites, inline=True)
        embed.add_field(name='Fee', value=fees, inline=True)
        embed.add_field(name='Profit After Fees', value=profits, inline=True)
        
        await client.send_message(channel, embed=embed)


''' Discord command to check if a specific website is a Shopify website
    
    @param ctx: Discord information
    @param url: URL to be checked '''  
@client.command(name='isshopify',
                description='This command uses a given URL in order to determine whether a website is a shopify site or not.',
                pass_context=True)
async def shopify_check(ctx, url):
    shopify = Shopify()
    await shopify.check_if_shopify(ctx, url)
    

''' Discord command to Jig a specific gmail address.
    @param ctx: Discord information
    @param email: Email to be jigged '''
@client.command(name='gmail',
                description='This command manipulates any gmail address passed to it as a parameter.',
                aliases=['mail', 'email'],
                pass_context=True)
async def gmail_jig(ctx, email):
    gmail = GmailJig()
    await gmail.run(str(email), ctx)
    

''' Discord command to Jig a specific residential address.
    @param ctx: Discord information
    @param adr: Residential address to be jigged ''' 
@client.command(name='address',
                description='This command manipulates any residential address passed to it as a parameter.',
                aliases=['addr', 'adr'],
                pass_context=True)
async def address_jig(ctx):
    address = AddressJig()
    adr = str(ctx.message.content) 
    adr = adr.replace("!address ", "")
    await address.generate_address_two(str(adr), ctx)


''' Discord command to generate Add to Cart links for Shopify Websites.
    @param ctx: Discord information
    @param url: URL for item to be purchased '''  
@client.command(name='atc',
                description='Add To Cart command for any Shopify website. Generates a link leading the user ' +
                'straight to the payment page. Takes in the item\'s URL as a parameter',
                pass_context=True)
async def add_to_cart(ctx, url):
    shopify = Shopify()
    await client.send_message(ctx.message.channel, ':hourglass: Retrieving sizes. Please wait...')
    await shopify.run(str(url), ctx)

''' Discord command for eBay views: limited to 200 views one command 
    @param ctx: Discord information
    @param rul: Url for item to be viewed '''
@client.command(name='ebayviews', 
                description='Automatic eBay viewer for any listing. Views the given URL up to 200 times',
                pass_context=True)
async def ebay_view(ctx, url):
    if ebay_used_urls[0] != datetime.date.today():
        ebay_used_urls.clear()
        ebay_used_urls.append(datetime.date.today())
    
    if url in ebay_used_urls:
        await client.send_message(ctx.message.author, "You have already viewed this item today.")
    else:
        if not 'ebay.' in url:
            await client.send_message(ctx.message.author, "First parameter is not an ebay url.")
        else:
            try:
                ebay = eBay()
                _thread.start_new_thread(ebay.ebayview, (ctx, str(url),))
                embed = discord.Embed(title="", color=0xF5AF02)
                embed.add_field(name=":eyes:  Viewer started. Your views should be applied shortly. :hourglass:", value="~~~~~ Powered by FOMO ~~~~~", inline=True)      
                ebay_used_urls.append(url)
                await client.send_message(ctx.message.author, embed=embed)
            except Exception as e:
                await client.send_message(ctx.message.author, f"An error occurred trying to view the item. If it persists, please contact an admin")


''' Discord command for eBay watches: limited to 20 views one command 
    @param ctx: Discord information
    @param url: URL for eBay listing
    @param watches: Number of watches '''
@client.command(name='ebaywatch', 
                description='Automatic eBay watcher for any listing. Watches the given URL 20 times',
                pass_context=True)
async def ebay_watch(ctx, url, watches):
    try: 
        if int(watches) < 21:
            ebay = eBay()
            _thread.start_new_thread(ebay.ebaywatch, (str(url), int(watches),))
            await client.send_message(ctx.message.channel, 'Link watched %s times. Please wait for the watches to be applied' % (watches))
        else:
            await client.send_message(ctx.message.channel, 'The maximum number of watches allowed in one request is 20. Please try again')
    except:
        await client.send_message(ctx.message.channel, 'Error. Please contact your server admin.')



# ------------------------------------------------------------- #
#                                                               #
# Individual classes to represent the different functionalities #
#             that the Discord bot will have                    #
#                                                               #   
# ------------------------------------------------------------- #
class KrispyKreme(object):
    
    def __init__(self, ):
        self.headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'}
        self.uk_signup = 'https://friends.krispykremerewards.co.uk/Friends/SignUp/SignUp.aspx?ChannelSource=Website&InputSource=Direct'
        self.password = 'MyPassword123'
        
    def plus_jig(self, gmail):
        num1 = int(random.randrange(0,10))
        num2 = int(random.randrange(0,10))
        num3 = int(random.randrange(0,10))
        num4 = int(random.randrange(0,10))
        num5 = int(random.randrange(0,10))
        num6 = int(random.randrange(0,10))
        plusjig = str(num1) + str(num2) + str(num3) + str(num4) + str(num5) + str(num6)
        return gmail + '+' + plusjig + '@gmail.com'
    
    def krispykreme_uk(self, email):
        gmail = self.plus_jig(email) 
        session = requests.session()
        tokens = requests.get(self.uk_signup, headers=self.headers) 
        soup = BeautifulSoup(tokens.text, 'html.parser')
        
        viewstate = str(soup.find("input", {"type":"hidden", "name":"__VIEWSTATE"}, tokens.text))
        viewstate = viewstate.replace('<input id="__VIEWSTATE" name="__VIEWSTATE" type="hidden" value="','')
        viewstate = viewstate.replace('"/>','')
        
        viewstategenerator = str(soup.find("input",{"type":"hidden","name":"__VIEWSTATEGENERATOR"}, tokens.text))
        viewstategenerator = viewstategenerator.replace('<input id="__VIEWSTATEGENERATOR" name="__VIEWSTATEGENERATOR" type="hidden" value="','')
        viewstategenerator = viewstategenerator.replace('"/>','')
        
        eventvalidation = str(soup.find("input",{"type":"hidden","name":"__EVENTVALIDATION"}, tokens.text))
        eventvalidation = eventvalidation.replace('<input id="__EVENTVALIDATION" name="__EVENTVALIDATION" type="hidden" value="','')
        eventvalidation = eventvalidation.replace('"/>','')
    
        formdata1 = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "ctl00$ContentPlaceHolder1$wucSignInStep1$txtFName": names.get_first_name(),
            "ctl00$ContentPlaceHolder1$wucSignInStep1$txtLName": names.get_last_name(),
            "ctl00$ContentPlaceHolder1$wucSignInStep1$txtCorreo": gmail,
            "ctl00$ContentPlaceHolder1$wucSignInStep1$ChkConsentKK": "on",
            "ctl00$ContentPlaceHolder1$wucSignInStep1$cboDondeCompra": "1",
            "ctl00$ContentPlaceHolder1$wucSignInStep1$ChkAcceptEmail": "on",
            "ctl00$ContentPlaceHolder1$btnPaso1Next": "NEXT",
            "ctl00$ContentPlaceHolder1$HiddenField1": "False",
            "ctl00$ContentPlaceHolder1$hidSocioID": "",
            "ctl00$ContentPlaceHolder1$hidUsuarioIDFb": "",
            "ctl00$ContentPlaceHolder1$txtPreferencias": ""
        }
    
        submit1 = session.post(self.uk_signup, headers=self.headers, data=formdata1)
        soup = BeautifulSoup(submit1.text, 'html.parser')
        
        viewstate = str(soup.find("input",{"type":"hidden","name":"__VIEWSTATE"}, tokens.text))
        viewstate = viewstate.replace('<input id="__VIEWSTATE" name="__VIEWSTATE" type="hidden" value="','')
        viewstate = viewstate.replace('"/>','')
    
        viewstategenerator = str(soup.find("input",{"type":"hidden","name":"__VIEWSTATEGENERATOR"}, tokens.text))
        viewstategenerator = viewstategenerator.replace('<input id="__VIEWSTATEGENERATOR" name="__VIEWSTATEGENERATOR" type="hidden" value="','')
        viewstategenerator = viewstategenerator.replace('"/>','')
        
        eventvalidation = str(soup.find("input",{"type":"hidden","name":"__EVENTVALIDATION"}, tokens.text))
        eventvalidation = eventvalidation.replace('<input id="__EVENTVALIDATION" name="__EVENTVALIDATION" type="hidden" value="','')
        eventvalidation = eventvalidation.replace('"/>','')
    
        socioid = str(soup.find("input",{"type":"hidden","name":"ctl00$ContentPlaceHolder1$hidSocioID"}, submit1.text))
        socioid = socioid.replace('<input id="ContentPlaceHolder1_hidSocioID" name="ctl00$ContentPlaceHolder1$hidSocioID" type="hidden" value="','')
        socioid = socioid.replace('"/>','')
    
        formdata2 = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "ctl00$ContentPlaceHolder1$wucSignInStep2$fechaNacimiento$ddlDia": "7",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$fechaNacimiento$ddlMes": "7",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$fechaNacimiento$ddlAnio": "1998",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$wucCP$txtCP": "G41 4PY",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$wucCP$txtContry": "City of Glasgow",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$wucCP$txtCityTwon": "Glasgow",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$wucCP$hidPaginaPadre": "SignUp.aspx",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$ctl00$cboListaDatos": "2",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$wucGpoDondeCompra$ChkPreferencia_10": "on",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$ctl01$cboListaDatos": "-""1",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$txtNumeroTjta": "",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$txtRegCode": "",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$txtPass": self.password,
            "ctl00$ContentPlaceHolder1$wucSignInStep2$txtConfirmPass": self.password,
            "ctl00$ContentPlaceHolder1$wucSignInStep2$chkTC": "on",
            "ctl00$ContentPlaceHolder1$btnConfirm": "CONFIRM",
            "ctl00$ContentPlaceHolder1$HiddenField1": "False",
            "ctl00$ContentPlaceHolder1$hidSocioID": socioid,
            "ctl00$ContentPlaceHolder1$hidUsuarioIDFb": "",
            "ctl00$ContentPlaceHolder1$txtPreferencias": ",10_ChkPreferencia,null"
        }
    
        submit2 = session.post(self.uk_signup, headers=self.headers, data=formdata2)
        if submit2.status_code == 200:
            session.close()
            return gmail
        if submit2.status_code != 200:
            session.close()
            return("Request Failed")


class FOMO_SMS(object):
    
    def __init__(self):
        self.from_ = twilio_from
        self.account_sid = twilio_sid
        self.auth_token = twilio_auth_token
        self.sms_client = Client(self.account_sid, self.auth_token)
        self.sms_db_client = pymongo.MongoClient(mongo_sms_url)
        self.sms_db = self.sms_db_client.get_database()
        self.posts = self.sms_db.posts

    async def add_user(self, message, number):
        server = client.get_server(server_id)
        author = message.author
        db_check = self.posts.find({'discord_id':author.id}).count()
        member = server.get_member(author.id) 
            
        if member_role or 'Moderator' or 'Admin' in [role.name for role in member.roles]:
            # If user isn't in the database, check if the entered number was entered with a + sign before it
            if db_check == 0:
                # Add number to the database if it is correct
                if '+' in number:
                    new_user = dict()
                    new_user['discord_id'] = author.id 
                    new_user['number_+'] = number 
                    new_user['number'] = number.replace('+','')
                    new_post = self.posts.insert_one(new_user).inserted_id
                    embed = Embed(title="SUCCESS!", description="You have been added to the database.", color=0xffffff)
                    embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                    embed.add_field(name="Number on File:", value=new_user['number_+'])
                    embed.set_footer(icon_url=icon_img, text=footer_text)
                    await client.send_message(author, embed=embed)
                else:
                    embed = Embed(title="FAILED", description="Make sure you format your number correctly", color=0xffffff)
                    embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                    embed.add_field(name="FOR EXAMPLE:", value="sms!add +13058554140")
                    embed.set_footer(icon_url=icon_img, text=footer_text)
                    await client.send_message(author, embed=embed)
            elif db_check > 0:
                user = self.posts.find_one({'discord_id':author.id})
                embed = Embed(title="FOUND!", description="You are already in the database.", color=0xffffff)
                embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                embed.add_field(name="TO UPDATE YOUR NUMBER, SAY:", value="sms!update")
                embed.set_footer(icon_url=icon_img, text=footer_text)
                await client.send_message(author, embed=embed)
        else:
            embed = Embed(title="NOT A MEMBER", description="You must be a paying member to access this feature.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(author, embed=embed)
                           
    async def check_user(self, message):
        server = client.get_server(server_id)
        author = message.author
        member = server.get_member(author.id)
        db_check = self.posts.find({'discord_id':author.id}).count()
    
        if member_role or 'Moderator' or 'Admin' in [role.name for role in member.roles]:
            if db_check > 0:
                user = self.posts.find_one({'discord_id': author.id})
                embed = Embed(title="FOUND!", description="You were found in the database.", color=0xffffff)
                embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                embed.add_field(name="TO UPDATE YOUR NUMBER ON FILE, SAY:", value="sms!update")
                embed.set_footer(icon_url=icon_img, text=footer_text)
                await client.send_message(author, embed=embed)
            elif db_check == 0:
                embed = Embed(title="NOT FOUND!", description="You were not found in the database.", color=0xffffff)
                embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                embed.add_field(name="TO ADD YOUR NUMBER, SAY:", value="sms!add followed by your number with the country & area code.")
                embed.set_footer(icon_url=icon_img, text=footer_text)
                await client.send_message(author, embed=embed)
        else:
            embed = Embed(title="NOT A MEMBER", description="You must be a paying member to access this feature.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(author, embed=embed)
            
    async def update_user(self, message, number):
        server = client.get_server(server_id)
        author = message.author
        member = server.get_member(author.id)
    
        if member_role or 'Moderator' or 'Admin' in [role.name for role in member.roles]:
            if '+' in number:
                number_plus = number
                number_noplus = number.replace('+','')
                db_check = self.posts.find({'discord_id':author.id}).count()
    
                if db_check > 0:
                    self.posts.update_one({
                        'discord_id': author.id
                        }, {
                            '$set': {
                                'number_+':number_plus,
                                'number':number_noplus
                            }
                    })
                    user = self.posts.find_one({'discord_id': author.id})
                    embed = Embed(title="SUCCESS!", description="Your number on file was updated.", color=0xffffff)
                    embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                    embed.add_field(name="NUMBER ON FILE:", value=user['number_+'])
                    embed.set_footer(icon_url=icon_img, text=footer_text)
                    await client.send_message(author, embed=embed)
                elif db_check == 0:
                    embed = Embed(title="NOT FOUND!", description="You were not found in the database.", color=0xffffff)
                    embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                    embed.add_field(name="LEARN MORE BY SAYING:", value="sms!help")
                    embed.set_footer(icon_url=icon_img, text=footer_text)
                    await client.send_message(author, embed=embed)
            else:
                embed = Embed(title="FAILED", description="Make sure you format your number correctly", color=0xffffff)
                embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                embed.add_field(name="FOR EXAMPLE:", value="sms!add +13058554140")
                embed.set_footer(icon_url=icon_img, text=footer_text)
                await client.send_message(author, embed=embed)
        else:
            embed = Embed(title="NOT A MEMBER", description="You must be a paying member to access this feature.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(author, embed=embed)
        
    
    async def remove_user(self, message):
        server = client.get_server(server_id)
        author = message.author
        member = server.get_member(author.id)
    
        db_check = self.posts.find({'discord_id':author.id}).count()
    
        if db_check == 0:
            embed = Embed(title="NOT FOUND!", description="You were not found in the database.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.add_field(name="LEARN MORE BY SAYING:", value="sms!help")
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(author, embed=embed)
        elif db_check > 0:
            user = self.posts.find_one({'discord_id':author.id})
            self.posts.delete_one(user)
            embed = Embed(title="REMOVED", description="You will no longer receive SMS alerts.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.add_field(name="LEARN MORE BY SAYING:", value="sms!help")
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(author, embed=embed)
            
    async def send_sms(self, message):
        server = client.get_server(server_id)
        author = message.author
        member = server.get_member(author.id)
    
        if member.server_permissions.administrator:
            users = self.posts.find({})
            msg = str(message.content)
            msg = msg.replace('sms!send ', '')
            for user in users:
                number = user['number_+']
                sms_message = self.sms_client.messages.create(
                    to=number,
                    from_=twilio_number,
                    body=msg)
                
                if "queued" or "sent" or "delivered" in sms_message.status:
                    print("SMS SENT: " + sms_message.status)
                else:
                    print("ERROR SENDING SMS: " + sms_message.status)
            await client.send_message(author, "Message Sent!")
        else:
            embed = Embed(title="NOT A STAFF MEMBER", description="You must be a moderator/admin to use this command.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(author, embed=embed)
            
    async def sms_help(self, message):
        author = message.author
        embed = Embed(title="SMS HELP CENTER", color=0xffffff)
        embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
        embed.add_field(name="sms!add", value="Adds your number to the database.")
        embed.add_field(name="sms!check", value="Checks if your number is in the database.")
        embed.add_field(name="sms!update", value="Updates your number in the database.")
        embed.add_field(name="sms!stop", value="Removes your number from the database.")
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(author, embed=embed)


class SuccessPoster(object): 
    
    def __init__(self):
        self.consumer_key = twitter_consumer_key
        self.consumer_secret = twitter_consumer_secret
        self.access_token = twitter_access_token
        self.access_token_secret = twitter_access_secret
        self.twitter_api = twitter.Api(consumer_key=self.consumer_key,
                                       consumer_secret=self.consumer_secret,
                                       access_token_key=self.access_token,
                                       access_token_secret=self.access_token_secret)
        
    def success_poster(self, author, image_url):
        status = self.twitter_api.PostUpdate(f'Success by {author}', media=image_url)
        

class Stripe(object):
    async def process_payment(self, message):
        messiah = get(client.get_all_members(), id=discord_owner_id)
        msg_data = message.content.split()
        token = msg_data[0]
        email = msg_data[1].lower()
        web_source = msg_data[2]
        
        # Create a customer
        if web_source == "FOMO":
            customer = stripe.Customer.create(
                api_key=FOMO_STRIPE_KEY,
                source=token,
                email=email
            )
        else:
            customer = stripe.Customer.create(
                api_key=MOREHYPED_STRIPE_KEY,
                source=token,
                email=email
            )
         
        try:
            # Charge the Customer instead of the card
            if web_source == "FOMO":
                stripe.Charge.create(
                    api_key=FOMO_STRIPE_KEY,
                    amount=2000,
                    currency='usd',
                    customer=customer.id
                )
            else:
                stripe.Charge.create(
                    api_key=MOREHYPED_STRIPE_KEY,
                    amount=2000,
                    currency='usd',
                    customer=customer.id
                )
            
            now = datetime.datetime.now().date()
            # Search for email in database
            data = subscriptions.find_one({"email": f"{email}"})
            # If the email doesn't exist in the database
            if data == None:
                # Insert new user data in the database
                subscriptions.insert({
                    "email": email,
                    "customer_id": customer.id,
                    "status": "pending",
                    "error_count": 0,
                    "sub_date": str(now),
                    "pay_date": str(now),
                    "web_source": web_source
                })
            else:
                # Update an existing subscription with new information
                subscriptions.update_one({
                    "email": email
                }, {
                    "$set": {
                        "customer_id": customer.id,
                        "status": "active",
                        "error_count": 0,
                        "pay_date": str(now)
                    }
                }, upsert=False)
        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            
            await client.send_message(messiah, f"There was an error processing the payment for email {email}")
            await client.send_message(messiah, f"Status is: {e.http_status}")
            await client.send_message(messiah, f"Type is: {err.get('type')}")
            await client.send_message(messiah, f"Code is: {err.get('code')}")
        except stripe.error.RateLimitError as e:
            await client.send_message(messiah, f"Rate limit error: {e}")
        except stripe.error.AuthenticationError as e:
            await client.send_message(messiah, f"Authentication error: {e}")
        except stripe.error.APIConnectionError as e:
            await client.send_message(messiah, f"Stripe error: {e}")
        except stripe.error.StripeError as e:
            await client.send_message(messiah, f"Stripe error: {e}")
        except Exception as e:
            await client.send_message(messiah, f"Exception occurred during process_payment: {e}")
    
    
    async def check_membership(self, ctx, email):
        # Search for email in database
        data = subscriptions.find_one({"email": f"{email}"})
        # If the email doesn't exist in the database
        if data == None:
            # No subscription was purchased under the given email
            await client.send_message(ctx.message.author, 'No subscription data was found under that email. If you believe this to be a mistake, please contact an admin.')
        else:
            if data['status'] == "active":
                await client.send_message(ctx.message.author, "This subscription has already been activated. If you believe this to be a mistake, please contact an admin.")
            elif data['status'] == "disabled":
                await client.send_message(ctx.message.author, "This subscription was previously disabled. To reactivate it, please contact the developer Messiah.")
            else:
                subscriptions.update_one({
                    "email": email
                }, {
                    "$set": {
                        "discord_id": ctx.message.author.id,
                        "status": "active"
                    }
                }, upsert=False)
                
                await sub_and_assign_roles(email, ctx.message.author)
            
    async def recurring_charges(self):
        discord_server = client.get_server(server_id)
        messiah = get(client.get_all_members(), id=discord_owner_id)
        now = datetime.datetime.now().date()
        cursor = subscriptions.find({})
        
        await client.send_message(messiah, f"{now} - checking for recurring payments now!")
            
        for index,document in enumerate(cursor):
            email = document['email']
            error_count = document['error_count']
            error_count = int(error_count)
            error_count += 1
            old_date = document['pay_date']
            web_source = document['web_source']
            old_date = datetime.datetime.strptime(old_date, "%Y-%m-%d").date()
            
            # TODO - fix removing old members from server and database  
            delta = now - old_date
            if delta.days > 30 and (document['status'] == 'disabled'):
                discord_id = document["discord_id"]
                user = discord_server.get_member(discord_id)
                print(f'Inactive user: {user}')
                
                if user != None:
                    if member_role in [role.name for role in user.roles]:
                        role = get(discord_server.roles, name=member_role)
                        await client.remove_roles(user, role)
            if delta.days > 30 and (document['status'] == 'active'):
                discord_id = document['discord_id']
                user = get(client.get_all_members(), id=discord_id)
                print(f'Active user: {user}')    
                
                customer_id = document['customer_id']
                try: 
                    if web_source == "FOMO":      
                        charge = stripe.Charge.create(
                            api_key=FOMO_STRIPE_KEY,
                            amount=2000,
                            currency='usd',
                            customer=customer_id
                        )
                    else:
                        charge = stripe.Charge.create(
                            api_key=MOREHYPED_STRIPE_KEY,
                            amount=2000,
                            currency='usd',
                            customer=customer_id
                        )
                          
                    subscriptions.update_one({
                        "email": email 
                    }, {
                        "$set": {
                            "pay_date": str(now),
                            "error_count": 0
                        }
                    })
                except stripe.error.CardError as e:
                    body = e.json_body
                    err = body.get('error', {})
                        
                    subscriptions.update_one({
                        "email": email 
                    }, {
                        "$set": {
                            "error_count": error_count
                        }
                    })
                        
                    await client.send_message(messiah, f"There was an error processing the payment for email {email}")
                    await client.send_message(messiah, f"Status is: {e.http_status}")
                    await client.send_message(messiah, f"Type is: {err.get('type')}")
                    await client.send_message(messiah, f"Code is: {err.get('code')}")
                        
                    if error_count == 1:
                        await client.send_message(user, "Our first attempt to charge you for your recurring subscription has failed." 
                                                    + "We will try two more times before cancelling your subscription. Please contact an admin as soon as possible.")
                    elif error_count == 2:
                        await client.send_message(user, "Our second attempt to charge you for your recurring subscription has failed." 
                                                    + "We will try one more time before cancelling your subscription. Please contact an admin as soon as possible.")
                    else:
                        await client.send_message(messiah, f"Please cancel the subscription for the user with email: {email}")
                        await client.send_message(user, "Our final attempt to charge you for your recurring subscription has failed." 
                                                    + "We will now be cancelling your subscription.")
                             
                        discord_user = discord_server.get_member(discord_id)
                        print(f'Discord user: {discord_user}')
                        role = get(discord_server.roles, name=member_role)
                        await client.remove_roles(discord_user, role)
                except stripe.error.RateLimitError as e:
                    await client.send_message(messiah, f"Rate limit error: {e}")
                    break
                except stripe.error.AuthenticationError as e:
                    await client.send_message(messiah, f"Authentication error: {e}")
                    break
                except stripe.error.APIConnectionError as e:
                    await client.send_message(messiah, f"Stripe error: {e}")
                    break
                except stripe.error.StripeError as e:
                    await client.send_message(messiah, f"Stripe error: {e}")
                    break
                except Exception as e:
                    await client.send_message(messiah, f"Exception occurred during recurring_charge: {e}")
                    break
    

class GmailJig(object):
    emails = ''
    
    ''' Kickstarts the Gmail Jigging Process.
        
        @param email: Email to be jigged
        @param ctx: Discord information '''
    async def run(self, email, ctx):
        if email.replace(' ', '') == "":
            await client.send_message(ctx.message.author,"Empty input given. Please try again")
        else:
            await self.email_check(email, ctx)
            
    ''' Checks for a correct email (google email address only).
    
        @param email: Email to be checked
        @param ctx: Discord information '''
    async def email_check(self, email, ctx):
        # Make sure gmail address was passed
        verified = re.search('(@gmail.+)', email)
        if verified == None:
            await client.send_message(ctx.message.author,"Invalid email address. Please use a @gmail address")
        else:
            # Store email provider/second part of email address -> @gmail...
            email_suffix = verified.group()
            # Store first part of email
            prefix = email.replace(email_suffix, '')
            # Make sure first part of email is of a reasonable length for jigging
            if len(prefix) > 2:
                await self.jig_email(prefix, email_suffix, ctx)
            else:
                await client.send_message(ctx.message.author,"Your email is not long enough. Please try another email")
    
    ''' Jigs a given gmail address.
    
        @param email_prefix: Everything before the @ sign
        @param email_suffix: Everything after the @ sign, @ sign included
        @param ctx: Discord information '''   
    async def jig_email(self, email_prefix, email_suffix, ctx):
        # Keeps track of indices where period was applied
        used_indeces = []
        # Keeps track of indices neighboring an existing period + periods location
        email_dot_indeces = []
        # length of email prefix
        last_index = len(email_prefix) - 1
        limit = 6    
        stop = 0
        
        # Go through the prefix
        for index, character in enumerate(email_prefix):
            # If there is a dot anywhere in the prefix already
            if character == '.':
                # Keep track of its location and adjacent indexes
                email_dot_indeces.append(index)
                if index-1 not in email_dot_indeces:
                    email_dot_indeces.append(index-1)
                
                if (index + 1) < last_index and (index + 1) not in email_dot_indeces:
                    email_dot_indeces.append(index+1)
        # Limit the number of items to be displayed to the user           
        if limit < last_index - len(email_dot_indeces):
            stop = limit
        else:
            stop = (last_index - len(email_dot_indeces)) + 1
        # Randomly get an integer to serve as index to insert a dot    
        for i in range(1,stop):
            r = random.randint(1, last_index)
            # Make sure index is not already used
            if r not in used_indeces and r not in email_dot_indeces:
                used_indeces.append(r)
            else:
                while r in used_indeces or r in email_dot_indeces:
                    r = random.randint(1, last_index)
                    
                used_indeces.append(r)
            
        count = 0
        # Go through all the indeces to be used
        for i in used_indeces:
            # Add only 1 dot to email
            email_var = email_prefix[:i] + '.' + email_prefix[i:]
            self.emails += email_var + email_suffix + '\n'

            # Add 2 dots for variety
            if i == used_indeces[-1]:
                smaller = i if i < used_indeces[0] else used_indeces[0]
                larger = i if i > used_indeces[0] else used_indeces[0]
                
                email_var = email_prefix[:smaller] + '.' + email_prefix[smaller:larger] + '.' + email_prefix[larger:]
            else:
                smaller = i if i < used_indeces[count+1] else used_indeces[count+1]
                larger = i if i > used_indeces[count+1] else used_indeces[count+1]
                
                email_var = email_prefix[:smaller] + '.' + email_prefix[smaller:larger] + '.' + email_prefix[larger:]
            
            self.emails += email_var + email_suffix + '\n'
            count += 1
            
        embed = Embed(title="", color=0xff2600)
        embed.add_field(name='Jigged Gmail', value=self.emails, inline=True)

        await client.send_message(ctx.message.author, embed=embed)


class AddressJig(object):
    addresses = ''
    
    ''' Generates the 4 character code to be added to beginning of address. 
    
        @return: 4 Character code to be added to beginning of address '''
    def generate_code(self):
        code = ''
        for i in range(0,4):
            code += random.choice(string.ascii_uppercase)
            
        return code
        
    ''' Generates the 2nd part of the address
    
        @param address: The address passed by the user
        @param ctx: Discord information '''  
    async def generate_address_two(self, address, ctx):
        if address.replace(' ', '') == '':
            await client.send_message(ctx.message.author,"Please enter a valid address.")
        else:
            address_options = ['Apt', 'Apartment', 'Building', 'Bldg', 'Suite', 'Room', 'Condo', 'Unit']
            
            for i in range(1,16):
                index = random.randint(0, len(address_options)-1)
                address_2 = address_options[index]
                
                code = self.generate_code()
                num = 0
                if address_2 == 'Unit':
                    num = random.randint(5, 100)
                else:
                    num = random.randint(15, 500)
                
                self.addresses += code + ' ' + address + ' ' + address_2 + ' ' + str(num) + '\n'
            
            embed = Embed(title="", color=0xff9300)
            embed.add_field(name='Jigged Addresses', value=self.addresses, inline=True)
            
            await client.send_message(ctx.message.author, embed=embed)
            
            
class Shopify(object):
    # Shopify ATC related variables
    sizes = ''
    atc_links = ''
    
    ''' Checks whether a given url is a Shopify website or not.
    
        @param ctx: Discord information 
        @param url: The URL to check for Shopify status ''' 
    async def check_if_shopify(self, ctx, url):
        channel = ctx.message.channel
        
        # Ensure url starts with https:// in case url only contains www....
        url_formatting = re.match('https://', url)
        if url_formatting == None:
            url = 'https://' + url
        try:
            raw_HTML = requests.get(url, headers=headers, timeout=10)
            if raw_HTML.status_code != 200:
                await client.send_message(channel, "An error has occurred completing your request.")
            else:
                # Search for a specific script that exists in all shopify websites
                page = bs4.BeautifulSoup(raw_HTML.text, 'lxml')
                script = page.find_all('script')
                for i in script:
                    # If script is found, we know it's a Shopify website
                    if 'shopify' in str(i).lower():
                        await client.send_message(channel, "It IS a Shopify website!")
                        return
                await client.send_message(channel, 'It IS NOT a Shopify website!')
        except requests.Timeout as error:
            await client.send_message(channel, "There was a timeout error")
        except requests.ConnectionError as error:
            await client.send_message(channel, "A connection error has occurred.")
        except requests.RequestException as error:
            await client.send_message(channel, "An error occurred making the internet request.")
    
    
    ''' Retrieves sizes for item in stock.
        
        @param url: The url passed by the user pointing to the item he/she wants
        @param ctx: Discord information  ''' 
    async def get_sizes(self, url, ctx):
        # Ensure url starts with https:// in case url only contains www....
        url_formatting = re.match('https://', url)
        if url_formatting == None:
            url = 'https://' + url
        try:
            raw_HTML = requests.get(url, headers=headers, timeout=10)
            if raw_HTML.status_code != 200:
                await client.send_message(ctx.message.channel,"An error has occurred completing your request")
                return 
            else:
                page = bs4.BeautifulSoup(raw_HTML.text, 'lxml')
#                 print(page.title.string)
                await self.get_size_variant(url, page, ctx)
                return
        except requests.Timeout as error:
            await client.send_message(ctx.message.channel,"There was a timeout error")
        except requests.ConnectionError as error:
            await client.send_message(ctx.message.channel,"A connection error has occurred.")
        except requests.RequestException as error:
            await client.send_message(ctx.message.channel,"An error occurred making the internet request.")
            
    ''' Retrieves only the absolute URL from passed in URL.
    
        @param url: The address passed in by the user
        @return: absolute url retrieved from given url '''
    def get_absolute_url(self, url):
        absolute_url = re.match('https://', url)
        if absolute_url == None:
            absolute_url = re.match('[a-zA-Z0-9.-]+/', url)
            if absolute_url == None:
                return False
            absolute_url = absolute_url.group()
            return absolute_url
        else:
            absolute_url = re.match('https://[a-zA-Z0-9.-]+/', url)
            absolute_url = absolute_url.group()
            return absolute_url
        
    ''' Retrieves the thumbnail image for the item requested.
    
        @param page: HTML containing information to be scraped for image URL
        @return: url for thumbnail image to be displayed on Discord or None if not found'''
    def get_thumbnail_image(self, page):
        correct_image = None
        img = page.find_all('img')
        for i in img:
            if 'products' in str(i):
                correct_image = str(i)
                break
        
        if correct_image == None:
            return None
        else:
            item_image_url = re.search('cdn\.shopify.+\"', correct_image)
            if item_image_url == None:
                return None
            else:
                item_image_url = item_image_url.group()
                item_image_url = item_image_url.split(' ')
                url = "https://"
                url += item_image_url[0].replace('"','')
                return url
    
    ''' Retrieves the id associated to the item size (required to create a link). 
    
        @param url: The item's url  
        @param page: Page information retrieved through requests
        @param ctx: Discord information  '''
    async def get_size_variant(self, url, page, ctx):
        scripts = page.find_all("script")
        if scripts == None:
            await client.send_message(ctx.message.channel,"An error has occurred completing your request. Check that the website is a shopify website.")
            return
        
        script_index = self.find_variant_script(scripts)
        
        script = scripts[script_index].getText()
        
        ''' split it in this manner to store items of script separated by a new line '''
        script = script.split(';')
        ''' retrieve only the line containing size information '''
        script = script[3]
        ''' split in this manner so that each size is a different list item '''
        script = script.split('{\"id\":')
        ''' remove unwanted information in beginning of list '''
        script.remove(script[0])
        script.remove(script[0])
        
        status = True  
        for item in script:
            if 'public_title\":\"' in item:
                data = item
                data = data.split(',')
                
                size = data[3].split("\"")
                size = size[3]
#                 print(size)
                retrieved_id = data[0]
                
                # add leading and trailing spaces to make regex matching easier
                size = " " + size + " "
                item_size = re.search('\s\d+\.\d+\s', str(size))
                if item_size == None:
                    item_size = re.search('\s\d{1,2}\s', str(size))
                    if item_size == None:
                        item_size = re.search('(?i)(XS|X-S|(\sS\s|Small)|(\sM\s|Medium)|(\sL\s|Large)' + 
                                                      '|XL|XXL|XXXL|X-L|XX-L|XXX-L)', str(size))
                        if item_size == None:
                            item_size = size
                
                if item_size != size:
                    item_size = item_size.group()
                    
                item_size = item_size.replace('\\', '')
                item_size = item_size.replace('/', "")
                status = await self.print_link(url, item_size, str(retrieved_id), ctx)
                if status == False:
                    break
        
        thumbnail_url = self.get_thumbnail_image(page)
        embed = Embed(title=page.title.string, url=url, description=self.atc_links, color=0x00f900)
        embed.set_footer(text=str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        if thumbnail_url == None:
            pass
        else:
            embed.set_thumbnail(url=thumbnail_url)

        await client.send_message(ctx.message.channel, embed=embed)
    
    
    ''' Prints a correctly formated link which takes user straight to purchase.
    
        @param url: URL of the item to be bought
        @param size: Size of the given item
        @param retrieved_id: Id associated to the item size
        @param ctx: Discord information 
        @return: Whether or not generating links was successful '''
    async def print_link(self, url, size, retrieved_id, ctx):
        absolute_url = self.get_absolute_url(url)
        if absolute_url == False:
            await client.send_message(ctx.message.channel, "An error has occurred completing your request")
            return False
        
        self.sizes += size + "\n"
        link = tiny(absolute_url + 'cart/' + retrieved_id + ':1', ctx)
        if link == None:
            return False
        else:
            self.atc_links += '[[ ATC ]](' + link + ') - ' + size + '\n'
        
        return True
    
    ''' Kickstarts the entire script.
    
        @param url: The url pointing to the item which the user wants to buy
        @param ctx: Discord information '''
    async def run(self, url, ctx):
        await self.get_sizes(url, ctx)
        
    ''' Find the correct script to retrieve information from.
    
        @params scripts: All the scripts retrieved for the page '''
    def find_variant_script(self, scripts):  
        for number, script in enumerate(scripts):
            if "variants\":[{" in script.getText():
                return number
                break
            
            
          

            
class eBay(object):
    def ebayview(self, ctx, url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'
        }
        
        count = 0
        try:
            for i in range(200):
                print(f"------- {i} -------")
                req = requests.get(url, headers=headers, verify=True, timeout=10)
                if req.status_code == 200:
                    count += 1
        except Exception as e:
            print(f"EXCEPTION ON EBAYVIEW: {e}")
    
            
            
    def ebaywatch(self, ebaylink, watches):
        account_list = open('accounts.txt', 'r')
        accountsplit = account_list.read().splitlines()
        for x in range (0, watches):
            accountpuller = accountsplit[x]
            s = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            r = s.get('https://signin.ebay.com/ws/eBayISAPI.dll?SignIn&ru=https%3A%2F%2Fwww.ebay.com%2F', headers=headers).content
            soup = BeautifulSoup(r, 'lxml')

            f = soup.find('input', attrs={'id': 'rqid', 'name': 'rqid'})
            rqid = f['value']

            f = soup.find('script', attrs={'type': 'text/javascript', 'id': 'dfpDetails'})
            js = f.find(text=True)
            jsonValue = '{%s}' % (js.partition('{')[2].rpartition('}')[0],)
            value = json.loads(jsonValue)
            mid = value['mid']

            f = soup.find('input', attrs={'type': 'hidden', 'name': 'srt'})
            srt = f['value']
        
            payload = {
                'AppName': '',
                'errmsg': '', 
                'fypReset': '', 
                'htmid': '',
                'i1': '', 
                'ICurl': '', 
                'keepMeSignInOption2': 'on', 
                'lkdhjebhsjdhejdshdjchquwekguid': rqid,
                'mid':  mid,
                'pageType': '-1',
                'pass': 'sonarbot1',
                'returnUrl': 'https://www.ebay.com/',
                'rqid': rqid,
                'rtmData': '',
                'src': '',
                'srcAppId': '',
                'srt': srt,
                'tagInfo': '',
                'userid': accountpuller,
                'usid': rqid
                }

            r = s.post('https://www.ebay.com/signin/s', headers=headers, data=payload).content
   
            r = s.get('https://www.ebay.com/', headers=headers)
            r = s.get(str(ebaylink), headers=headers).content

            soup = BeautifulSoup(r, 'lxml')
            f = soup.find('a', attrs={'id': 'watchLink', 'rel': 'nofollow'})
            link = f['href']
            print(link)
    
            r = s.get(link, headers=headers)
            print('watched')
            
if __name__ == "__main__":           
    ''' Initialize Discord bot by making the first call to it '''
    try:
        db_client = pymongo.MongoClient(MONGODB_URI)
        db = db_client.get_default_database()
        subscriptions = db['subscriptions']
        subscriptions.create_index('email')
        ebay_used_urls.append(datetime.date.today())
        STRIPE = Stripe()
        KRISPYKREME = KrispyKreme()
        SUCCESS_POSTER = SuccessPoster()
        SMS = FOMO_SMS()
        client.run(TOKEN)
    except (HTTPException, LoginFailure) as e:
        client.loop.run_until_complete(client.logout())