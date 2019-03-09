from twilio.rest import Client
import json, asyncio, pymongo, os
from twilio.base.exceptions import TwilioRestException

with open ('config.json','r') as output:
    userInfo = json.load(output)
class SMS(object):
    
    def __init__(self):
        self.from_ = userInfo['twilio_from']
        self.account_sid = userInfo['twilio_sid']
        self.auth_token = userInfo['twilio_auth_token']
        self.sms_client = Client(self.account_sid, self.auth_token)
        self.sms_db_client = pymongo.MongoClient(os.environ['MONGODB_URI'])
        self.sms_db = self.sms_db_client.get_database()
        self.posts = self.sms_db.sms_messages

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
        db_check = self.posts.find({'discord_id':discord_id}).count()
        if db_check == 0:
            if '+' in number:
                validate = await self.is_valid_number(number)
                if validate == True:
                    new_user = dict()
                    new_user['discord_id'] = discord_id 
                    new_user['number_+'] = number 
                    new_user['number'] = number.replace('+','')
                    new_post = self.posts.insert_one(new_user).inserted_id
                    response = dict()
                    response['number'] = new_user['number_+']
                    response['result'] = 'SUCCESS'
                    response['status'] = 'NEW'
                    return(response)
                elif validate == False:
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
            response = dict()
            response['result'] = 'DUPLICATE'
            return(response)
        else:
            return({'result':'NOT_MEMBER'})
                           
    async def check_user(self, discord_id):
        db_check = self.posts.find({'discord_id':discord_id}).count()
        if db_check > 0:
            user = self.posts.find_one({'discord_id': discord_id})
            response = dict()
            response['number'] = user['number_+']
            response['result'] = 'SUCCESS'
            return(response)
        elif db_check == 0:
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
                response = dict()
                response['number'] = user['number_+']
                response['result'] = 'SUCCESS'
                return(response)
            elif db_check == 0:
                response = {'result':'FAILED','number':'INVALID'}
                return(response)
            else:
                response = {'result':'FAILED'}
                return(response)
        
    async def remove_user(self, discord_id):
        db_check = self.posts.find({'discord_id':discord_id}).count()
    
        if db_check == 0:
            response = {"DELETED":"FALSE"}
            return(response)
        elif db_check > 0:
            user = self.posts.find_one({'discord_id':discord_id})
            self.posts.delete_one(user)
            return({"DELETED":"TRUE"})

    async def send_sms(self, message):
        notification = self.sms_client.notify.services(userInfo['twilio_service_id']).notifications.create(
            to_binding=[
                "{\"binding_type\":\"sms\",\"address\":\"+15555555555\"}"
            ],
            body = ""
        )
        numbers_list = []
        users = self.posts.find({})
        msg = message.replace('!sendsms ', '')
        for user in users:
            number = user['number_+']
            numbers_list.append("{\"binding_type\":\"sms\",\"address\":\"" + number + "\"}")
        notification = self.sms_client.notify.services(userInfo['twilio_service_id']).notifications.create(
            to_binding=numbers_list,
            body = msg
        )
        print(notification)
            # try:
            #     sms_message = self.sms_client.messages.create(
            #         to=number,
            #         from_=userInfo['twilio_number'],
            #         body=msg)
            #     if "queued" or "sent" or "delivered" in sms_message.status:
            #         print("SMS SENT: " + sms_message.status)
            # except:
            #     print("ERROR SENDING SMS: " + sms_message.status + ": " + number)
       
            # if "queued" or "sent" or "delivered" in sms_message.status:
            #     print("SMS SENT: " + sms_message.status)
            # else:
            #     print("ERROR SENDING SMS: " + sms_message.status)
        return("FINISHED")
        
