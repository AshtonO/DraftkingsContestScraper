import requests
from pycookiecheat import chrome_cookies
import globalVariables

url = 'http://draftkings.com'


if len(globalVariables.COOKIE_FILE_PATH) > 0:
    cookies = chrome_cookies(url, cookie_file = globalVariables.COOKIE_FILE_PATH)
else:
    cookies = chrome_cookies(url, )

if len(cookies) == 0:
    print "Error finding your draftkings cookies from chrome.  Make sure you're logged into Draftkings.com on chrome.  If you've already done this, then you may need to set the cookie file path in globalVariables.py"
else:
    session = requests.session()
    session.cookies.update(cookies)

def getSession():
    return session
