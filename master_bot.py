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


from decimal import Decimal
from discord.ext.commands import Bot
from discord.utils import get
from discord.errors import LoginFailure, HTTPException
from discord.embeds import Embed 
from threading import Thread
from twilio.rest import Client

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
# Variables to make calls to Shopify (Subscription related data)
SHOPIFY_USER = os.environ["FOMO_HELPER_SHOPIFY_USER"]
SHOPIFY_PASS = os.environ["FOMO_HELPER_SHOPIFY_PASS"]
# URI for Mongo/Heroku Database
MONGODB_URI = os.environ["FOMO_HELPER_MONGODB_URI"]

PAYPAL_CLIENT_ID = os.environ["FOMO_HELPER_PAYPAL_CLIENT_ID"]
PAYPAL_CLIENT_SECRET = os.environ["FOMO_HELPER_PAYPAL_CLIENT_SECRET"]

# Create Discord Bot instance with the given command triggers
client = Bot(command_prefix=BOT_PREFIX)#, description=BOT_DESCRIPTION#)
# Remove the default Discord help command
client.remove_command('help')
# Reference to Mongo/Heroku database
db = None
# Reference to subscriptions collection
subscriptions = None
# Reference to paypal class object
paypal = None

# Logger for tracking errors.
logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

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
async def sub_and_assign_roles(email, author, free, member, monitors):
    # Search for email in database
    data = subscriptions.find_one({"email": f"{email}"})
    # Reference to the FOMO discord server
    discord_server = client.get_server("355178719809372173")
    # If the email doesn't exist in the database
    if data == None:
        # Insert new user data in the database
        subscriptions.insert({
            "email": email,
            "status": "active",
            "discord_id": author.id,
            "free": free,
            "member": member,
            "monitors": monitors
        })
        
        # Assign correct role to user
        if member:
            role = get(discord_server.roles, name="Premium")
            user = discord_server.get_member(author.id)
            await client.add_roles(user, role)
        elif monitors:
            role = get(discord_server.roles, name="Monitor")
            user = discord_server.get_member(author.id)
            await client.add_roles(user, role)
        elif free:
            role = get(discord_server.roles, name="Free")
            user = discord_server.get_member(author.id)
            await client.add_roles(user, role)
        
        # Send message on Discord
        await client.send_message(author, "Your subscription has been successfully activated!")
        return True
    else:
        # If an entry exists in the database for the email
        status = data['status']
        # Determine how to proceed based on current status of subscription
        if status == "active":
            await client.send_message(author, "You have already activated your subscription. If you believe this to be a mistake, please contact an admin.")
            return False
        else:
            # If subscription was canceled and user wants to reactivate it, he needs an admins approval
            # see the !resub command
            if status == "canceled":
                await client.send_message(author, "Your subscription was previously canceled by one of our admins. Please contact one of them to reactivate it.")
                return False
            else:
                member = str(data["member"])
                monitors = str(data["monitors"])
                free = str(data["free"])
                
                if member == "True":
                    subscriptions.replace_one({
                        "email": email
                    }, {
                        "email": email,
                        "status": "active",
                        "discord_id": author.id,
                        "member": "True",
                        "free": "False",
                        "monitors": "False"
                    })
                    
                    role = get(discord_server.roles, name="Premium")
                    user = discord_server.get_member(author.id)
                    await client.add_roles(user, role)
                elif monitors == "True":
                    subscriptions.replace_one({
                        "email": email
                    }, {
                        "email": email,
                        "status": "active",
                        "discord_id": author.id,
                        "member": "False",
                        "free": "False",
                        "monitors": "True"
                    })
                    
                    role = get(discord_server.roles, name="Monitor")
                    user = discord_server.get_member(author.id)
                    await client.add_roles(user, role)
                else:
                    subscriptions.replace_one({
                        "email": email
                    }, {
                        "email": email,
                        "status": "active",
                        "discord_id": author.id,
                        "member": "False",
                        "free": "True",
                        "monitors": "False"
                    })
                    
                    role = get(discord_server.roles, name="Free")
                    user = discord_server.get_member(author.id)
                    await client.add_roles(user, role)
                    
                    
                await client.send_message(author, "Your subscription has been reactivated!")
                return True
