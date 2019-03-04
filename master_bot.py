'''
Created on Jul 15, 2018
@author: yung_messiah
'''
import asyncio, datetime, discord, pinger, json, success, os, pymongo, re, requests, _thread, stripe, shopify, solebox
import sms as SMS_CLIENT
import ebay as EBAY
import krispykreme as KK
from dateutil.relativedelta import *
import gmail as GM
from address import AddressJig
from fee import feeCalc
from discord.ext.commands import Bot
from discord.utils import get
from discord.errors import LoginFailure, HTTPException
from discord.embeds import Embed 

with open('config.json','r') as config:
    userInfo = json.load(config)

# PULL PINGER KEYWORDS
k = requests.get('https://jsonblob.com/api/jsonBlob/1a574529-3e55-11e9-bd88-f34ccbbcde5d')
k = json.loads(k.text)
# Token for Discord Bot 
TOKEN = os.environ["BOT_TOKEN"]
MONGODB_URI = os.environ["MONGODB_URI"]
FOMO_STRIPE_KEY = userInfo['STRIPE_KEY']
MOREHYPED_STRIPE_KEY = userInfo['MOREHYPED']

# PINGER CHANNELS
posted_channels = dict()

server_id = userInfo['server_id']
footer_text = userInfo['footer_text']
member_role = userInfo['member_role']
sub_channel = userInfo['sub_channel']
sitelist_link = userInfo['sitelist_link']
BOT_NAME = userInfo['BOT_NAME']
guide_link = userInfo['guide_link']
restock_role_id = "<@&{}>".format(userInfo['RESTOCK_ROLE_ID'])
mongo_sms_url = userInfo['mongo_sms_url']
discord_owner_id = userInfo['discord_owner_id']
icon_img = userInfo['icon_img']
twitter_consumer_key = userInfo['twitter_consumer_key']
twitter_consumer_secret = userInfo['twitter_consumer_secret']
twitter_access_token = userInfo['twitter_access_token']
twitter_access_secret = userInfo['twitter_access_secret']
twilio_from = userInfo['twilio_from']
twilio_auth_token = userInfo['twilio_auth_token']
twilio_sid = userInfo['twilio_sid']
twilio_number = userInfo['twilio_number']
MONITOR_LIST = userInfo['MONITORS']
fmRole = userInfo['FREE_MONTH']

# Discord command triggers
BOT_PREFIX = ("?", "!")
# General Discord Bot Description

# Initiliaze Stripe api with correct credential
stripe.api_version = "2018-11-08"

client = discord.ext.commands.Bot(command_prefix=BOT_PREFIX)#, description=BOT_DESCRIPTION#)
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
    
# Subscribes user to service by adding them to the database and assigning the appropriate role(s).
# @param email: The email to be added to the database
# @param author: User responsible for sending authentication message
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
            query = { "discord_id": f"{member.id}" }
            subscriptions.delete_one(query)
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
### MONITOR PINGER ----------------------------------------------------------------------------------------- MONITOR PINGER ###
    embeds = message.embeds
    keywords = requests.get('https://jsonblob.com/api/jsonBlob/1a574529-3e55-11e9-bd88-f34ccbbcde5d')
    keywords = json.loads(keywords.text)
    if len(embeds) == 0:
        for keyword in keywords:
            sub_keys = keywords[keyword]
            for sub_key in sub_keys:
                 
                if keyword.lower() in message.content.lower() and sub_key.lower() in message.content.lower() and (message.channel.name in MONITOR_LIST): 
                    has_posted = pinger.channel_check(str(message.channel), keyword, sub_key, posted_channels)
                    if has_posted == False:
                        posted_channels[str(message.channel)].append((datetime.datetime.time(datetime.datetime.now().replace(microsecond=0)), keyword, sub_key))
                        embed = discord.Embed(title="KEYWORD MATCHED!", description=f"{keyword}, {sub_key}", color=0xffffff)
                        embed.set_footer(icon_url=icon_img, text=footer_text)
                        await client.send_message(message.channel, restock_role_id, embed=embed)     
    else:
        for embed in embeds:
            for keyword in keywords:
                sub_keys = keywords[keyword]
                for sub_key in sub_keys:
                    if ((keyword.lower() in embed["description"].lower() or keyword.lower() in embed["title"].lower()) and 
                        (sub_key.lower() in embed["description"].lower() or sub_key.lower() in embed["title"].lower()) and (message.channel.name in MONITOR_LIST)):  
                        has_posted = pinger.channel_check(str(message.channel), keyword, sub_key, posted_channels)
                        if has_posted == False:
                            posted_channels[str(message.channel)].append((datetime.datetime.time(datetime.datetime.now().replace(microsecond=0)), keyword, sub_key))
                            embed = discord.Embed(title="KEYWORD MATCHED!", description=f"{keyword}, {sub_key}", color=0xffffff)
                            embed.set_footer(icon_url=icon_img, text=footer_text)
                            await client.send_message(message.channel, restock_role_id, embed=embed)
