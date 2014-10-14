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
                   'Elite European Leagues',  # will get these via European Coupons
                   'European Championships',
                   'Specials',
                   'Outright',
                   'Accas',
                   'Bundles',
                   'Transfer',
                   'Over',
                   'Popular',
                   'Under',
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