# ------------------------------------------------------------- #
#                                                               #
#                 All the Discord Bot methods                   #
#                                                               #   
# ------------------------------------------------------------- #
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
        
        if status == "canceled":
            pass
        else:
            for role in member.roles:
                if "Premium" or "Monitor" or "Free" in role.name:
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
    
    # Make sure the message sent is not a command
    if not message.content.startswith('!') and not message.content.startswith('?'):
        # Automate responses by displaying specific output based on user message if necessary
         if re.search('nike element react|element react|react 87|react|nike element', message.content, re.IGNORECASE):
             if re.search('sitelist', message.content, re.IGNORECASE):
                await client.send_message(message.channel, 'Nike Element React sitelist URL: <https://goo.gl/b7m6hi>')
             elif re.search('keyword|kw|kws|keywords', message.content, re.IGNORECASE):
                await client.send_message(message.channel, 'Nike Element React keywords: +react, +element, +87')
             elif re.search('raffle|raffles', message.content, re.IGNORECASE):
                 await client.send_message(message.channel, 'Updated list in <#471089859034087434>, don\'t forget to enter! Open raffles can also be found on <https://fomo.supply/>')
         elif re.search('pharrell afro pack|pharrell afro|afro pack|pharrell afro hu|afro hu|pharrell hu', message.content, re.IGNORECASE):
             if re.search('raffle|raffles', message.content, re.IGNORECASE):
                 await client.send_message(message.channel, 'Updated list in <#471089859034087434>, don\'t forget to enter! Open raffles can also be found on <https://fomo.supply/>') 
         elif re.search('slots', message.content, re.IGNORECASE):
             if re.search('guide|how\s+do|work|what\s+are|how\s+to|sign\s+up|submit', message.content, re.IGNORECASE):
                 await client.send_message(message.channel, 'You can find a detailed explanation on how slots work in <#471003962854604810> or in the FOMO Guide: <https://goo.gl/MQUnG7>')
         elif re.search('fomo', message.content, re.IGNORECASE):
             if re.search('guide|how\s+to|works|work|tutorial', message.content, re.IGNORECASE):
                 await client.send_message(message.channel, "FOMO Guide: <https://goo.gl/MQUnG7>")
    else:
        # If it's a command that was sent, process the command normally
        await client.process_commands(message)

''' Admin only function to display all expired premium accounts 

    @param ctx: Discord information '''
@client.command(name='expired',
                description='See all the premium members whose PayPal subscription has expired',
                pass_context=True)
async def expired_subs(ctx):
    # User using the command
    author = ctx.message.author
    # FOMO Discord server reference
    discord_server = client.get_server("355178719809372173")
    # Author and Member are considered different things on Discord
    member = discord_server.get_member(author.id)
    # If admin role exists for the member, run correct process
    if "Admin" in [role.name for role in member.roles]:
        await paypal.paypal_observer(author)
    else:
        await client.send_message(author, "This command is for Admins only")

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

''' Discord event, triggered upon successful Login '''
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    
''' Command used by admins to grant user's permission to resubscribe to the Discord group
    if their subscription was previously cancelled (NOTE - cancelled subscription is different,
    from a disabled subscription.) 
    
    @param ctx: Discord information 
    @param *args: Email and subscription type passed by user '''
@client.command(name='resub',
                description='Gives a member back his subscription if they had their subscription canceled',
                pass_context=True)
