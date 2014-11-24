#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division  # nice division
import difflib  # for string comparison
import unicodedata  # Normalize unicode by forcing to ascii equiv in compStr
import argparse
from smtplib import SMTPException

# Django and oddsbot
from scrapy.conf import settings
import sys
import os
sys.path.append(settings['ODDSBOT_DIR'])
# This allows us to use the modules available to oddsbot without installing
# them in the oddScr env too:
sys.path.append(settings['ODDSBOT_ENV'])
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oddsbot.settings")

from arb import Arb

# =====================CMDLINE ARG PARSING
parser = argparse.ArgumentParser(description='Hunt some arbs.')
parser.add_argument("--books", help="Bookies to search(at least one req)",
                    nargs="+", metavar=('Bookie1', 'Bookie2'))
args = parser.parse_args()
booksGroup = args.books

# ======================LOGGING
import logging
LOG_LEVEL = logging.DEBUG
LOGFORMAT = "  %(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s"
from colorlog import ColoredFormatter
logging.root.setLevel(LOG_LEVEL)
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)
log = logging.getLogger('pythonConfig')
log.setLevel(LOG_LEVEL)
log.addHandler(stream)

# =============PARAMETERS
# The fraction bookie odd > exchange odd to be consiered worthy of keeping.
MIN_ARB_FRAC = 0.95
# The min odd at bookmaker to keep.
MIN_BOOK_ODD = 1.00
# List of lists grouping bookies that share odds, this saves us uneeded scraping
# N.B. Dhoze, Betsson, Betsafe are linked and sim websites, but odds seem to be
# diff (indeed I think there is even a connection between them and Trio/Nordic)
# N.B. Guts also part of teambet group but odds are different...(I think with
# Oddsmatrix Bookies can just add the solution into their own lines and modify
# bets, but others seem to rely excusively (or heavily on matrx))
sharedOddsLists = [['Setantabet', 'Jenningsbet', ],
                   ['Betvictor', 'McBookie', ],
                   ['sport888', 'Unibet', 'Paf', '32RedSport', 'iveriabet', ],
                   ['Stanjames', 'Betpack', ],
                   ['Nordicbet', 'Triobet', ],
                   ['Whitebet', 'Redbet', ],
                   ['Titanbet', 'Betvernons', ],
                   ['Apollobet', 'Seaniemac', 'Boylesports', ],
                   ['Teambet', 'Betredkings', 'Jetbull', 'Bestbet', ],
                   ]

# if str is in dictionary of aliases replace by standard:
# should be pickled eventually or some such.
# ALIASES = {'manchester city': ['man city', 'man.city'],
#            'manchester united': ['man united', 'man u', 'man utd',
#                                  'manchester u', 'manchester utd'],
#            'cordoba': ['cordoba cf', ],
#            'evian thonon gaillard': ['evian tg', ],
#            'paris saint germain': ['paris sg', 'paris st-g', 'paris st g',
#                                    'paris st germain', 'paris st.g',
#                                    'paris st.germain', ],
#            'qpr': ["queen's park rangers", ],
#            'atletico madrid': ['atl madrid', ],
#            'rayo vallecano': ['vallecano', ],
#            'blackburn rovers': ['blackburn', ],
#            'bayern munich': ['b munich', ],
#
#            }

# =============POSTGRES (store arbs in postgres)
import psycopg2
conn = psycopg2.connect("dbname=arbs user=oddsbot password='oddsbot' host=localhost")
with conn:
    cur = conn.cursor()
    initSQLcmd = "CREATE TABLE IF NOT EXISTS "
    initSQLcmd += ("arbs_tab(Id SERIAL PRIMARY KEY, event_datetime TIMESTAMP WITH TIME ZONE,"
                   "sport TEXT, market_type TEXT,")
    initSQLcmd += ("competition TEXT, event_name TEXT, bet_on TEXT,"
                   "arb_value REAL, bookie_name TEXT, bookie_odd REAL,"
                   "exchange_name TEXT,")
    initSQLcmd += ("mid TEXT, mhref TEXT, exchange_odd1 REAL, exchange_stake1 REAL,"
                   "exchange_odd2 REAL, exchange_stake2 REAL,"
                   "exchange_odd3 REAL, exchange_stake3 REAL, found_stamp TIMESTAMP WITH TIME ZONE)")
    cur.execute(initSQLcmd)


