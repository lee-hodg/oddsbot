#!/usr/bin/env python
from scrapy import log
from scrapy import signals
from subprocess import call
import os
from twisted.internet import reactor, defer
from scrapy.crawler import Crawler
from scrapy.utils.project import get_project_settings


# Spiders
from Bookies.spiders.sport888_spider import sport888Spider
from Bookies.spiders.Apollobet_spider import ApollobetSpider
from Bookies.spiders.Apostasonline import ApostasonlineSpider
from Bookies.spiders.bet188_spider import Bet188Spider
from Bookies.spiders.Bet3000_spider import Bet3000Spider
from Bookies.spiders.Betathome import BetathomeSpider
from Bookies.spiders.Betfred_spider import BetfredSpider
from Bookies.spiders.Betinternet_spider import BetinternetSpider
from Bookies.spiders.Betsafe_spider import BetsafeSpider
from Bookies.spiders.Betsson_spider import BetssonSpider
from Bookies.spiders.Betvictor_spider import BetvictorSpider
from Bookies.spiders.Betway_spider import BetwaySpider
from Bookies.spiders.BGbet_spider import BGbetSpider
from Bookies.spiders.Buzzodds_spider import BuzzoddsSpider
from Bookies.spiders.Bwin_spider import BwinSpider
from Bookies.spiders.Coral_spider import CoralSpider
from Bookies.spiders.Dhoze_spider import DhozeSpider
from Bookies.spiders.Doxxbet_spider import DoxxbetSpider
from Bookies.spiders.Fortunawin_spider import FortunawinSpider
from Bookies.spiders.Gentingbet_spider import GentingbetSpider
from Bookies.spiders.Interwetten_spider import InterwettenSpider
from Bookies.spiders.Ladbrokes_spider import LadbrokesSpider
from Bookies.spiders.Marathonbet_spider import MarathonbetSpider
from Bookies.spiders.Nordicbet_spider import NordicbetSpider
from Bookies.spiders.Oddsring import OddsringSpider
from Bookies.spiders.OneVice_spider import OneviceSpider
from Bookies.spiders.Paddypower_spider import PaddypowerSpider
from Bookies.spiders.Setantabet_spider import SetantabetSpider
from Bookies.spiders.Skybet_spider import SkybetSpider
from Bookies.spiders.Sportingbet_spider import SportingbetSpider
from Bookies.spiders.Sportium_spider import SportiumSpider
from Bookies.spiders.Stanjames_spider import StanjamesSpider
from Bookies.spiders.Titanbet_spider import TitanbetSpider
from Bookies.spiders.Tonybet import TonybetSpider
from Bookies.spiders.Totesport_spider import TotesportSpider
from Bookies.spiders.Whitebet import WhitebetSpider
from Bookies.spiders.Williamhill_spider import WilliamhillSpider

# Map spider names to spider class instances
spiderDict = {'sport888': sport888Spider,
              'Apollobet': ApollobetSpider,
              'Apostasonline': ApostasonlineSpider,
              'Bet188': Bet188Spider,
              'Bet3000': Bet3000Spider,
              'Betathome': BetathomeSpider,
              'Betfred': BetfredSpider,
              'Betinternet': BetinternetSpider,
              'Betsafe': BetsafeSpider,
              'Betsson': BetssonSpider,
              'Betvictor': BetvictorSpider,
              'Betway': BetwaySpider,
              'BGbet': BGbetSpider,
              'Buzzodds': BuzzoddsSpider,
              'Bwin': BwinSpider,
              'Coral': CoralSpider,
              'Dhoze': DhozeSpider,
              'Doxxbet': DoxxbetSpider,
              'Fortunawin': FortunawinSpider,
              'Gentingbet': GentingbetSpider,
              'Interwetten': InterwettenSpider,
              'Ladbrokes': LadbrokesSpider,
              'Marathonbet': MarathonbetSpider,
              'Nordicbet': NordicbetSpider,
              'Oddsring': OddsringSpider,
              'Onevice': OneviceSpider,
              'Paddypower': PaddypowerSpider,
              'Setantabet': SetantabetSpider,
              'Skybet': SkybetSpider,
              'Sportingbet': SportingbetSpider,
              'Sportium': SportiumSpider,
              'Stanjames': StanjamesSpider,
              'Titanbet': TitanbetSpider,
              'Tonybet': TonybetSpider,
              'Totesport': TotesportSpider,
              'Whitebet': WhitebetSpider,
              'Williamhill': WilliamhillSpider,
              }


# ======================LOGGING (python logging not scrapy logging)
import logging
LOG_LEVEL = logging.DEBUG
LOGFORMAT = "  %(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s"
from colorlog import ColoredFormatter
logging.root.setLevel(LOG_LEVEL)
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)
log2 = logging.getLogger('pythonConfig')
log2.setLevel(LOG_LEVEL)
log2.addHandler(stream)

# ======================MONGO
# Need mongo so we can delete old db for given bookie
from pymongo import MongoClient
client = MongoClient()
client = MongoClient('localhost', 27017)
db = client.oddsbot_scrapy  # connect to our db
events = db.events  # then events collection
xevents = db.xevents  # then xevents collection


