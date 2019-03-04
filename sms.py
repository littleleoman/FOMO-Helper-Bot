from twilio.rest import Client
import json, asyncio, pymongo
from twilio.base.exceptions import TwilioRestException

with open ('config.json','r') as output:
    userInfo = json.load(output)
class SMS(object):
    
    def __init__(self):
        self.from_ = userInfo['twilio_from']
        self.account_sid = userInfo['twilio_sid']
        self.auth_token = userInfo['twilio_auth_token']
        self.sms_client = Client(self.account_sid, self.auth_token)
        self.sms_db_client = pymongo.MongoClient(userInfo['mongo_sms_url'])
        self.sms_db = self.sms_db_client.get_database()
        self.posts = self.sms_db.posts

    async def is_valid_number(self, number):
        twilio_client = Client(self.account_sid, self.auth_token)
        try:
            response = twilio_client.lookups.phone_numbers(number).fetch()
            return True
        except TwilioRestException as e:
            if e.code == 20404:
                return False
            else:
                raise e
    async def add_user(self, discord_id, number):
        #server = client.get_server(server_id)
        #author = message.author
        db_check = self.posts.find({'discord_id':discord_id}).count()
        #member = server.get_member(discord_id) 
            
        #if member_role or 'Moderator' or 'Admin' in [role.name for role in member.roles]:
            # If user isn't in the database, check if the entered number was entered with a + sign before it
        if db_check == 0:
            # Add number to the database if it is correct
            if '+' in number:
                validate = await self.is_valid_number(number)
                if validate == True:
                    new_user = dict()
                    new_user['discord_id'] = discord_id 
                    new_user['number_+'] = number 
                    new_user['number'] = number.replace('+','')
                    new_post = self.posts.insert_one(new_user).inserted_id
                #embed = Embed(title="SUCCESS!", description="You have been added to the database.", color=0xffffff)
                #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                #embed.add_field(name="Number on File:", value=new_user['number_+'])
                #embed.set_footer(icon_url=icon_img, text=footer_text)
                    response = dict()
                    response['number'] = new_user['number_+']
                    response['result'] = 'SUCCESS'
                    response['status'] = 'NEW'
                    return(response)
                elif validate == False:
                    #embed = Embed(title="FAILED", description="Make sure you format your number correctly", color=0xffffff)
                    #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                    #embed.add_field(name="FOR EXAMPLE:", value="sms!add +13058554140")
                    #embed.set_footer(icon_url=icon_img, text=footer_text)
                    #await client.send_message(author, embed=embed)
                    response = dict()
                    response['result'] = 'FAILED'
                    response['status'] = 'INVALID NUMBER'
                    return(response)
            else:
                response = dict()
                response['result'] = 'FAILED'
                response['status'] = 'INVALID NUMBER'
                return(response)
        elif db_check > 0:
            #user = self.posts.find_one({'discord_id':author.id})
            #embed = Embed(title="FOUND!", description="You are already in the database.", color=0xffffff)
            #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            #embed.add_field(name="TO UPDATE YOUR NUMBER, SAY:", value="sms!update")
            #embed.set_footer(icon_url=icon_img, text=footer_text)
            response = dict()
            #await client.send_message(author, embed=embed)
            response['result'] = 'DUPLICATE'
            return(response)
        else:
            #embed = Embed(title="NOT A MEMBER", description="You must be a paying member to access this feature.", color=0xffffff)
            #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            #embed.set_footer(icon_url=icon_img, text=footer_text)
            #await client.send_message(author, embed=embed)
            return({'result':'NOT_MEMBER'})
                           
    async def check_user(self, discord_id):
        #server = client.get_server(server_id)
        #author = message.author
        #member = server.get_member(author.id)
        db_check = self.posts.find({'discord_id':discord_id}).count()
    
        #if member_role or 'Moderator' or 'Admin' in [role.name for role in member.roles]:
        if db_check > 0:
            user = self.posts.find_one({'discord_id': discord_id})
            #embed = Embed(title="FOUND!", description="You were found in the database.", color=0xffffff)
            #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            #embed.add_field(name="TO UPDATE YOUR NUMBER ON FILE, SAY:", value="sms!update")
            #embed.set_footer(icon_url=icon_img, text=footer_text)
            #await client.send_message(author, embed=embed)
            response = dict()
            response['number'] = user['number_+']
            response['result'] = 'SUCCESS'
            return(response)
        elif db_check == 0:
            #embed = Embed(title="NOT FOUND!", description="You were not found in the database.", color=0xffffff)
            #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            #embed.add_field(name="TO ADD YOUR NUMBER, SAY:", value="sms!add followed by your number with the country & area code.")
            #embed.set_footer(icon_url=icon_img, text=footer_text)
            #await client.send_message(author, embed=embed)
            response = dict()
            response['number'] = 'NONE'
            response['result'] = 'FAILED'
            return(response)
        '''else:
            embed = Embed(title="NOT A MEMBER", description="You must be a paying member to access this feature.", color=0xffffff)
            embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            embed.set_footer(icon_url=icon_img, text=footer_text)
            await client.send_message(author, embed=embed)'''
            
    async def update_user(self, discord_id, number):
        #server = client.get_server(server_id)
        #author = message.author
        #member = server.get_member(author.id)
    
        #if member_role or 'Moderator' or 'Admin' in [role.name for role in member.roles]:
        if '+' in number:
            number_plus = number
            number_noplus = number.replace('+','')
            db_check = self.posts.find({'discord_id':discord_id}).count()
            validate = await self.is_valid_number(number_plus)
            if validate == True and db_check > 0:
                self.posts.update_one({
                    'discord_id': discord_id
                    }, {
                        '$set': {
                            'number_+':number_plus,
                            'number':number_noplus
                        }
                })
                user = self.posts.find_one({'discord_id': discord_id})
                #embed = Embed(title="SUCCESS!", description="Your number on file was updated.", color=0xffffff)
                #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                #embed.add_field(name="NUMBER ON FILE:", value=user['number_+'])
                #embed.set_footer(icon_url=icon_img, text=footer_text)
                #await client.send_message(author, embed=embed)
                response = dict()
                response['number'] = user['number_+']
                response['result'] = 'SUCCESS'
                return(response)
            elif db_check == 0:
                #embed = Embed(title="NOT FOUND!", description="You were not found in the database.", color=0xffffff)
                #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
                #embed.add_field(name="LEARN MORE BY SAYING:", value="sms!help")
                #embed.set_footer(icon_url=icon_img, text=footer_text)
                response = {'result':'FAILED'}
                return(response)
            else:
                response = {'result':'FAILED'}
                return(response)
        
    async def remove_user(self, discord_id):
        #server = client.get_server(server_id)
        #author = message.author
        #member = server.get_member(author.id)
    
        db_check = self.posts.find({'discord_id':discord_id}).count()
    
        if db_check == 0:
            #embed = Embed(title="NOT FOUND!", description="You were not found in the database.", color=0xffffff)
            #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            #embed.add_field(name="LEARN MORE BY SAYING:", value="sms!help")
            #embed.set_footer(icon_url=icon_img, text=footer_text)
            response = {"DELETED":"FALSE"}
            return(response)
        elif db_check > 0:
            user = self.posts.find_one({'discord_id':discord_id})
            self.posts.delete_one(user)
            #embed = Embed(title="REMOVED", description="You will no longer receive SMS alerts.", color=0xffffff)
            #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            #embed.add_field(name="LEARN MORE BY SAYING:", value="sms!help")
            #embed.set_footer(icon_url=icon_img, text=footer_text)
            #await client.send_message(author, embed=embed)
            return({"DELETED":"TRUE"})

    async def send_sms(self, message):
        #server = client.get_server(server_id)
        #author = message.author
        #member = server.get_member(author.id)
    
        #if member.server_permissions.administrator:
        users = self.posts.find({})
        msg = str(message.content)
        msg = msg.replace('sms!send ', '')
        for user in users:
            number = user['number_+']
            sms_message = self.sms_client.messages.create(
                to=number,
                from_=userInfo['twilio_number'],
                body=msg)
            
            if "queued" or "sent" or "delivered" in sms_message.status:
                print("SMS SENT: " + sms_message.status)
                return("SENT")
            else:
                print("ERROR SENDING SMS: " + sms_message.status)
                return("FAILED")
        #else:
            #embed = Embed(title="NOT A STAFF MEMBER", description="You must be a moderator/admin to use this command.", color=0xffffff)
            #embed.set_thumbnail(url='https://cdn0.iconfinder.com/data/icons/apple-apps/100/Apple_Messages-512.png')
            #embed.set_footer(icon_url=icon_img, text=footer_text)
            #await client.send_message(author, embed=embed)


