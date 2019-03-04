import requests, json
from bs4 import BeautifulSoup

class eBay(object):
    def ebayview(self, ctx, url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'
        }
        
        count = 0
        try:
            for i in range(200):
                print(f"------- {i} -------")
                req = requests.get(url, headers=headers, verify=True, timeout=10)
                if req.status_code == 200:
                    count += 1
        except Exception as e:
            print(f"EXCEPTION ON EBAYVIEW: {e}")
    
            
            
    def ebaywatch(self, ebaylink, watches):
        account_list = open('accounts.txt', 'r')
        accountsplit = account_list.read().splitlines()
        for x in range (0, watches):
            accountpuller = accountsplit[x]
            s = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            r = s.get('https://signin.ebay.com/ws/eBayISAPI.dll?SignIn&ru=https%3A%2F%2Fwww.ebay.com%2F', headers=headers).content
            soup = BeautifulSoup(r, 'lxml')

            f = soup.find('input', attrs={'id': 'rqid', 'name': 'rqid'})
            rqid = f['value']

            f = soup.find('script', attrs={'type': 'text/javascript', 'id': 'dfpDetails'})
            js = f.find(text=True)
            jsonValue = '{%s}' % (js.partition('{')[2].rpartition('}')[0],)
            value = json.loads(jsonValue)
            mid = value['mid']

            f = soup.find('input', attrs={'type': 'hidden', 'name': 'srt'})
            srt = f['value']
        
            payload = {
                'AppName': '',
                'errmsg': '', 
                'fypReset': '', 
                'htmid': '',
                'i1': '', 
                'ICurl': '', 
                'keepMeSignInOption2': 'on', 
                'lkdhjebhsjdhejdshdjchquwekguid': rqid,
                'mid':  mid,
                'pageType': '-1',
                'pass': 'sonarbot1',
                'returnUrl': 'https://www.ebay.com/',
                'rqid': rqid,
                'rtmData': '',
                'src': '',
                'srcAppId': '',
                'srt': srt,
                'tagInfo': '',
                'userid': accountpuller,
                'usid': rqid
                }

            r = s.post('https://www.ebay.com/signin/s', headers=headers, data=payload).content
   
            r = s.get('https://www.ebay.com/', headers=headers)
            r = s.get(str(ebaylink), headers=headers).content

            soup = BeautifulSoup(r, 'lxml')
            f = soup.find('a', attrs={'id': 'watchLink', 'rel': 'nofollow'})
            link = f['href']
            print(link)
    
            r = s.get(link, headers=headers)
            print('watched')