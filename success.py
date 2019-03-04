import twitter
import json

with open('config.json') as output:
    userInfo = json.load(output)


class SuccessPoster(object): 
    
    def __init__(self):
        self.consumer_key = userInfo['twitter_consumer_key']
        self.consumer_secret = userInfo['twitter_consumer_secret']
        self.access_token = userInfo['twitter_access_token']
        self.access_token_secret = userInfo['twitter_access_secret']
        self.twitter_api = twitter.Api(consumer_key=self.consumer_key,
                                       consumer_secret=self.consumer_secret,
                                       access_token_key=self.access_token,
                                       access_token_secret=self.access_token_secret)
        
    def success_poster(self, author, image_url):
        status = self.twitter_api.PostUpdate(f'Success by {author}', media=image_url)