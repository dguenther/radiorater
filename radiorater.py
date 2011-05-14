## 
## animenfo rating bot
##
## Last Updated: 05-03-2011
## Version 1
##
## future improvements:
## add songs to favorites
## request songs that haven't been voted for yet
## use datetime instead of counting seconds to determine 8-hour periods
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

def safeOpen(url, data=None):
    ''' Retry opening URL until it is successful'''
    success = False
    while success == False:
        try:
            if data == None:
                br.open(url)
            else:
                br.open(url,data)
            success = True
        except:
            # if url opening fails, sleep for 3 seconds
            success = False
            time.sleep(3)

def login():
    values = {'frompage':'index.php',
            'username':USERNAME,
            'password':PASSWORD
            }
    data = urllib.urlencode(values)
    safeOpen("https://www.animenfo.com/radio/login.php", data)
    # TODO: add some kind of handler if login fails
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

def favoriteSong():
    if (findMechanizeLinkById('np_delfav') == None):
        favoriteLink = findMechanizeLinkById('np_addfav')
        if (favoriteLink != None):
            br.follow_link(favoriteLink)
            br.back()
            print "Added this song to favorites."
        else:
            print "Unable to favorite song - no favorites links detected."
    else:
        print "Already favorited this song."

def formatOutput(text):
    data = ''.join(text.findAll(text=True)).partition('favourites')
    data = (data[0]+data[1]).strip()
    data = data.replace('\t\t\t\t','')
    return data

def findMechanizeLinkById(desiredId):
    for link in br.links():
        attrDict = dict(link.attrs)
        try:
            if (attrDict['id'] == desiredId):
                return link
        # if KeyError is thrown while accessing id, link has no id, so skip
        except KeyError:
            pass
    return None

def findSoupItemById(desiredId):
    soup = BeautifulSoup(br.response().read())
    return soup.find(attrs={'id' : desiredId})

def getSeconds():
    span = findSoupItemById('np_timer')
    return int(span['rel'])

def songHasBeenRated():
    rateText = findSoupItemById('rateform')
    rateText = rateText.contents[4].strip()
    return (rateText.find('Change your rating for this song:') != -1)

while(True):
    totalSeconds = 0
    # 28800 seconds = 8 hours
    while(totalSeconds < 28800):
        safeOpen(SONG_URL)
        try:
            br.select_form(nr=0)
        except:
            # if a form can't be selected, the browser isn't logged in
            login()
            safeOpen(SONG_URL)
            br.select_form(nr=0)
        seconds = getSeconds()
        if seconds <= 45:
            # if <= 30, rate and set timer to timer + ~10
            soup = BeautifulSoup(br.response().read())
            items = soup.findAll('td', limit=2)
            text = items[1]
            if not (songHasBeenRated()):
                rating = text.contents[12].strip().strip('Rating: ')
                currentRating = rating.split('/', 1)[0]
                rates = rating.split('rate', 1)[0]
                rates = rates.split('(')[1]

                myRating = generateRating(currentRating, rates)

                print formatOutput(text)
                print 'My Rating: %d' % myRating

                br['rating'] = [str(myRating)]
                br.submit()

                # if song is above rating threshold, add it to favorites
                if (myRating >= 9):
                    favoriteSong()

            else:
                rating = br['rating'][0]
                print formatOutput(text)
                print 'Already rated this song: %s' % rating
                # if song is above rating threshold, add it to favorites
                if (float(rating) >= 9):
                    favoriteSong()

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