### MONITOR PINGER ----------------------------------------------------------------------------------------- MONITOR PINGER ###
        
### SMS COMMANDS ------------------------------------------------------------------------------------------ SMS COMMANDS ###    
    if message.content.startswith('sms!help'):
        embed = Embed(title="SMS HELP CENTER", color=0xffffff)
        embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
        embed.add_field(name="sms!add", value="Adds your number to the database.")
        embed.add_field(name="sms!check", value="Checks if your number is in the database.")
        embed.add_field(name="sms!update", value="Updates your number in the database.")
        embed.add_field(name="sms!stop", value="Removes your number from the database.")
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(message.author, embed=embed)
    elif message.content.startswith('sms!stop'):
        response = await SMS_CLIENT.remove_user(message.author.id)
        print(response)
        if (response["DELETED"] == "TRUE"):
            embed = Embed(title="REMOVED", description="You will no longer receive SMS alerts.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.add_field(name="LEARN MORE BY SAYING:", value="sms!help")
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(message.author, embed=embed)
        else:
            embed = Embed(title="NOT FOUND!", description="You were not found in the database.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.add_field(name="LEARN MORE BY SAYING:", value="sms!help")
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(message.author, embed=embed)
    elif message.content.startswith('sms!update'):
        number = str(message.content)
        number = number.replace("sms!update ","")
        response = await SMS_CLIENT.update_user(message.author.id, number)
        print(response)
        if (response['result'] == 'SUCCESS'):
            embed = Embed(title="SUCCESS!", description="Your number on file was updated.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.add_field(name="NUMBER ON FILE:", value=response['number'])
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(message.author, embed=embed)
        else:
            embed = Embed(title="NOT FOUND!", description="You were not found in the database.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.add_field(name="LEARN MORE BY SAYING:", value="sms!help")
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(message.author, embed=embed)
    elif message.content.startswith('sms!check'):
        response = await SMS_CLIENT.check_user(message.author.id)
        print(response)
        if response['result'] == 'SUCCESS':
            embed = Embed(title="FOUND!", description="You were found in the database: `{}`".format(response['number']), color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.add_field(name="TO UPDATE YOUR NUMBER ON FILE, SAY:", value="sms!update")
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(message.author, embed=embed)
        else:
            embed = Embed(title="NOT FOUND!", description="You were not found in the database.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.add_field(name="TO ADD YOUR NUMBER, SAY:", value="sms!add followed by your number with the country & area code.")
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(message.author, embed=embed)
    elif message.content.startswith('sms!add'):
        number = str(message.content)
        number = number.replace("sms!add ","")
        response = await SMS_CLIENT.add_user(message.author.id, number)
        print(response)
        if response['result'] == 'DUPLICATE':
            embed = Embed(title="FOUND!", description="You are already in the database.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.add_field(name="TO UPDATE YOUR NUMBER, SAY:", value="sms!update")
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(message.author, embed=embed)
        elif response['result'] == 'FAILED':
                embed = Embed(title="FAILED", description="Make sure you format your number correctly", color=0xffffff)
                embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                embed.add_field(name="FOR EXAMPLE:", value="sms!add +13058554140")
                embed.set_footer(icon_url=icon_img, text=footer_text)
                await client.send_message(message.author, embed=embed)
        elif response['result'] == 'SUCCESS':
                embed = Embed(title="SUCCESS!", description="You have been added to the database.", color=0xffffff)
                embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                embed.add_field(name="Number on File:", value=response['number'])
                embed.set_footer(icon_url=icon_img, text=footer_text)
                await client.send_message(message.author, embed=embed)

 ### SMS COMMANDS ------------------------------------------------------------------------------------------ SMS COMMANDS ###    


### GUIDE AND SITELIST COMMANDS --------------------------------------------------------------------------- GUIDE AND SITELIST COMMANDS ###
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
### GUIDE AND SITELIST COMMANDS --------------------------------------------------------------------------- GUIDE AND SITELIST COMMANDS ###
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
    if len(command) == 0:
        embed1 = Embed(
            title="__***{} COMMANDS***__".format(BOT_NAME),
            description="**List of commands I can run for you** :slight_smile:",
            color = 0xffffff
            #description = BOT_DESCRIPTION
        )
### ACTIVATION HELP COMMAND ------------------------------------------------------------------------------------------- ACTIVATION HELP COMMAND ###
        embed2 = Embed(
            title=":closed_lock_with_key: __***AUTHENTICATION COMMANDS***__",
            description="**Commands to activate or cancel your membership.**",
            color = 0xffffff
            #description = BOT_DESCRIPTION
        )
        embed2.add_field(name=':white_check_mark: !activate [email]\nExample: `!activate fomo@gmail.com`',value="Activate your subscription. Follow the example, if you have trouble, please open a ticket or DM an admin!", inline=True)
        embed2.add_field(name=':sob: !cancel [email]\nExample: `!cancel fomo@gmail.com`', value='Cancel your subscription. You will remain a member until 30 days after your last payment and no longer will be charged.', inline=True)
### ACTIVATION HELP COMMAND ------------------------------------------------------------------------------------------- ACTIVATION HELP COMMAND ###

### SHOPIFY HELP COMMAND --------------------------------------------------------------------------------------- SHOPIFY HELP COMMAND ###
        embed3 = Embed(
            title=":shopping_bags: __***SHOPIFY TOOLS***__",
            description='**Commands for all of your Shopify needs!**',
            color = 0xffffff
            #description = BOT_DESCRIPTION
        )
        embed3.add_field(name=':grey_question: !isshopify [URL]\nExample: `!isshopify https://kith.com`', value='Check if any given website is a Shopify website.', inline=True)
        embed3.add_field(name=':shopping_cart: !atc [URL]\nExample: `!atc https://kith.com/product/sneaker`', value='Generate ATC links for any Shopify product. These links add the product to your cart to help you checkout much faster!', inline=True)
        embed3.add_field(name=':globe_with_meridians: !shopify\nExample: `!shopify`',value='Generate an account on any Shopify website. I will ask you for the information I need after you call the command.', inline=True)
        embed3.add_field(name=':arrows_counterclockwise: !delay\nExample: `!delay`',value='Calculate a delay to use with your Shopify bot. The delay calculated will __**NEVER**__ get your proxies banned. I will ask you for the information I need after you call the command.', inline=True)
### SHOPIFY HELP COMMAND --------------------------------------------------------------------------------------- SHOPIFY HELP COMMAND ###

### SMS HELP COMMAND --------------------------------------------------------------------------------------- SMS HELP COMMAND ###
        embed4 = Embed(
            title=":speech_left: __***SMS NOTIFICATIONS***__",
            description='**Say `sms!help` to learn about my SMS commands.**',
            color = 0xffffff
            #description = BOT_DESCRIPTION
        )
### SMS HELP COMMAND --------------------------------------------------------------------------------------- SMS HELP COMMAND ###

### TOOLS HELP COMMAND ------------------------------------------------------------------------------------------- TOOLS HELP COMMAND ###
        embed5 = Embed(
            title=":tools: __***MISCELLANEOUS TOOLS***__",
            description='**Commands to check fees on popular reselling platforms and more.**',
            color = 0xffffff
            #description = BOT_DESCRIPTION
        )
        embed5.add_field(name=":incoming_envelope: !gmail [gmail]\nExample: `!gmail fomo@gmail.com`",value="Generate additional email addresses using Gmail's period trick. I will need your full Gmail address like in the example.", inline=True)
        embed5.add_field(name=':mailbox_with_mail: !address ["address"]\nExample: `!address "1234 152nd Ave`"',value="Generate additional unique shipping addresses for the same address. These addresses are accepted by all shipping carriers. Use these to order more than 1 of the same item to the same place. Make sure to wrap you address in quotes like in the example!", inline=True)
        embed5.add_field(name=':moneybag: !fee [amount]\nExample: `!fee 1000`',value="Calculate seller fees and payouts for all major reselling platforms.", inline=True)
        embed5.add_field(name=':doughnut: !donutuk [gmail prefix]\nExample: `!donutuk fomo`', value="Get a free Krispy Kreme doughnut, 100% legit and safe. Make sure to pass in your Gmail prefix as a paremeter. If your Gmail is fomo@gmail.com, send `!donutuk fomo`, for example.", inline=True)
### TOOLS HELP COMMAND ------------------------------------------------------------------------------------------- TOOLS HELP COMMAND ###

### EBAY HELP COMMAND ------------------------------------------------------------------------------------------- EBAY HELP COMMAND ###
        embed6 = Embed(
            title=":shopping_bags: __***EBAY TOOLS***__",
            description='**Commands to add watchers and/or viewers to your eBay listing(s).**',
            color = 0xffffff
            #description = BOT_DESCRIPTION
        )

        embed6.add_field(name=':eye: !ebayviews [eBay listing URL]\nExample: `!ebayviews https://ebay.com/itm/1234`',value='Add 200 views to your eBay listing. Simply pass in your listing URL as a parameter! Please allow up to 5 minutes for views to be applied.', inline=True)
        embed6.add_field(name=':watch: !ebaywatch [eBay listing URL] [number of watchers]\nExample: `!ebaywatch https://ebay.com/itm/1234 10`',value="Add as many as 10 watchers to your eBay listing. Follow the example to make sure you call the command correctly! Please allow up to 5 minutes for watches to be applied.", inline=True)
### EBAY HELP COMMAND ------------------------------------------------------------------------------------------- EBAY HELP COMMAND ###

### FINAL HELP MESSAGE ------------------------------------------------------------------------------------------- FINAL HELP MESSAGE ###
        embed7 = Embed(
            title=":warning:",
            description='**If you are having any troubles or issues, please open a ticket or DM an admin!**',
            color = 0xffffff
            #description = BOT_DESCRIPTION
        )
### FINAL HELP MESSAGE ------------------------------------------------------------------------------------------- FINAL HELP MESSAGE ###

### SEND HELP MESSAGE ------------------------------------------------------------------------------------------- SEND HELP MESSAGE ###
        embeds = list()
        embeds.append(embed1)
        embeds.append(embed2)
        embeds.append(embed3)
        embeds.append(embed4)
        embeds.append(embed5)
        embeds.append(embed6)
        embeds.append(embed7)
        
        for embed in embeds:
            await client.send_message(ctx.message.author,embed=embed)
### SEND HELP MESSAGE ------------------------------------------------------------------------------------------- SEND HELP MESSAGE ###

### CALENDAR START ------------------------------------------------------------------------------------------------ CALENDAR START
@client.command(name='calendar', pass_context=True)
@discord.ext.commands.has_any_role("Admin","Moderator","Support")
async def post_calendar(ctx):
    author = ctx.message.author
    channel = '534057583426797568'
    #JORDAN 1 CRIMSON START --- EXAMPLE START
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
    #JORDAN 1 CRIMSON END --- EXAMPLE END
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
    embed.add_field(name="MARKET:", value="[CLICK HERE]({})".format(suplink), inline=True)
    embed.set_footer(icon_url="https://i.imgur.com/5fSzax1.jpg", text="Powered by FOMO | @FOMO_supply | Information is Subject to Change!")


    await client.send_message(author, "LOOKING GOOD?", embed=embed)
    await client.send_message(author, "Say `Yes` or `Y` if you are done, and `N` or `no` if you aren't.")
    response  = await client.wait_for_message(author=author)

    if 'y' in str(response.content).lower():
        await client.send_message(client.get_channel(channel), embed=embed)
        await client.send_message(author, 'MESSAGE POSTED')
    else:
        return await client.send_message(author, 'Please try again by saying `!calendar`')
### CALENDAR END ------------------------------------------------------------------------------------------------ CALENDAR START

### START DELAY FUNCTION ------------------------------------------------------------------------------- START DELAY FUNCTION ###
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
### END DELAY FUNCTION ------------------------------------------------------------------------------- END DELAY FUNCTION ###


### ADMIN STRIPE COMMANDS ---------------------------------------------------------------------------- ADMIN STRIPE COMMANDS ###
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
### ADMIN STRIPE COMMANDS ---------------------------------------------------------------------------- ADMIN STRIPE COMMANDS ###

### ACTIVATE & CANCEL COMMANDS ------------------------------------------------------------------------------------------------ ACTIVATE & CANCEL COMMANDS ###
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

### ACTIVATE & CANCEL COMMANDS ------------------------------------------------------------------------------------------------ ACTIVATE & CANCEL COMMANDS ###

### KRISPY KREME DONUT FOOD COMMAND ----------------------------------------------------------------------------------- KRISPY KREME DONUT FOOD COMMAND ###
@client.command(name='donutuk', 
                pass_context=True)
async def donut_message(ctx, gmail):
    author = ctx.message.author
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
### KRISPY KREME DONUT FOOD COMMAND ----------------------------------------------------------------------------------- KRISPY KREME DONUT FOOD COMMAND ###

### FREE MONTH COMMAND START ---------------------------------------------------------------------------------------- FREE MONTH COMMAND START
@client.command(name='fmCheck', pass_context=True)
async def check(ctx):
    date = datetime.datetime.today().strftime('%Y-%m-%d')

    f = open("FREE_MONTHS.txt", "r")
    lines = f.readlines()
    f.close()
    f = open("FREE_MONTHS.txt", "w")
    for line in lines:
        if f'"expiration": "{date}"'+"\n" not in line:
            jsonMember = json.loads(line)[member_role]
            if jsonMember == "false":
                jsonID = json.loads(line)["id"]
                server = client.get_server(server_id)
                member = server.get_member(jsonID)
                role = get(ctx.message.server.roles, name=fmRole)
                role2 = get(ctx.message.server.roles, name=member_role)
                await client.remove_roles(member, role)
                await client.remove_roles(member, role2)
                await client.send_message(member,'Your free trial at **FOMO** has ended. Follow us on [social media](https://twitter.com/fomo_supply) to grab a spot on our next restock! :heart:')
                await client.send_message(ctx.message.channel,"<@{}>'s Free Month has ended".format(member.id))
            else:
                jsonID = json.loads(line)["id"]
                server = client.get_server(server_id)
                member = server.get_member(jsonID)
                role = get(ctx.message.server.roles, name=fmRole)
                await client.remove_roles(member, role)
                await client.send_message(member,'Your free trial at **FOMO** has ended. If you are still owed a refund, please open a ticket :heart:')
                await client.send_message(ctx.message.channel,"<@{}>'s Free Month has ended".format(member.id))

        else:
            f.write(line)
    f.close()
    f = open("FREE_MONTHS.txt", "r")
    lines2 = f.readlines()
    f.close()
    if lines == lines2:
        await client.send_message(ctx.message.channel, "Were all good.")
        
# member_role = '460930653350002698'
# free_month_role = '493636552661008384'

@client.command(name='fmEnd', pass_context=True)
async def end(ctx, user : discord.Member):
    await client.delete_message(ctx.message)
    role = discord.utils.get(ctx.message.server.roles, name=fmRole)
    role2 = discord.utils.get(ctx.message.server.roles, name=member_role)
    await client.remove_roles(user, role)
    await client.remove_roles(user, role2)
    await client.say(f"{user} has lost his privileges.")
    embed = discord.Embed(
    title = "Your Subscription has Ended",
    description = """
Hey there! Hope ya enjoyed your time!
    """,
    colour = 0xffffff
)
    await client.send_message(user, embed=embed)


@client.command(name='freemonth', pass_context=True)
async def freemonth(ctx, user : discord.Member):
    if "546371982619443220" in [role.id for role in user.roles]:
        member = user
        ids = member.id
        your_datetime = datetime.datetime.today()
        test = your_datetime + relativedelta(months=1)
        expire = test.strftime('%Y-%m-%d')
        date = datetime.datetime.today().strftime('%Y-%m-%d')
        role = discord.utils.get(member.server.roles, name=fmRole)
        await client.send_message(ctx.message.channel, f"{user} has been given a **FREE MONTH** of access.")
        embed = discord.Embed(
            title = "Free Month!",
            description = f"Hello, since you're already a member you can claim a refund for this month's fee.",
            color = 0xffffff
        )
        await client.send_message(user, embed=embed)
        data = {
            "id": ids,
            "start": date,
            "expiration": expire,
            member_role: "true"
        }
        with open("FREE_MONTHS.txt", 'a') as outfile:
            json.dump(data, outfile)
            outfile.write("\n")
        await client.add_roles(user, role)
    else:
        member = user
        ids = member.id
        your_datetime = datetime.datetime.today()
        test = your_datetime + relativedelta(months=1)
        expire = test.strftime('%Y-%m-%d')
        date = datetime.datetime.today().strftime('%Y-%m-%d')
        role = discord.utils.get(member.server.roles, name=fmRole)
        role2 = discord.utils.get(member.server.roles, name=member_role)
        await client.send_message(ctx.message.channel, f"{user} has been given a **FREE MONTH** of access.")
        embed = discord.Embed(
            title = "Free Month!",
            description = f"Hello, you have gained free access to our servers for a **MONTH**!\nBe sure to browse our server and open a ticket if you need any help. Thanks for being with us :heart:",
            color = 0xffffff
        )
        await client.send_message(user, embed=embed)
        data = {
            "id": ids,
            "start": date,
            "expiration": expire,
            member_role: "false"
        }
        with open("FREE_MONTHS.txt", 'a') as outfile:
            json.dump(data, outfile)
            outfile.write("\n")
        await client.add_roles(user, role)
        await client.add_roles(user, role2)
### FREE MONTH COMMAND END -------------------------------------------------------------------------------------------------------------- FREE MONTH COMMAND END ###

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
### START FEE CALCULATOR ----------------------------------------------------------------------------- START FEE CALCULATOR ###
@client.command(name='fee',
                description='Calculates the seller fees applied by different websites',
                pass_context=True)
async def fee_calculator(ctx, sale_price):
    # Discord channel on which command was called
    channel = ctx.message.channel
    response = feeCalc(sale_price)
    if response == "ERROR":
        await client.send_message(channel, 'Please enter a valid sale price!')
    else:
        embed = Embed(color = 0x008f00)
        embed.add_field(name='Website', value=response['websites'], inline=True)
        embed.add_field(name='Fee', value=response['fees'], inline=True)
        embed.add_field(name='Profit After Fees', value=response['profits'], inline=True)
        await client.send_message(channel, embed=embed)
### END FEE CALCULATOR ----------------------------------------------------------------------------- END FEE CALCULATOR ###    

''' Discord command to Jig a specific gmail address.
    @param ctx: Discord information
    @param email: Email to be jigged '''

### START GMAIL COMMAND ----------------------------------------------------------------------------------- START GMAIL COMMAND ###
@client.command(name='gmail',
                description='This command manipulates any gmail address passed to it as a parameter.',
                aliases=['mail', 'email'],
                pass_context=True)
async def gmail_jig(ctx, email):
    gmail = GM.GmailJig()
    emails = gmail.run(str(email))
    embed = Embed(title="TRICKED EMAILS:", description=emails, color=0xffffff)
    await client.send_message(ctx.message.author,embed=embed)
### END GMAIL COMMAND ----------------------------------------------------------------------------------- END GMAIL COMMAND ###

''' Discord command to Jig a specific residential address.
    @param ctx: Discord information
    @param adr: Residential address to be jigged ''' 
### START ADDRESS COMMAND --------------------------------------------------------------------------------- START ADDRESS COMMAND ###
@client.command(name='address',
                description='This command manipulates any residential address passed to it as a parameter.',
                aliases=['addr', 'adr'],
                pass_context=True)
async def address_jig(ctx):
    address = AddressJig()
    adr = str(ctx.message.content) 
    adr = adr.replace("!address ", "")
    response = address.generate_address_two(str(adr), ctx)
    if response == 'INVALID':
        await client.send_message(ctx.message.author,"Please enter a valid address.")
    else:
        embed = Embed(title="", color=0xff9300)
        embed.add_field(name='Jigged Addresses', value=response, inline=True)
        await client.send_message(ctx.message.author, embed=embed)
### END ADDRESS COMMAND --------------------------------------------------------------------------------- END ADDRESS COMMAND ###

''' Discord command for eBay views: limited to 200 views one command 
    @param ctx: Discord information
    @param rul: Url for item to be viewed '''
### SMS SEND COMMAND --------------------------------------------------------------------------------------------- SMS SEND COMMAND ###
@client.command(name='sendsms')
@discord.ext.commands.has_any_role("Admin","Moderator","Support")
async def send_SMS(ctx):
    message = str(ctx.message.content).replace('!sendsms ','')
    send = SMS_CLIENT.send_sms(message)
    if send == "SENT":
        await client.send_message(ctx.message.author, "MESSAGE SENT!")
    else:
        await client.send_message(ctx.message.author, "MESSAGE FAILED!")
### SMS SEND COMMAND --------------------------------------------------------------------------------------------- SMS SEND COMMAND ###

### EBAY COMMANDS --------------------------------------------------------------------------------------------- EBAY COMMANDS ###
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
                ebay = EBAY.eBay()
                _thread.start_new_thread(ebay.ebayview, (ctx, str(url),))
                embed = discord.Embed(title="", color=0xF5AF02)
                embed.add_field(name=":eyes:  Viewer started. Your views should be applied shortly. :hourglass:", value="~~~~~ {} ~~~~~".format(footer_text), inline=True)      
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
            ebay = EBAY.eBay()
            _thread.start_new_thread(ebay.ebaywatch, (str(url), int(watches),))
            await client.send_message(ctx.message.channel, 'Link watched %s times. Please wait for the watches to be applied' % (watches))
        else:
            await client.send_message(ctx.message.channel, 'The maximum number of watches allowed in one request is 20. Please try again')
    except:
        await client.send_message(ctx.message.channel, 'Error. Please contact your server admin.')
### EBAY COMMANDS --------------------------------------------------------------------------------------------- EBAY COMMANDS ###

### START SHOPIFY ACCOUNT GEN ---------------------------------------------------------------------------------------------- START SHOPIFY ACCOUNT GEN ###
''' Discord command to generate Add to Cart links for Shopify Websites.
    @param ctx: Discord information
    @param url: URL for item to be purchased '''  
@client.command(name='atc',
                description='Add To Cart command for any Shopify website. Generates a link leading the user ' +
                'straight to the payment page. Takes in the item\'s URL as a parameter',
                pass_context=True)
async def add_to_cart(ctx, url):
    await client.send_message(ctx.message.channel, ":hourglass: standby... we are generating your links.")
    info = shopify.atc_link_gen(url)
    if info['links'] == 'ERROR' or info['image'] == 'ERROR':
        await client.send_message(ctx.message.channel, "THERE WAS AN ERROR, MAKE SURE YOUR URL IS A SHOPIFY PRODUCT URL!")

    embed3 = discord.Embed(title=":shopping_cart: GENERATING LINKS FOR:", description=info['title'], color=0xffffff)
    embed3.set_thumbnail(url=info['image'])
    embed3.set_footer(icon_url="https://i.imgur.com/5fSzax1.jpg", text="Powered by FOMO | @FOMO_supply")
    await client.send_message(ctx.message.channel, embed=embed3)
    string = ''
    links = info['links']
    for link in links:
        string += str(link['Size']) + ": " + "[CART](" + link['URL'] + ")\n"
    print(string)
    embed2 = discord.Embed(title=":shopping_cart:", description=string, color=0xffffff)
    await client.send_message(ctx.message.channel, embed=embed2)

@client.command(name='shopify', pass_context=True)
async def shopifyTools(ctx):
    author = ctx.message.author
    embed = discord.Embed(title="SHOPIFY ACCOUNTE GENERATOR", description="Generate accounts on any Shopify website.", color=0xffffff)
    embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/social-media-2092/100/social-35-512.png')
    embed.add_field(name="PLEASE ENTER A SHOPIFY STORE URL", value='FOR EXAMPLE: `https://kith.com/`')
    await client.send_message(author, embed=embed)
    url = await client.wait_for_message(author=author)
    url = url.content
    check = shopify.shopify_check(url)

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
    credentials = shopify.shopify_gen(url,catchall)
    username, password = credentials.split(':')

    embed = discord.Embed(title="ACCOUNT GENERATED!", description="Generated on: `%s`" % url, color=0xffffff)
    embed.add_field(name="EMAIL:", value=username)
    embed.add_field(name="PASSWORD:", value=password, inline=False)
    embed.set_footer(icon_url=icon_img, text=footer_text)
    await client.edit_message(edit_this, embed=embed)   

''' Discord command to check if a specific website is a Shopify website
    
    @param ctx: Discord information
    @param url: URL to be checked '''  
@client.command(name='isshopify',
                description='This command uses a given URL in order to determine whether a website is a shopify site or not.',
                pass_context=True)
async def shopify_check(ctx, url):
    check = shopify.shopify_check(url)
    if check == True:
        embed = discord>embed(title=":white_check_mark: [***THE URL***]({}) __***IS***__ ***A SHOPIFY WEBSITE!***", color=0xffffff)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(ctx.message.author, embed=embed)
        #await client.send_message(ctx.message.channel, ":white_check_mark: [THE URL]({}) __**IS**__ A SHOPIFY WEBSITE!".format(url))
    elif check == False:
        embed = discord>embed(title=":no_entry_sign: [***THE URL***]({}) __***IS NOT***__ ***A SHOPIFY WEBSITE!***", color=0xffffff)
        embed.set_footer(icon_url=icon_img, text=footer_text)
        await client.send_message(ctx.message.author, embed=embed)
        #await client.send_message(ctx.message.channel, ":no_entry_sign: [THE URL]({}) __**IS NOT**__ A SHOPIFY WEBSITE!".format(url))
### END SHOPIFY TOOLS ---------------------------------------------------------------------------------------------- END SHOPIFY TOOLS ###

### START SOLEBOX ------------------------------------------------------------------------------------------------------------ START SOLEBOX
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
### END SOLEBOX -------------------------------------------------------------------------------------------------- END SOLEBOX ###

### START STRIPE AUTH --------------------------------------------------------------------------------------------- START STRIPE AUTH
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
### END STRIPE AUTH --------------------------------------------------------------------------------------------- END STRIPE AUTH
            
if __name__ == "__main__":           
    # Initialize Discord bot by making the first call to it
    try:
        db_client = pymongo.MongoClient(MONGODB_URI)
        db = db_client.get_default_database()
        subscriptions = db['subscriptions']
        subscriptions.create_index('email')
        ebay_used_urls.append(datetime.date.today())
        STRIPE = Stripe()
        KRISPYKREME = KK.KrispyKreme()
        SUCCESS_POSTER = success.SuccessPoster()
        SMS_CLIENT = SMS_CLIENT.SMS()
        client.run(TOKEN)
    except (HTTPException, LoginFailure) as e:
        client.loop.run_until_complete(client.logout())