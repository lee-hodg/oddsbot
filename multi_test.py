#!/usr/bin/env python
from twisted.internet import reactor
from scrapy.crawler import Crawler
from scrapy import log
from Bookies.spiders.Coral_spider import CoralSpider
from Bookies.spiders.BGbet_spider import BGbetSpider
from scrapy.utils.project import get_project_settings


def setup_crawler(spider):
    settings = get_project_settings()
    crawler = Crawler(settings)
    crawler.configure()
    crawler.crawl(spider)
    crawler.start()

spider1 = CoralSpider()
spider2 = BGbetSpider()
setup_crawler(spider1)
setup_crawler(spider2)
log.start()
reactor.run()