async def resub(ctx, *args):
    # Message author
    author = ctx.message.author 
    # FOMO Discord server reference
    discord_server = client.get_server("355178719809372173")
    # Member reference for user 
    member = discord_server.get_member(author.id)
    
    # Make sure message is a private message to FOMO Helper
    if isinstance(ctx.message.channel, discord.PrivateChannel):
        # Make sure an admin is using the command
        if "Admin" in [role.name for role in member.roles]:
            # Check for correct number of parameters passed
            if len(args) < 2:
                await client.send_message(author, "Command is missing an argument. Make sure you provide the shopify email and the role to be given")
            elif len(args) > 2:
                await client.send_message(author, "Command has extra argument(s). Make sure you provide the shopify email and the role to be given only.")
            else:
                # Email passed as a parameter
                email = args[0]
                # Subscription type passed as a parameter 
                sub = args[1]
                
                # Find user information on database if it exists
                data = subscriptions.find_one({"email": f"{email}"})
                if data == None:
                    await client.send_message(author, "Could not find the provided email. Please check that it is correct and try again.")
                else:
                    if sub.lower() == "member" or sub.lower() == "free" or sub.lower() == "monitors":
                        if sub.lower() == "member":
                            subscriptions.update_one({
                                "email": email
                            }, {
                                "$set": {
                                    "status": "disabled",
                                    "member": "True"
                                }
                            }, upsert=False)
                        elif sub.lower() == "free":
                            subscriptions.update_one({
                                "email": email
                            }, {
                                "$set": {
                                    "status": "disabled",
                                    "free": "True"
                                }
                            }, upsert=False)
                        else:
                            subscriptions.update_one({
                                "email": email
                            }, {
                                "$set": {
                                    "status": "disabled",
                                    "monitors": "True"
                                }
                            }, upsert=False)
                    
                        await client.send_message(author, "User has been given permission to reactivate their account!")
                    else:
                        await client.send_message(author, "Provided subscription isn't valid. Please make sure it is either **member**, **free** or **monitors**")
                    
        else:
            await client.send_message(author, "This command is for admins only")
        

''' Method for admin use only. Cancels a user's subscription and updates the database 

    @param ctx: Discord information
    @param email: Email associated to acount to cancel subscription for'''
@client.command(name='cancel',
                description='Cancel a user\'s subscription',
                pass_context=True)
async def cancel(ctx, email):
    # FOMO Discord server reference
    discord_server = client.get_server("355178719809372173")
    # Message author
    author = ctx.message.author 
    # Discord member reference based on user id
    member = discord_server.get_member(author.id)
    
    # If message is a private message 
    if isinstance(ctx.message.channel, discord.PrivateChannel):
        # Check if member is an admin
        if "Admin" in [role.name for role in member.roles]:
            data = subscriptions.find_one({"email": f"{email}"})
            if data == None:
                await client.send_message(author, "Could not find the provided email. Please check that it is correct and try again.")
            else:
                subscriptions.update_one({
                    "email": email
                }, {
                    "$set": {
                        "status": "canceled",
                        "member": "False",
                        "free": "False",
                        "monitors": "False"
                    }
                })
                    
                user_id = data["discord_id"]
                user = discord_server.get_member(user_id)
                monitor_role = get(discord_server.roles, name='Monitor')
                member_role = get(discord_server.roles, name='Premium')
                free_role = get(discord_server.roles, name="Free")
                await client.remove_roles(user, monitor_role)
                await client.remove_roles(user, member_role)
                await client.remove_roles(user, free_role)
                await client.send_message(author, "User subscription successfully canceled")
        else:
            await client.send_message(author, "This command is for admins only")        


''' Command responsible for authenticating a users free subscription on Discord and assigning
    appropriate role 
    
    @param ctx: Discord information
    @param email: email associated to account to activate subscription for '''
@client.command(name='free',
                description='Activate your free subscription to be assigned the appropriate roles',
                pass_context=True)
async def activate_free(ctx, email):
    # Discord message author
    author = ctx.message.author
    # FOMO Discord server reference
    discord_server = client.get_server("355178719809372173")
    
    # If message is a private message
    if isinstance(ctx.message.channel, discord.PrivateChannel):
        try:
            # Make a request to shopify api to conduct search for the passed email
            customers_req = requests.get(f'https://{SHOPIFY_USER}:{SHOPIFY_PASS}@fomosuptest.myshopify.com/admin/customers/search.json?query=email:{email}', timeout=10)
            
            if customers_req.status_code != 200:
                await client.send_message(author, "An error has occurred completing your request")
                return
            else:
                customers_resp = customers_req.json()
#                 print(customers_resp)
                valid_email = len(customers_resp['customers'])
#                 print("VALID EMAIL: " + str(valid_email))
                if valid_email == 0:
                    await client.send_message(author, "This email is invalid. Make sure you use the email you used to create an account on our FOMO website.")
                    return
                else:
                    customer = customers_resp['customers'][0]
                    if customer.get("orders_count") <= 0:
                        pass
                    else:
                        customer_id = str(customer.get("id"))
                        customer_last_order_id = str(customer.get("last_order_id"))
                         
                        last_order_req = requests.get(f'https://{SHOPIFY_USER}:{SHOPIFY_PASS}@fomosuptest.myshopify.com/admin/orders/{customer_last_order_id}.json', timeout=10)
                        if last_order_req.status_code != 200:
                            await client.send_message(author, "An error has occurred")
                            return
                        else:
                            order_resp = last_order_req.json()
