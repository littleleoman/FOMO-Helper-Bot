import requests
import names
from bs4 import BeautifulSoup
import re
import generators as g
import random

request_url = 'https://www.solebox.com/index.php?lang=1&'
token_url = 'https://www.solebox.com/en/my-account/'
street = 'Lafayette St'
housenumber = '337'
password = 'MyPassword123'
zipcode = '10012'
country = '8f241f11096877ac0.98748826'
state = 'NY'
city = 'New York'

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36'
}

def solebox_gen(catchall):
    firstname = names.get_first_name()
    lastname = names.get_last_name()
    email = firstname + lastname + str(random.randint(100,999)) + catchall
    session = requests.session()
    token = session.get(token_url, headers=headers)
    soup = BeautifulSoup(token.text,'html.parser')
    token = str(soup.find("input",{"type":"hidden","name":"stoken"}))
    token = re.search(r'<input name=\"stoken\" type=\"hidden\" value=\"(.+)(\"\/>)', token).groups(0)[0]

    data = {
        "stoken": token,
        "lang": "1",
        "listtype": "",
        "actcontrol": "account",
        "cl": "user",
        "fnc": "createuser",
        "reloadaddress": "",
        "blshowshipaddress": "1",
        "invadr[oxuser__oxsal]": "MR",
        "invadr[oxuser__oxfname]": firstname,
        "invadr[oxuser__oxlname]": lastname,
        "invadr[oxuser__oxstreet]": street,
        "invadr[oxuser__oxstreetnr]": housenumber,
        "invadr[oxuser__oxaddinfo]": "",
        "invadr[oxuser__oxzip]": zipcode,
        "invadr[oxuser__oxcity]": city,
        "invadr[oxuser__oxcountryid]": country,
        "invadr[oxuser__oxstateid]": state,
        "invadr[oxuser__oxbirthdate][day]": random.randint(1,30),
        "invadr[oxuser__oxbirthdate][month]": random.randint(1,12),
        "invadr[oxuser__oxbirthdate][year]": random.randint(1990,2001),
        "invadr[oxuser__oxfon]": g.phonegen(),
        "lgn_usr": email,
        "lgn_pwd": password,
        "lgn_pwd2": password,
        "userform": ""
        }
    
    create = session.post(request_url, data=data, headers=headers)

    if create.status_code == 200 or 302:
        return(email + ":" + password)
    
    else:
        return("SOMETHING WENT WRONG, STATUS CODE: " + str(create.status_code))