import datetime
from scrapy import log


def day2date(day):

    #
    # Take a name like Today, Tomorrow, short date Sat, sat, long date Saturday, saturday
    # and convert it to %m %d of the soonest Sat
    # from now.
    # N.B. dateutil.parser makes this redundent
    #
    day = day.lower()
    today = datetime.datetime.now()

    # get next 7 days as %m %d and dayname
    days = {}
    # first today and tomorrow
    days[0] = {'name': ['today', today.strftime('%a').lower(), today.strftime('%A').lower()],
               'fmt_date': today.strftime('%m %d')
               }
    tmoz = today + datetime.timedelta(days=1)
    days[1] = {'name': ['tomorrow', tmoz.strftime('%a').lower(), tmoz.strftime('%A').lower()],
               'fmt_date': tmoz.strftime('%m %d')
               }
    # then the next 5
    for n in range(2, 7):
        the_day = today + datetime.timedelta(days=n)
        days[n] = {'name': [the_day.strftime('%a').lower(), the_day.strftime('%A').lower()],
                   'fmt_date': the_day.strftime('%m %d')
                   }

    # perform format of day by matching
    for d in days:
        if day in days[d]['name']:
            return days[d]['fmt_date']
    # print '\033[31m\033[7m day2date Could not format day:  %s \033[0m' % day
    return -1


def linkFilter(name, link):
    #
    # If any of these phrases in the link
    # we deem link as junk, and do not want to scrape it.
    #
    junkPhrases = ['Long List',
                   '1-A-Piece',
                   'Galore',
                   'Delight',
                   "Today's Matches",
                   'First Goalscorer Scorecasts',
                   'Coupons',
                   'Group Betting',
                   'To Qualify',
                   'Correct Score Crazy',
                   '0-0 Cashback Offer',
                   'Elite European Leagues',
                   'European Championships',
                   'Specials',
                   'Outright',
                   'Accas',
                   'Bundles',
                   'Transfer',
                   'Over',
                   'Popular',
                   'Under',
                   'special',
                   'long-term',
                   'wc-',
                   'final',
                   'group-winner',
                   'outrights',
                   'Live',
                   'What If',
                   'World Cup',
                   '2016',
                   'Capital One',
                   'outright',
                   'in-play',
                   'winner',
                   'winning-nation',
                   'corners',
                   'reach-the',
                   'to-qualify',
                   'Winner',
                   'Top',
                   'Finishing',
                   'Special',
                   'Relegated',
                   'Overall',
                   'overall-winner',
                   'group-winner',
                   'final-participants',
                   'group',
                   'winners-nation',
                   'first-time-winner',
                   'qualification-group',
                   'group-',
                   'top-goal-scorer',
                   'Outrights',
                   'To progress',
                   'Fantasy Matches',
                   'Club specials',
                   'Veikkausliiga Season Bets',
                   'Winner',
                   'Top',
                   'Betclic',
                   'Enhanced Odds',
                   'Special',
                   'Specials',
                   'Outright',
                   'top-matches',
                   'action=go_fb',
                   'acca-bonus',
                   'uk-both-teams-to-score',
                   'today-and-tomorrow',
                   'win-draw-win-both-teams-to-score',
                   'my-matches',
                   'football-outrights',
                   'football-specials',
                   'multiple',
                   'specials',
                   'forecast',
                   'finalist',
                   'totals',
                   'elimination',
                   'awards',
                   'highest',
                   'top',
                   'world-cup-2014/groups',
                   'winner',
                   'fastest-goal',
                   'Multi Match',
                   ]

    exceptionPhrases = []

    for phrase in exceptionPhrases:
        # don't filter exceptions
        if phrase in link:
            return False

    for phrase in junkPhrases:
        if phrase in link:
            log.msg('Filtering out link: %s' % link,
                    level=log.INFO)
            return True

    return False  # don't filter rest


def am2dec(odd):
    '''
    Convert US odds to Decimal style.
    '''
    if odd in ['EV', 'ev', 'even', 'evens']:
        return odd

    try:
        odd = float(odd)
    except ValueError:
        return -1
    # retrun formatted 2d
    if odd <= -100:
        return "%0.2f" % (1-(100/odd))
    else:
        return "%0.2f" % (1+(odd/100))


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]


import math


def getOddsRounded(odds):

    '''
    This appears to be the function used by Setantabet
    to round the odds before doing the standard am2dec conv.
    I found this function by examing the DOM in firebug (note
    you can right-click func on rhs and copy and paste in a js
    beautifier without having to dig around all the js files)
    I ultimately grabbed it from chrome dev, as firebug was playing up
    : enter the console and type window to get the equiv of dom then do a search
    . Function names of interest: decimalOddsToAmerican, getOddsFromAmerican,
    getOddsFromAmericanToEU, hongKongToDecimal, getOddsRounded...chrome say this
    in global.js
    '''
    if math.fabs(odds) < 600:
        outOdds = int(round(odds/5)) * 5
        if outOdds == -100:
            return 100
        else:
            return outOdds
    elif (odds > -1000 and odds < 0):
        return math.floor(odds / 5) * 5
    else:
        return math.floor(odds / 25) * 25
