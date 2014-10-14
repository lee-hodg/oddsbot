# Scrapy settings for WH project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'Bookies'

SPIDER_MODULES = ['Bookies.spiders']
NEWSPIDER_MODULE = 'Bookies.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0"
#USER_AGENT = "Mozilla/5.0 (compatible; MSIE 10.6; Windows NT 6.1; Trident/5.0; InfoPath.2; SLCC1; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET CLR 2.0.50727) 3gpp-gba UNTRUSTED/1.0"
#USER_AGENT = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36"

DOWNLOAD_HANDLERS = {'http': 'scrapy.core.downloader.handlers.http10.HTTP10DownloadHandler'}


#I added all below to try and rotate USER AGENT STRING:
USER_AGENT_LIST=["Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0",
		"Mozilla/5.0 (compatible; MSIE 10.6; Windows NT 6.1; Trident/5.0; InfoPath.2; SLCC1; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET CLR 2.0.50727) 3gpp-gba UNTRUSTED/1.0",
		"Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36",
		"Mozilla/5.0 (Windows NT 5.2; RW; rv:7.0a1) Gecko/20091211 SeaMonkey/9.23a1pre",
		"Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/4.0; GTB7.4; InfoPath.3; SV1; .NET CLR 3.1.76908; WOW64; en-US)",
		"Mozilla/5.0 (X11; Linux) KHTML/4.9.1 (like Gecko) Konqueror/4.9",
		"Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36",
		"Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1467.0 Safari/537.36",
		"Mozilla/5.0 (X11; CrOS i686 3912.101.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36",
		"Mozilla/5.0 (Windows; U; Windows NT 5.1; pt-BR) AppleWebKit/534.8 (KHTML, like Gecko) Navscape/Pre-0.2 Safari/534.8",
		"Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)"]
#Note (see DOWNLOADER_MIDDLEWARES_BASE, middle ware is number 400. Num determines order of exec)
DOWNLOADER_MIDDLEWARES = {
 'Bookies.random_user_agent.RandomUserAgentMiddleware': 400,                     #use custom (at 400 number like normal)
 'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,      #disable built in
 }

DOWNLOAD_TIMEOUT = 20 #default 180
RETRY_TIMES = 1 #default 2

# COOKIES_DEBUG=True

# Make sure mongodb writing occurs after duplicates
ITEM_PIPELINES = {
    'Bookies.pipelines.BookiesPipeline': 300,
    'scrapy_mongodb.MongoDBPipeline': 800,
}

MONGODB_URI = 'mongodb://localhost:27017'
MONGODB_DATABASE = 'oddsbot_scrapy'
MONGODB_COLLECTION = 'events'
MONGODB_ADD_TIMESTAMP = True   # append timestamp when adding item

import os
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIRNAME = PROJECT_ROOT.split(os.sep)[-1]
LOG_DIR = os.path.join(PROJECT_ROOT, '..', 'logs')
# LOG_FILE = os.path.join(LOG_DIR,'scrapy_out.log')


EXTENSIONS = {
     #'scrapy.contrib.statsmailer.StatsMailer':500,
     'Bookies.errorstatsmailer.ErrorStatsMailer' : 500,
}

STATSMAILER_RCPTS = ['webmaster@oddsbot.co.uk']

# N.B. `RANDOMIZE_DOWNLOAD_DELAY` is True by default anyway
# but `DOWNLOAD_DELAY` is also 0 by default, meaning by default there is no
# delay at all. After setting `DOWNLOAD_DELAY` the scraper will wait between
# 0.5 and (1.5 * DOWNLOAD_DELAY) each time.
# You can also change setting per spider by setting the `download_delay` attrb.
# of spider (see Betsson)
DOWNLOAD_DELAY = 0.6

# Database settings (attempt with postgresql backend)
# DATABASE = {'drivername': 'postgres',
#             'host': 'localhost',
#             'port': '5432',
#             'username': 'postgres',
#             # 'password': '',
#             'database': 'bookie_scrape'}

try:
    from local_settings import *
except ImportError:
    pass
