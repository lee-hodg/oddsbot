#!/usr/bin/python

from requests import Session
from Bookies.spiders.Betvictor_script import process_script
import urllib #urlencoding
session = Session()

# HEAD requests ask for *just* the headers, which is all you need to grab the
# session cookie
#session.head('http://www.betvictor.com/sports/en/football')
#r=session.get('http://www.betvictor.com/sports/en/football')


"""
value = process_script(r)
value=str(value.strip())
print '\033[7m Value: \033[33m %s \033[0m' % value

"""

#curl  'http://www.betvictor.com/sports/en/football'
# -H 'User-Agent: Mozilla/5.0 (Windows; U; Windows NT 5.1; pt-BR) AppleWebKit/534.8 (KHTML, like Gecko) Navscape/Pre-0.2 Safari/534.8' 
#--data 'TS644333_id=3&TS644333_75=d92091cb378b059b47b17edaf45fd3ce:vyxz:Cxj3C9cb:1111348890&TS644333_md=1&TS644333_rf=0&TS644333_ct=0&TS644333_pd=0' --compressed

http_proxy  = "127.0.0.1:9999"
https_proxy  = "127.0.0.1:9999"
ftp_proxy  = "127.0.0.1:9999"

proxyDict = { 
              "http"  : http_proxy, 
              "https" : https_proxy, 
              "ftp"   : ftp_proxy
            }


value='37f104d3c3f9c323b8966f683114b7e2:hkhj:9SVLFBpk:996972615'
#POSTstr = "TS644333_id=3&TS644333_75=7a8b924dcf5f791d1dae6e246b5433bd%3Akijj%3A6K812H5v%3A1137271628&TS644333_md=1&TS644333_rf=0&TS644333_ct=0&TS644333_pd=0"
POSTstr = "TS644333_id=3&TS644333_75="
POSTstr+= urllib.quote_plus(value)
POSTstr+="&TS644333_md=1&TS644333_rf=0&TS644333_ct=0&TS644333_pd=0"

#FINAL / super important!!!
#Actually just a loop hole.
#real server verifcation should work without
#using POSTstr to maintain order (just incase)
#and using Content-Type: application/x-www-form-urlencoded is essential
#seems to fix things.
response = session.post(
     url='http://www.betvictor.com/sports/en/football',
     data=POSTstr,
#    data={
#          'TS644333_id':'3',
#          'TS644333_75':'7a8b924dcf5f791d1dae6e246b5433bd:kijj:6K812H5v:A1137271628',
#          'TS644333_md':'1',
#          'TS644333_rf':'0',
#          'TS644333_ct':'0',
#          'TS644333_pd':'0'
#        },
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
    proxies=proxyDict
)

print response.text

