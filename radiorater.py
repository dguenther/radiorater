## 
## animenfo rating bot
##
## Last Updated: 05-03-2011
## Version 1
##
## future improvements:
## add songs to favorites
## request songs that haven't been voted for yet
## lot of error-handling missing
##

from BeautifulSoup import BeautifulSoup
import ConfigParser
import mechanize
import urllib
import random
import sys
import time

# read configuration file

# need to implement creating configuration file if it doesn't exist
defaults = {'cookie-file':'cookies.dat',
            'song-url':'https://www.animenfo.com/radio/nowplaying.php?ajax=true&mod=playing',
            'user-agent':'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.8) Gecko/20100723 Ubuntu/10.04 (lucid) Firefox/3.6.8'
            }
config = ConfigParser.SafeConfigParser(defaults)
config.read('settings.cfg')

# set up constants from config file
USER_AGENT = config.get('general','user-agent')
COOKIE_FILE = config.get('general','cookie-file')
SONG_URL = config.get('site-specific','song-url')
USERNAME = config.get('site-specific','username')
PASSWORD = config.get('site-specific','password')
if (USERNAME == '' or PASSWORD == ''):
    print 'Error: No username or password specified. Check settings.cfg'
    sys.exit(0)

# initialize browser
br = mechanize.Browser(factory=mechanize.RobustFactory())

# initialize cookie jar
cj = mechanize.LWPCookieJar(COOKIE_FILE)
try:
    cj.revert()
except:
    cj.save()
br.set_cookiejar(cj)

# change useragent to useragent constant
br.addheaders = [('User-agent',USER_AGENT)]

#debug messages
#br.set_debug_http(True)
#br.set_debug_redirects(True)
#br.set_debug_responses(True)

def login():
    values = {'frompage':'index.php',
            'username':USERNAME,
            'password':PASSWORD
            }
    data = urllib.urlencode(values)
    br.open("https://www.animenfo.com/radio/login.php", data)
    # want to add some kind of handler if login fails
    cj.save()

def getStdDev(rates):
    ''' Determines a standard deviation for rating based on the number of people
        who have already rated a song '''
    # wouldn't mind finding a smoother way to do this, maybe some sort of
    # exponential curve
    if rates == 0:
        return 1.5
    elif rates < 100:
        return 1
    elif rates < 1000:
        return 0.75
    else:
        return 0.5

def generateRating(currentRating, rates):
    try:
        rating = float(currentRating)
    except:
        rating = 5.0
    stdDev = getStdDev(float(rates))
    myRating = int(round(random.gauss(rating, stdDev)))
    if myRating > 10:
        return 10
    if myRating < 1:
        return 1
    else:
        return myRating

def formatOutput(text):
    data = ''.join(text.findAll(text=True)).partition('favourites')
    data = (data[0]+data[1]).strip()
    data = data.replace('\t\t\t\t','')
    return data

while(True):
    totalSeconds = 0
    # 28800 seconds = 8 hours
    while(totalSeconds < 28800):
        br.open(SONG_URL)
        try:
            br.select_form(nr=0)
        except:
            # if a form can't be selected, the browser isn't logged in
            login()
            br.open(SONG_URL)
            br.select_form(nr=0)
        soup = BeautifulSoup(br.response().read())
        span = soup.find(attrs={'id' : 'np_timer'})
        seconds = int(span['rel'])
        if seconds <= 45:
            # if <= 30, rate and set timer to timer + ~10
            rateText = soup.find(attrs={'id' : 'rateform'})
            rateText = rateText.contents[4].strip()
            items = soup.findAll('td', limit=2)
            text = items[1]
            if (rateText.find('Change your rating for this song:') == -1):
                rating = text.contents[12].strip().strip('Rating: ')
                currentRating = rating.split('/', 1)[0]
                rates = rating.split('rate', 1)[0]
                rates = rates.split('(')[1]

                myRating = generateRating(currentRating, rates)
                print formatOutput(text)
                print 'My Rating: %d' % myRating
                
                br['rating'] = [str(myRating)]
                br.submit()
            else:
                print formatOutput(text)
                print 'Already rated this song: %s' % br['rating'][0]
            seconds = seconds + random.randint(5,15)
            print 'Sleeping for %d seconds...' % (seconds)
            time.sleep(seconds)
        else:
            # if > 30, set timer to timer - ~20
            seconds = seconds - random.randint(15,45)
            print 'Sleeping for %d seconds...' % (seconds)
            time.sleep(seconds)
        totalSeconds += seconds
    # 86400 seconds = 24 hours
    sleepTime = 86400 - totalSeconds
    print 'Sleeping for %d hours...' % (sleepTime / 3600)
    time.sleep(sleepTime)

