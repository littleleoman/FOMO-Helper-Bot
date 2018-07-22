'''
Created on Jul 15, 2018

@author: yung_messiah
'''

import bs4
from datetime import datetime
import os
import random
import re
import requests
import string


from discord.ext.commands import Bot
import logging
from discord.errors import LoginFailure, HTTPException
from discord.embeds import Embed    


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
# Create Discord Bot instance with the given command triggers
client = Bot(command_prefix=BOT_PREFIX)#, description=BOT_DESCRIPTION#)
# Remove the default Discord help command
client.remove_command('help')

# Logger for tracking errors.
# logger = logging.getLogger('discord')
# logger.setLevel(logging.ERROR)
# handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
# handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
# logger.addHandler(handler)

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
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'}
    
    URL = "https://tinyurl.com/create.php?source=indexpage&url=" + url + "&submit=Make+TinyURL%21&alias="
    raw_HTML = requests.get(URL, headers=headers, timeout=5)
        
    if raw_HTML.status_code != 200:
        client.send_message(ctx.message.author, "An error has occured completing your request")
        return None
    else:
        page = bs4.BeautifulSoup(raw_HTML.text, 'lxml')
        return page.find_all('div', {'class': 'indent'})[1].b.string


# ------------------------------------------------------------- #
#                                                               #
#                 All the Discord Bot methods                   #
#                                                               #   
# ------------------------------------------------------------- #
'''@client.event
async def on_message(message):
    # Don't want the bot to reply to itself
    if message.author == client.user:
        return 
    
    if not message.content.startswith('!') and not message.content.startswith('?'):
        await client.send_message(message.author, 'Hello! Before I begin to help you out, make sure you\'re familiar with all the commands by typing **!help**')
    else:
        await client.process_commands(message)
        
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
    

''' Discord custom help command, formatted different from the defaul help command

    @param ctx: Discord information
    @param *command: List of arguements passed with the command ''' 
@client.command(name='help',
                description='Help message to guide the user through using the bot.',
                brief='User guide',
                pass_context=True)
async def custom_help(ctx, *command):
    author = ctx.message.author
    
    if len(command) == 0:
#         desc = '**FOMO Helper** is a general service bot for all your consumer needs.'
#         desc += '\n\nThere are a couple of utility commands which are showcased here, and should serve you well.'
#         desc += '\n\nTo use all commands, precede the keyword by the exclamation mark ( **!** ) or a question mark ( **?** ).\n\n'
#         
        embed = Embed(
            color = 0xffffff,
            description = BOT_DESCRIPTION
        )
        
        keywords = '**!address** \n**!gmail** \n**!atc**'
        keyword_descriptions = 'Jig your home address; type input between **" "**\n'
        keyword_descriptions += 'Jig your gmail address\n'
        keyword_descriptions += 'Generate ATC for a shopify URL'
        
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
    elif (len(command) > 0 and (command[0] == 'atc' or command[0] == 'shopify')):
        desc = 'Add To Cart command for any Shopify website. Generates a link leading the user '
        desc += 'straight to the payment page. Takes in the item\'s URL as a parameter'
        embed = Embed(
            color = 0xffffff,
            description = desc
        )
        embed.add_field(name='Aliases', value='[ atc | shopify ]', inline=False)
        
        await client.send_message(author, embed=embed)


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
                aliases=['jig', 'addr', 'adr'],
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
                aliases=['shopify'],
                pass_context=True)
async def shopify(ctx, url):
    shopify = Shopify()
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
    
    ''' Retrieves sizes for item in stock.
        
        @param url: The url passed by the user pointing to the item he/she wants
        @param ctx: Discord information  ''' 
    async def get_sizes(self, url, ctx):
        headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'}
    
        # Ensure url starts with https:// in case url only contains www....
        url_formatting = re.match('https://', url)
        if url_formatting == None:
            url = 'https://' + url
        try:
            raw_HTML = requests.get(url, headers=headers, timeout=5)
            if raw_HTML.status_code != 200:
                await client.send_message(ctx.message.author,"An error has occured completing your request")
                return 
            else:
                page = bs4.BeautifulSoup(raw_HTML.text, 'lxml')
#                 print(page.title.string)
                await self.get_size_variant(url, page, ctx)
                return
        except requests.Timeout as error:
            await client.send_message(ctx.message.author,"There was a timeout error")
            logger.error('Timeout Error: %s', str(error))
        except requests.ConnectionError as error:
            await client.send_message(ctx.message.author,"A connection error has occured. Make sure you are connected to the Internet. The details are below.\n")
            logger.error('Connection Error: %s', str(error))
        except requests.RequestException as error:
            await client.send_message(ctx.message.author,"An error occured making the internet request.")
            logger.error('Request Error: %s', str(error))
            
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
            await client.send_message(ctx.message.author,"An error has occured completing your request")
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

        await client.send_message(ctx.message.author, embed=embed)
    
    
    ''' Prints a correctly formated link which takes user straight to purchase.
    
        @param url: URL of the item to be bought
        @param size: Size of the given item
        @param retrieved_id: Id associated to the item size
        @param ctx: Discord information 
        @return: Whether or not generating links was successful '''
    async def print_link(self, url, size, retrieved_id, ctx):
        absolute_url = self.get_absolute_url(url)
        if absolute_url == False:
            await client.send_message(ctx.message.author, "An error has occured completing your request")
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
            
            
''' Initialize Discord bot by making the first call to it '''
try:
    client.run(TOKEN)
except (HTTPException, LoginFailure) as e:
    client.loop.run_until_complete(client.logout())