# =============POSTGRES (store arbs in postgres)
# Need pg so we can delete old arbs for given bookies
import psycopg2
try:
    conn = psycopg2.connect("dbname=arbs user=oddsbot password='oddsbot' host=localhost")
except psycopg2.OperationalError as e:
    log2.error(e)
    exit()


# Scrape exchanges
def xrunner():
    '''
    Run the data gathering for exchanges.
    '''
    # change cwd to scripts
    orig_dir = os.getcwd()
    xpath = os.path.join(orig_dir, 'Exchanges')
    os.chdir(xpath)

    log2.info('Removing previous xevents in db')
    xevents.drop()
    # Exchange scripts take care of clearing own mongo entries
    # Betfair
    r1 = call(["./BFscrapev3.py", ])
    # Betdaq
    r2 = call(["./DAQxml.py", ])
    # Smarkets
    r3 = call(["./Smarketsxml.py", ])

    # Back to original dir
    os.chdir(orig_dir)
    return (r1, r2, r3)

# The logging is a real annoyance as although crawler arg(crawler=crawler) can bring
# back `log_count` stats for a given crawler, we can only start the log once
# without problems.
# Is there an `exception_count` key instead that could be used with stats
# mailer? or another way to get something like this functionality back?
log.start()


def setup_crawler(spider, stop=False):
    '''
    Takes a spider class object
    '''
    # Deferred means other functions can wait on this finishing
    # Wait until the callback is triggered by spider close
    # See twisted docs
    d = defer.Deferred()

    def foo(*a, **kw):
        # The result to be passed to any callbacks to deferred
        # (we don't use it, so True could've been False, None w/e)
        d.callback(True)
    settings = get_project_settings()
    crawler = Crawler(settings)
    crawler.configure()
    # Ref to foo otherwise it gets GC'd (garbage collected)
    crawler._tempref = foo
    # foo is the handler for the closed signal from this spider
    # N.B. dispatch returns spider and reason (e.g. 'finished') to foo.
    crawler.signals.connect(foo, signal=signals.spider_closed)
    crawler.crawl(spider)
    # N.B log is scrapy log. log2 is python color logger
    # The crawler arg is necessary for log_count/{ERROR, DEBUG, INFO..} stats
    # which you will want for stats mailer extension.
    # Starting this each time will cause the big torrade of ESMTP Error
    # log.start(crawler=crawler)
    crawler.start()
    return d


def processBatch(spiderNames):
    dlist = []
    # Setup the spiders for this batch
    for spiderName in spiderNames:
        # log2.info('Seting up crawler for bookie %s' % spiderName)
        d = setup_crawler(spiderDict[spiderName]())
        dlist.append(d)
    # Deferred list means things will wait until every element finished before
    # cont.
    return defer.DeferredList(dlist)

spiderNames = [['sport888',  'Apollobet', 'Apostasonline', 'Bet188', 'Bet3000'],
               # ['Betathome', 'Betfred', 'Betinternet', 'Betsafe', 'Betsson', ],
               # ['Betvictor', 'Betway', 'BGbet', 'Buzzodds', 'Bwin', 'Coral', ]
               # ['Dhoze', 'Doxxbet', 'Fortunawin', 'Gentingbet', 'Interwetten', ]
               # ['Ladbrokes', 'Marathonbet', 'Nordicbet', 'Oddsring', 'OneVice', ]
               # ['Paddypower', 'Setantabet', 'Skybet', 'Sportingbet', 'Sportium', ]
               # ['Stanjames', 'Titanbet', 'Tonybet', 'Totesport', 'Whitebet', 'Williamhill', ]
               ]


# defer.inlineCallbacks uses deferred behind scenes, allowing you to use yield
# syntax to wait on a deferred
@defer.inlineCallbacks
def startSpiders():

    for group in spiderNames:
        log.msg('\n\nStarting group: %s\n\n' % (group,))
        log2.info('Removing previous events in db for %s' % group)
        events.remove({'bookieName': {'$in': spiderNames}})
        yield processBatch(group)
        log.msg('\n\nEnded group: %s\n\n' % (group,))
        # do something else now that the batch is done.
        # ...
        # Scrape exchanges
        results = xrunner()
        log2.info('Hunt for some arbs...')
        # Finally search for some juicy arbs
        # Delete arbs in db for these bookies
        with conn:
            cur = conn.cursor()
            try:
                cur.execute('DELETE FROM arbs_tab WHERE bookie_name in %s' % str(tuple(group)))
            except psycopg2.ProgrammingError:
                # table doesn't exist
                pass
        # Need to fix findarbs so we are only looking
        # in latest batch (either by removing all events above instead
        # of just those with bookieName in group, or by passing
        # bookie names along as args to findarbs.py (keeping is good if in
        # future we wanted an xml feed of bookie data say, or some other use,
        # but might also slow down arb search?)
        res = call(['./findarbs.py',  '--books']+ group)
    reactor.stop()

reactor.callWhenRunning(startSpiders)
reactor.run()