# =============MONGO
# Now can easily insert documents with xmarket_id = xmarkets.insert(someevent)
# (see http://api.mongodb.org/python/current/tutorial.html)
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
client = MongoClient()
client = MongoClient('localhost', 27017)
db = client.oddsbot_scrapy  # connect to our db
events = db.events  # then bookies events collection
xevents = db.xevents  # then exchange events collection
# arbs = db.arbs  # arbs collection
aliases = db.aliases
# make primaryName unqiue
aliases.ensure_index('primaryName', unique=True)

# MONGO doesn't really support joins, but its read/write generally
# faster than postgres. It might be tempting to think sql with join
# and speed gain there is a good choice for arb finding (i.e.
# join on name1 == name2 and (odd1 > .95 odd1 or odd2> .95 odd2 or odd3 > .95 odd3)
# But in reality name1 is never equal name2, we need to string compare func
# also not sure just how complex the join logic can really be.
# We should test exactly where the bottle kneck comes from it is still slow
# using some timeit, is it the looping, the str comp alg, or what.
# There is writing a small c++ program at last resort. Maybe a stack overflow
# post too.

# Another Idea, could we use mongodb and strcompare to help build aliases
# dict keeping {'Man U': [....]} and appending if not in list when strcomp
# thinks it could be a match.


def aliasInsert(str1, str2):
    # Test if document exists with either str1 or str2 as primaryName
    # This should be made a unique field too somehow
    # This should gradually speed up compStr

    # ALSO NEED TO SELECT IF str1 or str2 in otherNames
    record = aliases.find_one({'$or':
                               [{"primaryName": {'$in': [str1, str2]}},
                                {'otherNames': {'$in': [str1, str2]}}
                                ]
                               })
    if record:
        if record['primaryName'] == str1:
            # Append str2 to its list if not already there
            aliases.update(record, {'$addToSet': {'otherNames': str2}})
        elif record['primaryName'] == str2:
            # Append str1 to its list if not already there
            aliases.update(record, {'$addToSet': {'otherNames': str1}})
        elif str1 in record['otherNames']:
            aliases.update(record, {'$addToSet': {'otherNames': str2}})
        elif str2 in record['otherNames']:
            aliases.update(record, {'$addToSet': {'otherNames': str1}})

    else:
        # no existing record with str1 as primary key
        try:
            aliases.insert({'primaryName': str1, 'otherNames': [str2, ]})
        except DuplicateKeyError:
            pass


def compStrQuick(str1, str2):
    if str1 == str2:
        return True
    return False


def compStr(str1, str2):
    '''
    Decide if two teams from different books are really the same.
    '''
    str1, str2 = str1.lower(), str2.lower()

    # Force unicode chars to ascii equiv, e.g. accented 'a' to regular 'a'
    str1 = unicodedata.normalize('NFKD', str1).encode('ascii', 'ignore')
    str2 = unicodedata.normalize('NFKD', str2).encode('ascii', 'ignore')
    # aliases = ALIASES
    # for key in aliases:
    #     if str1 in aliases[key]:
    #         str1 = key
    #     if str2 in aliases[key]:
    #         str2 = key
    # Standardise names on primaryName
    for alias in aliases.find():
        if str1 in alias['otherNames']:
            str1 = alias['primaryName']
        if str2 in alias['otherNames']:
            str2 = alias['primaryName']

    # Is either simply contained in other? (e.g. man city and man city fc)
    if (str1 in str2) or (str2 in str1):
        return True
    # If u21 or u18 in one must be in other
    if 'u21' in str1 and 'u21' not in str2:
        return False
    elif 'u21' in str2 and 'u21' not in str1:
        return False
    if 'u18' in str1 and 'u18' not in str2:
        return False
    elif 'u18' in str2 and 'u18' not in str1:
        return False

    # Resort to similiary testing. Quite unlikely both home/away will fail this.
    critVal = 0.8
    try:
        # The first arg allows junk ignore if set
        similarity = difflib.SequenceMatcher(None, str1, str2).ratio()
        if similarity > critVal:
                # Write str2 to str1 key of list in mongo overtime building up
                # lists we can maybe use to auto build alias dic
                # If deemed the same append to mongo aliases dic
                # to speed up things next time
                aliasInsert(str1, str2)
                return True
        else:
            return False
    except UnicodeEncodeError as e:
        print 'Unicode Error: %s.' % e
        print str1.encode('utf-8'), str2.encode('utf-8')


