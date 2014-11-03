#!/usr/bin/env python
from twisted.internet import reactor
from scrapy.crawler import Crawler
from scrapy import log
from Bookies.spiders.Coral_spider import CoralSpider
from Bookies.spiders.BGbet_spider import BGbetSpider
from Bookies.spiders.Apollobet_spider import ApollobetSpider
from scrapy.utils.project import get_project_settings


def setup_crawler(spider):
    settings = get_project_settings()
    crawler = Crawler(settings)
    crawler.configure()
    crawler.crawl(spider)
    return crawler

spider1 = CoralSpider()
spider2 = BGbetSpider()
spider3 = ApollobetSpider()
c1 = setup_crawler(spider1)
log.start()
print 'setup1'
print 'reactor.run()'
c1.start()
setup_crawler(spider3)
print 'setup3'

# This is event loop handler, cannot be restarted (should only be ran once)
reactor.run()