#                             print(order_resp)
                            is_free = re.search("line_items':.*title':\s'(discord beta limited access \(free\).*)',\s'quantity", str(order_resp).lower())
                            if is_free == None:
                                orders_req = requests.get(f'https://{SHOPIFY_USER}:{SHOPIFY_PASS}@fomosuptest.myshopify.com/admin/customers/{customer_id}/orders.json', timeout=10)
                                if orders_req.status_code != 200:
                                    await client.send_message(author, "An error has occurred")
                                    return
                                else:
                                    orders_resp = orders_req.json()
                                    is_free = re.search("line_items':.*title':\s'(discord beta limited access \(free\).*)',\s'quantity", str(orders_resp).lower())
                                    if is_free == None:
                                        await client.send_message(author, "You do not have a subscription. If you believe this to be a mistake, please contact an admin.")
                                        return
                                    else:
                                        await sub_and_assign_roles(email, author, True, False, False)
                                        return
                            else:
                                await sub_and_assign_roles(email, author, True, False, False)
                                return 
        except requests.Timeout as error:
            print("There was a timeout error")
            print(str(error))
        except requests.ConnectionError as error:
            print("A connection error has occurred. The details are below.\n")
            print(str(error))
        except requests.RequestException as error:
            print("An error occurred making the internet request.")
            print(str(error))

''' Command responsible for authenticating users premium subscription on Discord and 
    assigning correct role '''
@client.command(name='premium',
                description='Activate your premium subscription to be assigned the appropriate roles',
                pass_context=True)
async def activate_premium(ctx, email):
    # Discord message author  
    author = ctx.message.author
    # FOMO Discord server reference 
    discord_server = client.get_server("355178719809372173")
      
    # Check if message is a private message
    if isinstance(ctx.message.channel, discord.PrivateChannel):
        try:
            await paypal.check_membership(ctx, email)

        except requests.Timeout as error:
            print("There was a timeout error")
            print(str(error))
        except requests.ConnectionError as error:
            print("A connection error has occurred. The details are below.\n")
            print(str(error))
        except requests.RequestException as error:
            print("An error occurred making the internet request.")
            print(str(error))
        
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
        
        keywords = '**!address** \n**!gmail** \n**!atc** \n**!isshopify** \n**!fee** \n**!free** \n**!premium**'
        keyword_descriptions = 'Jig your home address; type input between **" "**\n'
        keyword_descriptions += 'Jig your gmail address\n'
        keyword_descriptions += 'Generate ATC for a shopify URL\n'
        keyword_descriptions += 'Checks if a website is Shopify\n'
        keyword_descriptions += 'Calculates seller profit after fees for a given sale price\n'
        keyword_descriptions += 'Authenticates Free Members and assigns correct role\n'
        keyword_descriptions += 'Authenticates Premium Members and assigns correct role\n'
        
        embed.add_field(name='Keywords:', value=keywords, inline=True)
        embed.add_field(name='Brief:', value=keyword_descriptions, inline=True)
        embed.add_field(name='More Info', value="For more information on a keyword, type **!help keyword**", inline=False)
        await client.send_message(author, embed=embed)    
    elif (len(command) > 0 and (command[0] == 'gmail' or command[0] == 'mail' or command[0] == 'email')):
        desc =  'This command manipulates any gmail address passed to it as a parameter.'
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ gmail | mail | email ]', inline=False)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'address' or command[0] == 'adr' or command[0] == 'addr')):
        desc = 'This command manipulates any residential address passed to it as a parameter.'
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ address | addr | adr ]', inline=False)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'atc')):
        desc = 'Add To Cart command for any Shopify website. Generates a link leading the user '
        desc += 'straight to the payment page. Takes in the item\'s URL as a parameter'
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ atc ]', inline=False)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'isshopify')):
        desc = 'This command uses a given URL in order to determine whether '
        desc += 'a website is a shopify site or not.'
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ isshopify ]', inline=False)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'fee')):
        desc = "Calculates the seller fees applied by different websites."
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ fee ]', inline=False)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'free')):
        desc = "Authenticates new Free Members of the group in the database "
        desc += "and assigns correct role(s) so they can have access to all the correct content. "
        desc += "The parameter for this command is the email used on the FOMO website."
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ free ]', inline=False)
        await client.send_message(author, embed=embed)
    elif (len(command) > 0 and (command[0] == 'premium')):
        desc = "Authenticates new Premium Members of the group in the database "
        desc += "and assigns correct role(s) so they can have access to all the correct content. "
        desc += "The parameter for this command is the email used to make your PayPal payments."
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ premium ]', inline=False)
        await client.send_message(author, embed=embed)
        
        
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
async def address_jig(ctx, adr):
    address = AddressJig()
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

