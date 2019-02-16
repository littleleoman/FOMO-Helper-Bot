# THINGS LEFT:
# -ADD MORE IF/ELIF/ELSE STATEMENTS TO MAKE IT
# THE CODE FLOW BETTER & CHECK FOR ERRORS/TIMEOUTS

import names
import random
import requests
from python_anticaptcha import AnticaptchaClient, NoCaptchaTaskProxylessTask
from bs4 import BeautifulSoup
import re
import os

headers = {
    'Upgrade-Insecure-Requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'
}

password = 'MyPassword123'
captcha_api = os.environ["CAPTCHA_API"]

def shopify_check(website):
    if website.endswith('/') == False:
        website = website + '/admin'
    else:
        website = website + 'admin'
    
    check = requests.get(website)

    if 'shopify' in check.text:
        return True
    else:
        return False
    
    

def find_auth_token(website):
    soup = BeautifulSoup(website,"lxml")
    return [token['value'] for token in soup.findAll('input', {'name':'authenticity_token'})]

def shopify_gen(website, email):

    #if shopify_check(website) == False:
    #   return "ERROR, NOT A VALID SHOPIFY URL"

    firstname = names.get_first_name()
    lastname = names.get_last_name()
    randomnums = random.randint(100,2000)

    email = firstname +lastname + str(randomnums) + email
    data = {
        "form_type": "create_customer",
        "utf8": "",
        "customer[first_name]": firstname,
        "customer[last_name]": lastname,
        "customer[email]": email,
        "customer[password]": password
    }

    if website.endswith('/') == False:
        account_url = website + '/account'
        challenge_url = website + '/challenge'
    else:
        account_url = website + 'account'
        challenge_url = website + 'challenge'
        pass
    
    session = requests.session()
    submit_account = session.post(account_url, data=data, headers=headers)

    if submit_account.url == challenge_url:
        print("CAPTCHA REQUESTED, PLEASE WAIT...\n")
        sitekey = '6LeoeSkTAAAAAA9rkZs5oS82l69OEYjKRZAiKdaF'
        captcha_url = website
        api_key = captcha_api

        client = AnticaptchaClient(api_key)
        task = NoCaptchaTaskProxylessTask(captcha_url, sitekey)
        job = client.createTask(task)
        job.join()
        captoken = job.get_solution_response()
        auth_token = find_auth_token(submit_account.text)

        captcha_data = {
            'utf-8':"",
            'authenticity_token':auth_token,
            'g-recaptcha-response':captoken
        }

        submit_captcha = session.post(account_url,data=captcha_data,headers=headers,verify=False)

        if submit_captcha.status_code == 200 or 302 and submit_captcha.url != challenge_url:
            return(email + ":" + password)
        else:
            return("ERROR")

    else:
        return(email + ":" + password)