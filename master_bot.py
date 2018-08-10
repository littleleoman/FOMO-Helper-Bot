'''
Created on Jul 15, 2018

@author: yung_messiah
'''

import bs4
import discord
import logging
import os
import pymongo
import random
import re
import requests
import string
from decimal import Decimal

from datetime import datetime
from discord.ext.commands import Bot
from discord.utils import get
from discord.errors import LoginFailure, HTTPException
from discord.embeds import Embed    
from pydoc import describe


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

# Token for Discord Bot, retrieved 
TOKEN = os.environ["TOKEN"]
# Variables to make calls to Shopify (Subscription related data)
SHOPIFY_USER = os.environ["SHOPIFY_USER"]
SHOPIFY_PASS = os.environ["SHOPIFY_PASS"]

MONGODB_URI = os.environ["MONGODB_URI"]


# Create Discord Bot instance with the given command triggers
client = Bot(command_prefix=BOT_PREFIX)#, description=BOT_DESCRIPTION#)
# Remove the default Discord help command
client.remove_command('help')
# Reference to Mongo/Heroku database
db = None
# Reference to subscriptions collection
subscriptions = None

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
    @return: The shortened url
'''
def tiny(url, ctx):
    URL = "https://tinyurl.com/create.php?source=indexpage&url=" + url + "&submit=Make+TinyURL%21&alias="
    raw_HTML = requests.get(URL, headers=headers, timeout=10)
        
    if raw_HTML.status_code != 200:
        client.send_message(ctx.message.channel, "An error has occurred completing your request")
        return None
    else:
        page = bs4.BeautifulSoup(raw_HTML.text, 'lxml')
        return page.find_all('div', {'class': 'indent'})[1].b.string
    
    

async def sub_and_assign_roles(email, author):
    data = subscriptions.find_one({"email": f"{email}"})
    if data == None:
        subscriptions.insert({
            "email": email,
            "status": "active",
            "discord_id": author.id
        })
        #role = "Member"
        await client.send_message(author, "Your subscription has been successfully activated!")
        return True
    else:
        status = data['status']
        if status == "active":
            await client.send_message(author, "You have already activated your subscription. If you believe this to be a mistake, please contact an admin.")
            return False
        else:
            subscriptions.replace_one({
                "email": email
            }, {
                "email": email,
                "status": "active",
                "discord_id": author.id
            })
            await client.send_message(author, "Your subscription has been reactivated!")
            return True
# ------------------------------------------------------------- #
#                                                               #
#                 All the Discord Bot methods                   #
#                                                               #   
# ------------------------------------------------------------- #
@client.event
async def on_member_remove(member):
    for role in member.roles:
        if "Member" in role.name:
            result = subscriptions.update_one({
                "discord_id": member.id
            }, {
                "$set": {
                    "status": "disabled"
                }
            }, upsert=False)
    
@client.event
async def on_message(message):
    # Don't want the bot to reply to itself
    if message.author == client.user:
        return 
      
    if not message.content.startswith('!') and not message.content.startswith('?'):
        # List of keywords for automated responses
        # keywords_1 = ['presto','prestos','sitelist','presto sitelist URL (there isn\'t one yet)']
        # keywords_2 = ['presto','prestos', 'keywords','kw','presto keywords (unavailable at this time)']
        # keywords_3 = ['presto','prestos','raffle','raffles','Open raffles can be found in #raffles or on https://fomo.supply/']
        # keywords_4 = ['FOMO','guide','tutorial','how to','FOMO Guide: https://goo.gl/MQUnG7']
         if re.search('travis|scott|air force|sail', message.content, re.IGNORECASE):
             if re.search('sitelist', message.content, re.IGNORECASE):
                await client.send_message(message.channel, 'Travis Scott sitelist URL: <https://goo.gl/b7m6hi>')
             elif re.search('keyword|kw', message.content, re.IGNORECASE):
                await client.send_message(message.channel, 'Travis Scott keywords: +travis, +sail, +force')
             elif re.search('raffle', message.content, re.IGNORECASE):
                 await client.send_message(message.channel, 'Updated list in <#471089859034087434>, don\'t forget to enter! Open raffles can also be found on <https://fomo.supply/>')
         elif re.search('slots', message.content, re.IGNORECASE):
             if re.search('guide|how\s+do|fomo|work|what\s+are|how\s+to|sign\s+up|submit', message.content, re.IGNORECASE):
                 await client.send_message(message.channel, 'You can find a detailed explanation on how slots work in <#471003962854604810> or in the FOMO Guide: <https://goo.gl/MQUnG7>')
    else:
        await client.process_commands(message)

            
'''
# @client.event
# async def on_member_join(member):
#     pass
'''

''' Discord event, triggered upon successful Login '''
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


@client.command(name='activate',
                description='Activate your subscription to be assigned the appropriate roles',
                pass_context=True)
async def activate_subscription(ctx, email):
    author = ctx.message.author 
    discord_server = client.get_server("355178719809372173")
    
    try:
        customers_req = requests.get(f'https://{SHOPIFY_USER}:{SHOPIFY_PASS}@fomosuptest.myshopify.com/admin/customers/search.json?query=email:{email}', timeout=10)
        if customers_req.status_code != 200:
            print("THE ERROR IS COMING RIGHT HERE")
            await client.send_message(author, "An error has occurred completing your request")
        else:
            customers_resp = customers_req.json()
            print(customers_resp)
            valid_email = len(customers_resp['customers'])
            print("VALID EMAIL: " + str(valid_email))
            if valid_email == 0:
                await client.send_message(author, "This email is invalid. Make sure you use the email you used to create an account on our FOMO website.")
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
                    else:
                        order_resp = last_order_req.json()
                        is_beta = re.search("line_items':.*title':\s'(discord beta access)',\s'quantity", str(order_resp).lower())
                        if is_beta == None:
                            orders_req = requests.get(f'https://{USER}:{PASS}@fomosuptest.myshopify.com/admin/customers/{customer_id}/orders.json', timeout=10)
                            if orders_req.status_code != 200:
                                await client.send_message(author, "An error has occurred")
                            else:
                                orders_resp = orders_req.json()
                                is_beta = re.search("line_items':.*title':\s'(discord beta access)',\s'quantity", str(orders_resp).lower())
                                if is_beta == None:
                                    await client.send_message(author, "You do not have a subscription. If you believe this to be a mistake, please contact an admin.")
                                else:
                                    status = await sub_and_assign_roles(email, author)
                                    if status == True:
                                        role = get(discord_server.roles, name="Member")
                                        user = discord_server.get_member(author.id)
                                        await client.add_roles(user, role)
                        else:
                            status = await sub_and_assign_roles(email, author)
                            if status == True:
                                role = get(discord_server.roles, name="Member")
                                user = discord_server.get_member(author.id)
                                await client.add_roles(user, role)

    except requests.Timeout as error:
        print("There was a timeout error")
        print(str(error))
    except requests.ConnectionError as error:
        print("A connection error has occurred. The details are below.\n")
        print(str(error))
    except requests.RequestException as error:
        print("An error occurred making the internet request.")
        print(str(error))
    

''' Discord custom help command, formatted different from the defaul help command

    @param ctx: Discord information
    @param *command: List of arguements passed with the command '''  
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
        
        keywords = '**!address** \n**!gmail** \n**!atc** \n**!isshopify** \n**!fee**'
        keyword_descriptions = 'Jig your home address; type input between **" "**\n'
        keyword_descriptions += 'Jig your gmail address\n'
        keyword_descriptions += 'Generate ATC for a shopify URL\n'
        keyword_descriptions += 'Checks if a website is Shopify\n'
        keyword_descriptions += 'Calculates seller profit after fees for a given sale price'
        
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
    elif (len(command) > 0 and (command[0] == 'fee')):
        desc = "Calculates the seller fees applied by different websites."
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        
        embed.add_field(name='Aliases', value='[ fee ]', inline=False)
        
        await client.send_message(author, embed=embed)

''' Discord command to calcualte the feels that are applied to sale products on multiple websites.

    @param ctx: Discord information
    @param sale_price: Price for which to make the calculations'''
@client.command(name='fee',
                description='Calculates the seller fees applied by different websites',
                pass_context=True)
async def fee_calculator(ctx, sale_price):
    sites = []
    channel = ctx.message.channel
    
    if re.match('^\d+(\.\d*)*$', sale_price) == None:
        await client.send_message(channel, 'The value given is not a proper monetary value')
    else:
        price = Decimal(sale_price)
        price = round(price, 2)
        
        # Tuple format
        #    - site title
        #    - fee percentage
        #    - fixed fee (0 if none)
        ebay = ('eBay', 0.09, 0.00)
        grailed = ('Grailed', 0.089, 0.30)
        paypal = ('PayPal', 0.029, 0.30)
        goat = ('Goat', 0.095, 5.00)
        stockx = ('StockX', 0.125, 0.00)
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


# ------------------------------------------------------------- #
#                                                               #
# Individual classes to represent the different functionalities #
#             that the Discord bot will have                    #
#                                                               #   
# ------------------------------------------------------------- #
class GmailJig(object):
    emails = ''
    emails_2 = ''
    
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
        verified = re.search('(@gmail.+)', email)
        if verified == None:
            await client.send_message(ctx.message.author,"Invalid email address. Please use a @gmail address")
        else:
            email_suffix = verified.group()
            prefix = email.replace(email_suffix, '')
            if len(prefix) > 2:
                await self.jig_email(prefix, email_suffix, ctx)
            else:
                await client.send_message(ctx.message.author,"Your email is not long enough. Please try another email")
    
    ''' Jigs a given gmail address.
    
        @param email_prefix: Everything before the @ sign
        @param email_suffix: Everything after the @ sign, @ sign included
        @param ctx: Discord information '''   
    async def jig_email(self, email_prefix, email_suffix, ctx):
        used_indeces = []
        email_dot_indeces = []
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
    
    ''' Generates the 4 character code to be added to beginning of address. '''
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
                page = bs4.BeautifulSoup(raw_HTML.text, 'lxml')
                script = page.find_all('script')
                for i in script:
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
    
        @param url: The address passed in by the user '''
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
    
        @param page: HTML containing information to be scraped for image URL '''
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
        embed.set_footer(text=str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
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
            
if __name__ == "__main__":           
    ''' Initialize Discord bot by making the first call to it '''
    try:
        db_client = pymongo.MongoClient(MONGODB_URI)
        db = db_client.get_default_database()
        subscriptions = db['subscriptions']
        subscriptions.create_index('email')

        client.run(TOKEN)
    except (HTTPException, LoginFailure) as e:
        client.loop.run_until_complete(client.logout())