''' Discord command for eBay views: limited to 20 views one command 

    @param url: URL for eBay listing '''
@client.command(name='ebayview', 
                description='Automatic eBay viewer for any listing. Views the given URL 20 times',
                pass_context=True)
async def ebay_view(ctx, url, views):
    try:
        if int(views) < 101:
            await eBay().ebayview(str(url), int(views))
            await client.send_message(ctx.message.channel, 'Link viewed %s times. Please wait for the views to be applied' % (views))
        else:
            await client.send_message(ctx.message.channel, 'The maximum number of views allowed in one request is 100. Please try again')
    except:
        await client.send_message(ctx.message.channel, 'Error. Please contact your server admin.')
     
# ------------------------------------------------------------- #
#                                                               #
# Individual classes to represent the different functionalities #
#             that the Discord bot will have                    #
#                                                               #   
# ------------------------------------------------------------- #
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
            logger.error('Timeout Error: %s', str(error))
            await client.send_message(channel, "There was a timeout error")
        except requests.ConnectionError as error:
            logger.error('Connection Error: %s', str(error))
            await client.send_message(channel, "A connection error has occurred.")
        except requests.RequestException as error:
            logger.error('Request Error: %s', str(error))
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
            logger.error('Timeout Error: %s', str(error))
            await client.send_message(ctx.message.channel,"There was a timeout error")
        except requests.ConnectionError as error:
            logger.error('Connection Error: %s', str(error))
            await client.send_message(ctx.message.channel,"A connection error has occurred.")
        except requests.RequestException as error:
            logger.error('Request Error: %s', str(error))
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
            
            
class PayPal(object):
    def __init__(self):
        self.expiration_date = None
        self.access_token = None
        self.page_count = None
        
    ''' Calculates dates to see if it has been more than a month since user's last payment.
        If it has, it means user's subscription has expired 
        
        @return: Both current date, and date information for around 1 month before current time '''
    def calculateDates(self): 
        END = datetime.datetime.utcnow().replace(tzinfo=pytz.utc).strftime('%Y-%m-%dT%H:%M:%S%z')
        start = datetime.datetime.utcnow().replace(tzinfo=pytz.utc) + datetime.timedelta(-30)
        START = start.strftime('%Y-%m-%dT%H:%M:%S%z')
        return (START, END)
    
    ''' Generates access token for PayPal calls if required and stores it along with the expiration date '''
    def generate_token(self):
        token_url = 'https://api.paypal.com/v1/oauth2/token'
        data = {'grant_type': 'client_credentials'}
        access_token_resp = requests.post(token_url, data, verify=True, auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET))

        print("Access Token: ")
        print(access_token_resp.headers)
        print("Body: " + access_token_resp.text)
           
        json_data = json.loads(access_token_resp.text)
        ''' Access token for PayPal '''
        self.access_token = json_data['access_token']
        ''' Number of seconds until token expires '''
        expires_in = json_data['expires_in']
        exp_date = datetime.datetime.utcnow().replace(tzinfo=pytz.utc) + datetime.timedelta(seconds=expires_in)
        self.expiration_date = exp_date.strftime('%Y-%m-%dT%H:%M:%S%z')
        print(self.expiration_date)
        
    ''' Checks to see if user has purchased a Premium membership 
    
        @param ctx: Discord information
        @param email: Email associated to Discord user to check membership for
        @param param: Index of page currently being looked at for information (pagination)
        @param param: Indicates whether or not it's the observer method that made the call -> SEE paypal_observer()'''
    async def check_membership(self, ctx, email, page=None, observer=False):
        author = ''
        discord_server = client.get_server("355178719809372173")
        
        if observer == True:
            pass
        else: 
            author = ctx.message.author
        
        
        access_token = self.access_token
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc).strftime('%Y-%m-%dT%H:%M:%S%z')
        
        # Regenerate access token if necessary
        if self.expiration_date == None:
            self.generate_token()
            access_token = self.access_token
        if self.expiration_date < now:
            self.generate_token()
            access_token = self.access_token
        
        # Calculate dates to check for expiration
        dates = self.calculateDates()
        
        params = {}
        count = None
        
        if page == None:
            count = 1
            params = {
                'start_date':dates[0],
                'end_date':dates[1],
                'fields':'all',
                'page_size':100,
                'page':1
            }
        else:
            count = page
            params = {
                'start_date':dates[0],
                'end_date':dates[1],
                'fields':'all',
                'page_size':100,
                'page':page
            }
            
        transactions_base_url = 'https://api.paypal.com/v1/reporting/transactions'
        api_call_headers = {'Authorization': 'Bearer ' + access_token }
        transactions = requests.get(transactions_base_url, headers=api_call_headers, verify=True, params=params)
        
        if transactions.status_code != 200:
            if observer:
                await client.send_message(discord_server.get_member("460997994121134082"), "An error has occurred with the PayPal observer")
            else:
                await client.send_message(author, "An error has occurred completing your request")
                return
        else:
            transactions_json = json.loads(transactions.text)