# ===========Seek Arbs
# As usual between each n bookies we drop xmarket and events coll in shell
# Now the search is for all bookies and exchanges at once.
# N.B. xmarkets uses team names and "The Draw" for Match Odds markets, not good,
# as don't want to comp str again so we could just use position in runners to
# determine home draw away, I think best way is to redefine them in polling API.
# For CS xmarkets has runnerNames like '1-0' avoiding
# team names, so we should format it that way in events too.
# For markets where it's impossible to differentiate without the team name in
# the runnerName (position and other text not sufficient) we'd have to comp str.

# Want to fix the bookie format so we have markets: [{ 'marketName': 'Match
# Odds', 'runners' : [{'runnerName': 'HOME', 'price': 4.5},....]},....]
# the following assumes that has been done.

log.info('Search books %s' % ', '.join(booksGroup))
pk_list = []
# Typically events is smaller than xmarkets so search it outer
for event in events.find({'bookie': {'$in': booksGroup}}):
    event_marketNames = [eventMarket['marketName'] for eventMarket in event['markets']]
    # Only if events have markets where at least one market in event_marketNames
    xevents_subset = xevents.find({'shortDateTime': event['dateTime'],
                                   'markets': {'$elemMatch': {"marketName":
                                                              {'$in': event_marketNames
                                                               }
                                                              }
                                               }
                                   })

    # If you could write the compStr in js, you could further reduce subset
    # with 'team1': $where: compStr() { //stuff better than obj.team1 ==
    # event['teams][0]} etc, but this function is quite python specific
    # Might be worth a look for speed (might be slow anyway though) as
    # the docs note that $where with js funcs can be slow...
    # xevents_subset = xevents.find({'team1': event['teams'][0],
    #                               'team2': event['teams'][1]
    #                               })
    if xevents_subset.count() == 0:
        continue
    else:
        for xevent in xevents_subset:
            if (compStr(xevent['team1'], event['teams'][0])
               and compStr(xevent['team2'], event['teams'][1])):
                # Event match
                # log.info('We have event name match: %s vs %s' %
                #          (xevent['team1'], xevent['team2']))
                for bmarket in event['markets']:
                    for xmarket in xevent['markets']:
                        if bmarket['marketName'] == xmarket['marketName']:
                            # log.info('Market match too: %s' % bmarket['marketName'])
                            # Finally check price data for the arb
                            for xrunner in xmarket['runners']:
                                for brunner in bmarket['runners']:
                                    if xrunner['runnerName'] == brunner['runnerName']:
                                        # log.error('...and a runner match:%s'% brunner)
                                        # Same runner
                                        # get best (first) lay price
                                        bprice = float(brunner['price'])
                                        if bprice > MIN_BOOK_ODD:
                                            try:
                                                xprice = float(xrunner['availableToLay'][0]['price'])
                                            except (KeyError, IndexError):
                                                continue
                                            if bprice > (MIN_ARB_FRAC*xprice):
                                                # Arb found
                                                # write to db
                                                # save the pk (or obj id) in list
                                                # so use same filter/email func as bef

                                                # Django  wants YYYY-MM-DD
                                                # HH:MM[:ss[.uuuuuu]][TZ]
                                                # format. Betfair is UTC, so
                                                # should be good even without
                                                # giving Django timezone
                                                # string.
                                                try:
                                                    # old_when = datetime.datetime.strptime(xevent['dateTime'],
                                                    #                                  '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d %H:%M%Z')
                                                    # Note literal Z is code for
                                                    # +0000, pg can parse that
                                                    # already
                                                    when = xevent['dateTime']
                                                    # log.critical(old_when)
                                                except (TypeError, ValueError) as e:
                                                    log.error(e)
                                                    log.error('Exchange dateTime non-existant or malformed?')
                                                    continue
                                                try:
                                                    comp = xevent['compName']
                                                except KeyError:
                                                    comp = 'Unknown'

                                                try:
                                                    exchange_size1 = xrunner['availableToLay'][0]['size']
                                                    if exchange_size1:
                                                        # if exists
                                                        exchange_size1 = float(exchange_size1)
                                                    else:
                                                        exchange_size1 = 0.00
                                                except (ValueError, IndexError) as e:
                                                    # log.error(e)
                                                    # log.error('Error when converting exchange size1')
                                                    exchange_size1 = 0.00

                                                try:
                                                    exchange_size2 = xrunner['availableToLay'][1]['size']
                                                    if exchange_size2:
                                                        # if exists
                                                        exchange_size2 = float(exchange_size2)
                                                    else:
                                                        exchange_size2 = 0.00
                                                except (ValueError, IndexError) as e:
                                                    # log.error(e)
                                                    # log.error('Error when converting exchange size2')
                                                    exchange_size2 = 0.00

                                                try:
                                                    exchange_size3 = xrunner['availableToLay'][2]['size']
                                                    if exchange_size3:
                                                        # if exists
                                                        exchange_size3 = float(exchange_size3)
                                                    else:
                                                        exchange_size3 = 0.00
                                                except (ValueError, IndexError) as e:
                                                    # log.error(e)
                                                    # log.error('Error when converting exchange size3')
                                                    exchange_size3 = 0.00

                                                try:
                                                    exchange_price1 = xrunner['availableToLay'][0]['price']
                                                    if exchange_price1:
                                                        # if exists
                                                        exchange_price1 = float(exchange_price1)
                                                    else:
                                                        exchange_price1 = 0.00
                                                except (ValueError, IndexError) as e:
                                                    # log.error(e)
                                                    # log.error('Error when converting exchange price1')
                                                    exchange_price1 = 0.00

                                                try:
                                                    exchange_price2 = xrunner['availableToLay'][1]['price']
                                                    if exchange_price2:
                                                        # if exists
                                                        exchange_price2 = float(exchange_price2)
                                                    else:
                                                        exchange_price2 = 0.00
                                                except (ValueError, IndexError) as e:
                                                    # log.error(e)
                                                    # log.error('Error when converting exchange price2')
                                                    exchange_price2 = 0.00

                                                try:
                                                    exchange_price3 = xrunner['availableToLay'][2]['price']
                                                    if exchange_price3:
                                                        # if exists
                                                        exchange_price3 = float(exchange_price3)
                                                    else:
                                                        exchange_price3 = 0.00
                                                except (ValueError, IndexError) as e:
                                                    # log.error(e)
                                                    # log.error('Error when converting exchange price3')
                                                    # log.error(xrunner['availableToLay'])
                                                    exchange_price3 = 0.00

                                                # arb = {'when': datetime.datetime.strptime(xevent['dateTime'],
                                                #                                           '%Y-%m-%dT%H:%M:%S.%fZ') \
                                                #                                           .strftime('%Y-%m-%d %H:%M'),
                                                #        'sport': event['sport'],
                                                #        'market_type': xmarket['marketName'],
                                                #        'competition': xevent['compName'],
                                                #        'event_name': xevent['eventName'],
                                                #        'bet_on': xrunner['runnerName'],
                                                #        'bookie': event['bookie'],
                                                #        'bookie_price': bprice,
                                                #        'exchange': xevent['exchangeName'],
                                                #        'mid': xmarket['marketId'],
                                                #        'exchange_stake1': xrunner['availableToLay'][0]['size'],
                                                #        'exchange_price1': xrunner['availableToLay'][0]['price'],
                                                #        'exchange_stake2': xrunner['availableToLay'][0]['size'],
                                                #        'exchange_price2': xrunner['availableToLay'][0]['price'],
                                                #        'exchange_stake3': xrunner['availableToLay'][0]['size'],
                                                #        'exchange_price3': xrunner['availableToLay'][0]['price'],
                                                #        'found_stamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')
                                                #        }

                                                # Form appropriate market href
                                                # depending on exch
                                                mhref = ''
                                                mid = xmarket['marketId'].replace('@', '.')
                                                if xevent['exchangeName'] == 'Betfair':
                                                    mhref = "http://www.betfair.com/exchange/football/market?id=%s" % mid
                                                elif xevent['exchangeName'] == 'Betdaq':
                                                    # Not sure how to link
                                                    # Betdaq
                                                    mhref = ''
                                                elif xevent['exchangeName'] == 'Smarkets':
                                                    # will just grab real url
                                                    # and store in mongo event
                                                    # for smarkets
                                                    mhref = xevent.get('url', '')
                                                # Create temp_arb
                                                temp_arb = Arb(when, event['sport'], xmarket['marketName'], comp,
                                                               xevent['eventName'], xrunner['runnerName'],
                                                               event['bookie'],
                                                               bprice, xevent['exchangeName'],
                                                               mid,
                                                               mhref,
                                                               exchange_price1, exchange_size1,
                                                               exchange_price2, exchange_size2,
                                                               exchange_price3, exchange_size3,
                                                               )

                                                print temp_arb

                                                flatList = [name for sublist in sharedOddsLists for name in sublist]
                                                if event['bookie'] not in flatList:
                                                    # Not sharing odds =>
                                                    # regular write
                                                    with conn:
                                                        arb_pk = temp_arb.writeSQLarb(conn, comm=0.05)
                                                        # Append arb pk to list
                                                        if arb_pk:
                                                            pk_list.append(arb_pk)
                                                        else:
                                                            log.error('Error writing arb pk list')
                                                else:
                                                    # Bookie is in a shared odds
                                                    # group, write the arb for other names
                                                    # in list too
                                                    for soList in sharedOddsLists:
                                                        if event['bookie'] in soList:
                                                            for bn in soList:
                                                                temp_arb.bookie = bn
                                                                with conn:
                                                                    arb_pk = temp_arb.writeSQLarb(conn, comm=0.05)
                                                                    if arb_pk:
                                                                        pk_list.append(arb_pk)
                                                                    else:
                                                                        log.error('Error writing arb pk to list')


