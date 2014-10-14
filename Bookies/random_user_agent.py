# You can use this middleware to have a random user agent every request the spider makes.
# You can define a user USER_AGENT_LIST in your settings and the spider will chose a random user agent from that list every time.
# 
# You will have to disable the default user agent middleware and add this to your settings file.
# 
#     DOWNLOADER_MIDDLEWARES = {
#         'scraper.random_user_agent.RandomUserAgentMiddleware': 400,
#         'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
#     }

from Bookies.settings import USER_AGENT_LIST
import random
from scrapy import log

class RandomUserAgentMiddleware(object):
    
    def process_request(self, request, spider):
        ua  = random.choice(USER_AGENT_LIST)
        if ua:
            request.headers.setdefault('User-Agent', ua)
        log.msg('>>>> UA %s'%request.headers)


