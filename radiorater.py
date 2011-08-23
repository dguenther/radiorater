## 
## animenfo rating bot
##
## Last Updated: 08-03-2011
## Version 2
##
## future improvements:
## request songs that haven't been voted for yet
## lot of error-handling missing
##

from BeautifulSoup import BeautifulSoup
import datetime
import ConfigParser
import mechanize
import urllib
import random
import sys
import time

# read configuration file
# TODO: need to implement creating configuration file if it doesn't exist
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

# constants not yet added to config file
START_HOUR = 9
END_HOUR = 17

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
    ''' Retries opening URL until it opens successfully '''
    success = False
    while success == False:
        try:
            if data == None:
                br.open(url)
            else:
                br.open(url,data)
            success = True
        except:
            # if url opening fails, sleep for 2 seconds
            success = False
            time.sleep(2)

def login():
    ''' Logs into the site and saves a cookie to the cookiejar '''
    values = {'frompage':'index.php',
            'username':USERNAME,
            'password':PASSWORD
            }
    data = urllib.urlencode(values)
    safeOpen("https://www.animenfo.com/radio/login.php", data)
    # TODO: add some kind of handler if login fails
    cj.save()

def getStdDev(rates):
    ''' Returns a standard deviation used for rating based on the number of people
        who have already rated a song '''
    # These are fairly arbitrary numbers. I wouldn't mind finding
    # a smoother way to do this, maybe some sort of exponential curve
    if rates == 0:
        return 1.5
    elif rates < 100:
        return 1
    elif rates < 1000:
        return 0.75
    else:
        return 0.5

def generateRating(currentRating, rates):
    ''' Generates an integer rating between 1 and 10 based on the current
        song rating and the number of times it has been rated '''
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
    ''' Add a song to the favorites list '''
    if (findMechanizeLinkById('np_removefav') == None):
        favoriteLink = findMechanizeLinkById('np_addfav')
        if (favoriteLink != None):
            br.follow_link(favoriteLink)
            br.back()
            print "Added this song to favorites."
        else:
            print "Unable to favorite song - no favorites links detected."
    else:  
        print "Already favorited this song."

def getContent():
    soup = BeautifulSoup(br.response().read())
    items = soup.findAll('td', limit=2)
    print items[1]
    return items[1]

def outputSongInfo():
    text = getContent()
    data = ''.join(text.findAll(text=True)).partition('favourites')
    data = (data[0]+data[1]).strip()
    data = data.replace('\t\t\t\t','')
    return data

def findMechanizeLinkById(desiredId):
    ''' Given the ID of a link on the page, returns that link as a mechanize link '''
    for link in br.links():
        attrDict = dict(link.attrs)
        try:
            if (attrDict['id'] == desiredId):
                return link
        # if KeyError is thrown while accessing id, link has no id, so skip it
        except KeyError:
            pass
    return None
    
def findMechanizeLinksWithClass(desiredClass):
    ''' Given a class, returns a list of mechanize links that have that class '''
    linkList = []
    for link in br.links():
        attrDict = dict(link.attrs)
        try:
            if (desiredClass in attrDict['class']):
                linkList.append(link)
        # if KeyError is thrown while accessing class, link has no class, so skip it
        except KeyError:
            pass
    return linkList

def findSoupItemById(tagName, desiredId):
    soup = BeautifulSoup(br.response().read())
    return soup.find(tagName, attrs={'id' : desiredId})

def getSeconds():
    timeSpan = findSoupItemById('span','np_timer')
    return int(timeSpan['rel'])

def songHasBeenRated():
    rateText = findSoupItemById('form', 'rateform')
    rateText = rateText.contents[4].strip()
    return (rateText.find('Change your rating for this song:') != -1)

def canRate(currentTime):
    ''' Returns true if the current time is between START_HOUR and END_HOUR '''
    date = currentTime.date()
    startDatetime = datetime.datetime.combine(date, datetime.time(START_HOUR,0,0))
    endDatetime = datetime.datetime.combine(date, datetime.time(END_HOUR,0,0))
    return (startDatetime < currentTime and endDatetime > currentTime)

def getSecondsUntilTomorrow(currentTime):
    ''' Returns the number of seconds until START_HOUR '''
    date = currentTime.date()
    date = date + datetime.timedelta(days=1)
    tomorrowDatetime = datetime.datetime.combine(date, datetime.time(START_HOUR,0,0))
    delta = tomorrowDatetime - currentTime
    return delta.seconds

# main (infinite) loop
while(True):
    currentTime = datetime.datetime.now()
    while(canRate(currentTime)):
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
            if not (songHasBeenRated()):
                soup = BeautifulSoup(br.response().read())
                items = soup.findAll('td', limit=3)
                text = items[2]
                rating = text.contents[5].strip().strip('Rating: ')
                currentRating = rating.split('/', 1)[0]
                rates = rating.split('rate', 1)[0]
                rates = rates.split('(')[1]

                myRating = generateRating(currentRating, rates)

                print outputSongInfo()
                print 'My Rating: %d' % myRating

                br['rating'] = [str(myRating)]
                br.submit()

                # if song is above rating threshold, add it to favorites
                if (myRating >= 9):
                    favoriteSong()

            else:
                rating = br['rating'][0]
                print outputSongInfo()
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
        currentTime = datetime.datetime.now()

    sleepTime = getSecondsUntilTomorrow(currentTime)
    print 'Sleeping for %d hours, %d minutes...' % ((sleepTime / 3600), ((sleepTime % 3600)/ 60))
    time.sleep(sleepTime)

