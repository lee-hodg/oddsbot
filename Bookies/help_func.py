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
                   'Matches',
                   'Club specials',
                   'Veikkausliiga Season Bets',
                   'Winner',
                   'Top',
                   'Betclic',
                   'Enhanced Odds',
                   'Special',
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
