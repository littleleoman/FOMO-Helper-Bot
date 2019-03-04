import random, requests, names
from bs4 import BeautifulSoup

class KrispyKreme(object):
    
    def __init__(self, ):
        self.headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'}
        self.uk_signup = 'https://friends.krispykremerewards.co.uk/Friends/SignUp/SignUp.aspx?ChannelSource=Website&InputSource=Direct'
        self.password = 'MyPassword123'
        
    def plus_jig(self, gmail):
        num1 = int(random.randrange(0,10))
        num2 = int(random.randrange(0,10))
        num3 = int(random.randrange(0,10))
        num4 = int(random.randrange(0,10))
        num5 = int(random.randrange(0,10))
        num6 = int(random.randrange(0,10))
        plusjig = str(num1) + str(num2) + str(num3) + str(num4) + str(num5) + str(num6)
        return gmail + '+' + plusjig + '@gmail.com'
    
    def krispykreme_uk(self, email):
        gmail = self.plus_jig(email) 
        session = requests.session()
        tokens = requests.get(self.uk_signup, headers=self.headers) 
        soup = BeautifulSoup(tokens.text, 'html.parser')
        
        viewstate = str(soup.find("input", {"type":"hidden", "name":"__VIEWSTATE"}, tokens.text))
        viewstate = viewstate.replace('<input id="__VIEWSTATE" name="__VIEWSTATE" type="hidden" value="','')
        viewstate = viewstate.replace('"/>','')
        
        viewstategenerator = str(soup.find("input",{"type":"hidden","name":"__VIEWSTATEGENERATOR"}, tokens.text))
        viewstategenerator = viewstategenerator.replace('<input id="__VIEWSTATEGENERATOR" name="__VIEWSTATEGENERATOR" type="hidden" value="','')
        viewstategenerator = viewstategenerator.replace('"/>','')
        
        eventvalidation = str(soup.find("input",{"type":"hidden","name":"__EVENTVALIDATION"}, tokens.text))
        eventvalidation = eventvalidation.replace('<input id="__EVENTVALIDATION" name="__EVENTVALIDATION" type="hidden" value="','')
        eventvalidation = eventvalidation.replace('"/>','')
    
        formdata1 = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "ctl00$ContentPlaceHolder1$wucSignInStep1$txtFName": names.get_first_name(),
            "ctl00$ContentPlaceHolder1$wucSignInStep1$txtLName": names.get_last_name(),
            "ctl00$ContentPlaceHolder1$wucSignInStep1$txtCorreo": gmail,
            "ctl00$ContentPlaceHolder1$wucSignInStep1$ChkConsentKK": "on",
            "ctl00$ContentPlaceHolder1$wucSignInStep1$cboDondeCompra": "1",
            "ctl00$ContentPlaceHolder1$wucSignInStep1$ChkAcceptEmail": "on",
            "ctl00$ContentPlaceHolder1$btnPaso1Next": "NEXT",
            "ctl00$ContentPlaceHolder1$HiddenField1": "False",
            "ctl00$ContentPlaceHolder1$hidSocioID": "",
            "ctl00$ContentPlaceHolder1$hidUsuarioIDFb": "",
            "ctl00$ContentPlaceHolder1$txtPreferencias": ""
        }
    
        submit1 = session.post(self.uk_signup, headers=self.headers, data=formdata1)
        soup = BeautifulSoup(submit1.text, 'html.parser')
        
        viewstate = str(soup.find("input",{"type":"hidden","name":"__VIEWSTATE"}, tokens.text))
        viewstate = viewstate.replace('<input id="__VIEWSTATE" name="__VIEWSTATE" type="hidden" value="','')
        viewstate = viewstate.replace('"/>','')
    
        viewstategenerator = str(soup.find("input",{"type":"hidden","name":"__VIEWSTATEGENERATOR"}, tokens.text))
        viewstategenerator = viewstategenerator.replace('<input id="__VIEWSTATEGENERATOR" name="__VIEWSTATEGENERATOR" type="hidden" value="','')
        viewstategenerator = viewstategenerator.replace('"/>','')
        
        eventvalidation = str(soup.find("input",{"type":"hidden","name":"__EVENTVALIDATION"}, tokens.text))
        eventvalidation = eventvalidation.replace('<input id="__EVENTVALIDATION" name="__EVENTVALIDATION" type="hidden" value="','')
        eventvalidation = eventvalidation.replace('"/>','')
    
        socioid = str(soup.find("input",{"type":"hidden","name":"ctl00$ContentPlaceHolder1$hidSocioID"}, submit1.text))
        socioid = socioid.replace('<input id="ContentPlaceHolder1_hidSocioID" name="ctl00$ContentPlaceHolder1$hidSocioID" type="hidden" value="','')
        socioid = socioid.replace('"/>','')
    
        formdata2 = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "ctl00$ContentPlaceHolder1$wucSignInStep2$fechaNacimiento$ddlDia": "7",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$fechaNacimiento$ddlMes": "7",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$fechaNacimiento$ddlAnio": "1998",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$wucCP$txtCP": "G41 4PY",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$wucCP$txtContry": "City of Glasgow",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$wucCP$txtCityTwon": "Glasgow",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$wucCP$hidPaginaPadre": "SignUp.aspx",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$ctl00$cboListaDatos": "2",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$wucGpoDondeCompra$ChkPreferencia_10": "on",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$ctl01$cboListaDatos": "-""1",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$txtNumeroTjta": "",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$txtRegCode": "",
            "ctl00$ContentPlaceHolder1$wucSignInStep2$txtPass": self.password,
            "ctl00$ContentPlaceHolder1$wucSignInStep2$txtConfirmPass": self.password,
            "ctl00$ContentPlaceHolder1$wucSignInStep2$chkTC": "on",
            "ctl00$ContentPlaceHolder1$btnConfirm": "CONFIRM",
            "ctl00$ContentPlaceHolder1$HiddenField1": "False",
            "ctl00$ContentPlaceHolder1$hidSocioID": socioid,
            "ctl00$ContentPlaceHolder1$hidUsuarioIDFb": "",
            "ctl00$ContentPlaceHolder1$txtPreferencias": ",10_ChkPreferencia,null"
        }
    
        submit2 = session.post(self.uk_signup, headers=self.headers, data=formdata2)
        if submit2.status_code == 200:
            session.close()
            return gmail
        if submit2.status_code != 200:
            session.close()
            return("Request Failed")