# print 'Pk insert list: %s' % pk_list

if pk_list:
    # ###############Do some email alerts for arbs found ##########################

    # For all premium members, loop over their savedsearches, then e-mail them
    # if any arbs are found in the database matching.

    from django.utils.http import urlencode
    from django.forms.models import model_to_dict

    def savedsearch2querystr(ss):
        '''
        Takes a SavedSearch object and
        converts it into a GET str
        '''
        # GETstr = '&'.join('{}={}'.format(k,v) for k,v in model_to_dict(ss).items())
        mydict = model_to_dict(ss)
        # Remove unwanted keys
        if 'id' in mydict.keys():
            del mydict['id']
        if 'userprof' in mydict.keys():
            del mydict['userprof']
        # Generate URL encoded GET string from dict.
        GETstr = urlencode(mydict)
        return GETstr

    # Premium members
    from accounts.models import UserProfile
    all_profiles = UserProfile.objects.all()
    prem_profiles = []
    for prof in all_profiles:
        if u'Premium' in [group.name for group in prof.user.groups.all()]:
            if prof.user.is_active:
                prem_profiles.append(prof)

    # Send emails
    from email_alerts import filterArbs
    from django.core.mail import send_mail
    sender = 'webmaster@oddsbot.co.uk'
    # sender = 'lee@localhost'
    for prof in prem_profiles:
        recipients = ['leehodg@gmail.com']  # ['lee@localhost']  # [prof.user.email]
        for ss in prof.savedsearches.all():
            # loop over saved searches for this member
            # over recently found arbs in pk_list
            arbs_list = filterArbs(prof.user, savedsearch2querystr(ss), pk_list)
            print 'Number of arb email-alerts: %i' % len(arbs_list)
            # Send e-mail (I should offer custom name for saved search too)
            if arbs_list:
                # If arbs exist
                subject = 'Arb alert for saved search'
                message = 'Hello %s, \n\n' % prof.user.username
                for arb in arbs_list:
                    message += '::ARB::\n'
                    message += 'Event name:'+arb.event_name+'\n'
                    message += 'Event datetime:'+arb.event_datetime.strftime('%Y-%m-%d %H:%M')+'\n'
                    message += 'Bet on outcome:'+arb.bet_on+'\n'
                    message += 'Arb value:'+str(arb.custom_arb_value())+' %\n'
                    message += 'Competition:'+unicode(arb.competition)+'\n'
                    message += 'Market type:'+str(arb.market_type)+'\n'
                    message += 'Bookie name:'+str(arb.bookie_name)+'\n'
                    message += 'Bookie odd:'+str(arb.bookie_odd)+'\n'
                    message += 'Exchange name:'+str(arb.exchange_name)+'\n'
                    message += 'Exchange link:'+str(arb.mhref)+'\n'
                    message += 'Exchange odd (slot1):'+str(arb.exchange_odd1)+'\n'
                    message += 'Exchange liquidity (slot1):'+str(arb.exchange_stake1)+'\n'
                    message += '-'*20+'\n'
                    message += 'Exchange odd (slot2):'+str(arb.exchange_odd2)+'\n'
                    message += 'Exchange liquidity (slot2):'+str(arb.exchange_stake2)+'\n'
                    message += 'Exchange odd (slot3):'+str(arb.exchange_odd3)+'\n'
                    message += 'Exchange liquidity (slot3):'+str(arb.exchange_stake3)+'\n'
                    message += '-'*20
                    message += '\n\n'
                try:
                    send_mail(subject, message, sender, recipients)
                except SMTPException as e:
                    log.errror(e)
                print subject
                print message
