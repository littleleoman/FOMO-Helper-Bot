# THINGS LEFT:
# -ADD MORE IF/ELIF/ELSE STATEMENTS TO MAKE IT
# THE CODE FLOW BETTER & CHECK FOR ERRORS/TIMEOUTS

import names
import random
import requests
from imagetyperzapi3.imagetyperzapi import ImageTyperzAPI
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import os
import json

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
    parse = urlparse(website)
    if parse.scheme == '':
        website = 'https://' + website
    elif parse.scheme == 'http://':
        website = website.replace('http://','https://')
    check = requests.get(website)
    if 'shopify' in check.text:
        return({"status":"TRUE","URL":website})
    elif 'shopify' not in check.text:
        return({"status":"FALSE","URL":website})

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
        ita = ImageTyperzAPI(captcha_api)      # init imagetyperz api obj
        
        recaptcha_params = {
            'page_url' : captcha_url,
            'sitekey' : sitekey,
            'type' : 1,                     # optional, 1 - normal recaptcha, 2 - invisible recaptcha, 3 - v3 recaptcha, default: 1
        }
        
        auth_token = find_auth_token(submit_account.text)

        captcha_data = {
            'utf-8':"",
            'authenticity_token':auth_token,
            'g-recaptcha-response':captoken
        }
        captcha_id = ita.submit_recaptcha(recaptcha_params)
        while ita.in_progress():    # while it's still in progress
            print("Waiting for Captcha...")
	    sleep(10)               # sleep for 10 seconds and recheck
        recaptcha_response = ita.retrieve_recaptcha(captcha_id)           # captcha_id is optional, if not given, will use last captcha id submited
        print ('Recaptcha response: {}'.format(recaptcha_response)) 
        
        submit_captcha = session.post(account_url,data=captcha_data,headers=headers,verify=False)

        if submit_captcha.status_code == 200 or 302 and submit_captcha.url != challenge_url:
            return(email + ":" + password)
        else:
            return("ERROR")

    else:
        return(email + ":" + password)

def atc_link_gen(product):
    productURL = re.search(r'^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/\n]+)', product)
    # STORE DOMAIN
    productURL = str(productURL.group(0))
    # STORE JSON
    productData = product + '.json'
    # STORE CART URL
    productCart = productURL + '/cart/'
    
    session = requests.session()
    data = session.get(productData)
    if data.status_code != 200:
        return "ERROR"
    data = json.loads(data.text)
    variants = data['product']['variants']
    picture = data['product']['images'][0]['src']
    title = data['product']['title']
    img = picture.replace('\\','')
    linkParts = list()
    for variant in variants:
        link = dict()
        link['id'] = variant['id']
        link['size'] = variant['title']
        linkParts.append(link)
    links = list()
    for linkPart in linkParts:
        link = dict()
        link['URL'] = productCart + str(linkPart['id']) + ":1"
        link['URL'] = tiny(link['URL'])
        link['Size'] = linkPart['size']
        links.append(link)
    info = dict()
    info['links'] = links
    info['image'] = img
    info['title'] = title
    return(info)

def tiny(url):
    URL = "https://tinyurl.com/create.php?source=indexpage&url=" + url + "&submit=Make+TinyURL%21&alias="
    raw_HTML = requests.get(URL, timeout=10)
        
    if raw_HTML.status_code != 200:
        return None
    else:
        page = BeautifulSoup(raw_HTML.text, 'lxml')
        return page.find_all('div', {'class': 'indent'})[1].b.string   
