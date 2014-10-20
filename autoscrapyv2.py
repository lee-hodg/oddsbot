#!/usr/bin/env python
from subprocess import call
import os


# ======================MONGO
# Now can easily insert documents with xmarket_id = xmarkets.insert(someevent)
# (see http://api.mongodb.org/python/current/tutorial.html)
from pymongo import MongoClient
client = MongoClient()
client = MongoClient('localhost', 27017)
db = client.oddsbot_scrapy  # connect to our db
events = db.events  # then events collection


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

# =============POSTGRES (store arbs in postgres)
import psycopg2
try:
    conn = psycopg2.connect("dbname=arbs user=oddsbot password='oddsbot' host=localhost")
except psycopg2.OperationalError as e:
    log.error(e)
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

# First x poll and first batch of spiders
results = xrunner()
log.info('Now begining batch of bookies...')
spiders = ['Coral', ]
for spider in spiders:
    # If passing string either shell must be True or string
    # must simply be name of progam sans args.
    # call_cmd = "scrapy crawl %s" % spider
    # res = call.(call_cmd, shell=True)
    # Clear previous entries from db
    log.info('Calling bookie %s' % spider)
    log.info('Removing previous events in db')
    events.remove({'bookieName': spider})
    log.info('Call spider...')
    res = call(['scrapy', 'crawl', spider])

log.info('Hunt for some arbs...')
# Finally search for some juicy arbs
# Delete arbs in db for these bookies
with conn:
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM arbs_tab WHERE bookie_name = any(%s)' % tuple(spiders))
    except psycopg2.ProgrammingError:
        # table doesn't exist
        pass
res = call(['./findarbs.py', ])
