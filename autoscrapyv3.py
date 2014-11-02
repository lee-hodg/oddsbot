#!/usr/bin/env python
from scrapy import log
from scrapy import signals
from subprocess import call
import os
from twisted.internet import reactor
from scrapy.crawler import Crawler
from scrapy.utils.project import get_project_settings
# from scrapy.xlib.pydispatch import dispatcher

# Listen for spider_closed, stop reactor.
# def stop_reactor():
#    reactor.stop()
# dispatcher.connect(stop_reactor, signal=signals.spider_closed)

# Spiders
from Bookies.spiders.Apollobet_spider import ApollobetSpider
from Bookies.spiders.BGbet_spider import BGbetSpider
from Bookies.spiders.Buzzodds_spider import BuzzoddsSpider
from Bookies.spiders.Bwin_spider import BwinSpider
from Bookies.spiders.Coral_spider import CoralSpider
# Map spider names to spider class instances
spiderDict = {'Apollobet': ApollobetSpider(),
              'BGbet': BGbetSpider(),
              'Buzzodds': BuzzoddsSpider(),
              'Bwin': BwinSpider(),
              'Coral': CoralSpider(),
              }

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


def setup_crawler(spider, stop=False):
    '''
    Takes a spider class object
    '''
    settings = get_project_settings()
    crawler = Crawler(settings)
    crawler.configure()
    if stop:
        log2.debug('Close set to stop reactor as last spider of batch.')
        # Stop reactor after spider runs
        crawler.signals.connect(reactor.stop, signal=signals.spider_closed)
    crawler.crawl(spider)
    # N.B log is scrapy log, log2 is python color logger
    log.start(logstdout=True, crawler=crawler)
    crawler.start()


# First x poll and first batch of spiders
# results = xrunner()
log2.info('Now begining batch of bookies...')
spiderNames = ['Buzzodds', ]  # ['Apollobet', 'BGbet', 'Buzzodds', 'Bwin', 'Coral', ]
# Setup the spiders for this batch
for n, spiderName in enumerate(spiderNames):
    log2.info('Seting up crawler for bookie %s' % spiderName)
    stop = False
    if n == len(spiderNames)-1:
        # Last spider
        stop = True
    setup_crawler(spiderDict[spiderName], stop=stop)
    log2.info('Removing previous events in db for %s' % spiderName)
    events.remove({'bookieName': spiderName})
reactor.run()
exit()
log2.info('Hunt for some arbs...')
# Finally search for some juicy arbs
# Delete arbs in db for these bookies
with conn:
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM arbs_tab WHERE bookie_name in %s' % str(tuple(spiderNames)))
    except psycopg2.ProgrammingError:
        # table doesn't exist
        pass
res = call(['./findarbs.py', ])
