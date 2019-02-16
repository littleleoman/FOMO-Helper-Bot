import random
import names
import string

catchall = '@fomo.host'

def phonegen():
    number = '0000000000'
    while '9' in number[3:6] or number[3:6]=='000' or number[6]==number[7]==number[8]==number[9]:
        number = str(random.randint(10**9, 10**10-1))
    return number[:3] + '-' + number[3:6] + '-' + number[6:]
    

def namegen():
    global firstname
    global lastname
    firstname = names.get_first_name()
    lastname = names.get_last_name()
    return firstname + ' ' + lastname

def catchallgen():
    global catchall
    for x in range(4):
        number1 = random.randint(1,10)
        number2 = random.randint(1,10)
        number3 = random.randint(1,10)
        number4 = random.randint(1,10)
    prefix = firstname
    email_total = prefix + str(number1) + str(number2) + str(number3) + str(number4) + catchall
    return email_total

def instagram():
    for x in range(2):
        number1 = random.randint(1,10)
        number2 = random.randint(1,10)
    igusername = '@' + firstname + str(number1) + str(number2)
    return igusername

def plusjig(gmail):
    num1 = int(random.randrange(0,10))
    num2 = int(random.randrange(0,10))
    num3 = int(random.randrange(0,10))
    num4 = int(random.randrange(0,10))
    num5 = int(random.randrange(0,10))
    num6 = int(random.randrange(0,10))
    plusjig = str(num1) + str(num2) + str(num3) + str(num4) + str(num5) + str(num6)
    return gmail + '+' + plusjig + '@gmail.com'

def addressjigline1(address):
    code = ''
    for i in range(0,4):
        code += random.choice(string.ascii_uppercase)
    address1 = code + ' ' + address
    return address1

def addressjigline2():
    address_options = ['Apt', 'Apartment', 'Building', 'Bldg', 'Suite', 'Room', 'Condo', 'Unit']
    for i in range(1,16):
        index = random.randint(0, len(address_options)-1)
        address_2 = address_options[index]
        num = 0
        if address_2 == 'Unit':
            num = random.randint(5, 100)
        else:
            num = random.randint(15, 500)
    return address_2 + ' ' + str(num)