#             print(transactions_json)
            self.page_count = transactions_json['total_pages']
#             print(self.page_count)
            for transaction in transactions_json['transaction_details']:
                if 'email_address' in transaction['payer_info']:
                    trans_email = transaction['payer_info']['email_address']
                    trans_status = transaction['transaction_info']['transaction_status']
                    
                    if trans_email == email:
                        if trans_status == 'S':
                            if transaction['transaction_info']['transaction_amount']['value'] == '20.00':
                                if observer:
                                    return True
                                else:
                                    await sub_and_assign_roles(email, author, False, True, False)
                                    return
                            if transaction['transaction_info']['transaction_amount']['value'] == '15.00':
                                if observer:
                                    return True
                                else:
                                    await sub_and_assign_roles(email, author, False, False, True)
                                    return 
                        else:
                            if observer:
                                return False
                            else:
                                await client.send_message(author, "There was a problem with your transaction or it hasn't been fully processed by PayPal." 
                                + " Please allow PayPal some time to process your payment and try again. If the problem persists, contact one of the admins.")
                                return
            
            if count < self.page_count:
                self.check_membership(ctx, email, count+1)
            else:
                if observer:
                    return False
                else:
                    await client.send_message(author, "This email is invalid. Make sure you use the email for the account you used to make your PayPal payment.")
                    return 
    ''' Observer to check for expired memberships on PayPal 
    
        @param author: User responsible for calling method to check for expired membership ''' 
    async def paypal_observer(self, author):
        discord_server = client.get_server("355178719809372173")
        
        await client.send_message(author, ':hourglass: Checking PayPal. Please wait...')
    
        expired_subs= "Subscriptions for the following emails have either expired or there have been problems with their transaction. Please check PayPal to confirm before handling their subscription.\n"
        list = ""
        emails = subscriptions.distinct("email")
        for email in emails:
            data = subscriptions.find_one({"email": f"{email}"})
            if data != None:
                member = data["member"]
                monitors = data["monitors"]
                if member or monitors == "True":
                    status = await self.check_membership(None, email, None, True)
                    if status == False:
                        list += f"\t- {email}\n"
                    else:
                        continue
            
        if list == "":
            await client.send_message(author, "No subscriptions have expired")
        else:
            expired_subs += list
            await client.send_message(author, expired_subs)
            
class eBay(object):
    async def ebayview(self, product_url, entries):
        entries = int(entries)
        i = 1
        while i < entries + 1:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'
                }
            try:
                a = requests.get(str(product_url), headers=headers)
                i = i+1
            except:
                print('error')
            
if __name__ == "__main__":           
    ''' Initialize Discord bot by making the first call to it '''
    try:
        db_client = pymongo.MongoClient(MONGODB_URI)
        db = db_client.get_default_database()
        subscriptions = db['subscriptions']
        subscriptions.create_index('email')
        paypal = PayPal()

        client.run(TOKEN)
    except (HTTPException, LoginFailure) as e:
        client.loop.run_until_complete(client.logout())
