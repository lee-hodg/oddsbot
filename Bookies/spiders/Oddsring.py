from __future__ import division
from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from Bookies.help_func import linkFilter
from scrapy.http import Request
# from scrapy.conf import settings
# import datetime
# import pytz
# import urllib  # for encode with .quote
import re
take_first = TakeFirst()
# MY_IP = settings['MY_IP']

# def setCookie(cname, value=MY_IP, expire_days=10):
#     '''
#     Oddsring now sets a cookie via js (not headers) on init page
#     necessary to scrape the value, and use in this func
#     IP can only be obtained by external query, set static for now
#     '''
#     # Set aware tz.
#     dt = datetime.datetime.now(pytz.utc) + datetime.timedelta(days=expire_days)
#     # stamp = int(newday.strftime("%s"))*1000  #ms
#     # Infact ultimately want date formatted like Wed, 28 Jul 1993 09:09:07 UTC
#     expire_date = dt.strftime("%a, %d %b %Y %H:%M:%S %Z")
#     cookie = cname + "=" + urllib.quote(value) + ";expires=" + expire_date + ";path=/"
#     return cookie


class OddsringSpider(Spider):

    name = "Oddsring"

    # Overide usual delay with spider-specific attr
    # without some delay this server gets overwhelmed and starts giving 503
    # service unavail. This will also help not getting blocked.
    # see also max_concurrent_requests, which is a spider attr overriding
    # CONCURRENT_REQUESTS_PER_SPIDER(8 by default)
    download_delay = 1

    # Visit the homepage first
    def start_requests(self):
        yield Request(url='http://www.oddsring.com/',
                      callback=self.setupJScookie, dont_filter=True)

    def setupJScookie(self, response):
        wanted_script = take_first(response.xpath('//script').extract())
        wanted_line = wanted_script.splitlines()[-11]
        p = re.compile(r"setCookie\(\'(?P<cname>.+)\'\, \'(?P<value>.+)\'\, (?P<expire_days>\d+)\);")
        m = p.match(wanted_line)
        dico = m.groupdict()
        cname = None
        value = None
        if 'cname' in dico:
            cname = dico['cname']
        if 'value' in dico:
            value = dico['value']

        if cname and value:
            # cookie = {cname: setCookie(cname, value=value, expire_days=int(expire_days))}
            # Doesn't look like I can set a sticky cookie anyway, so no point in
            # expiry date, will need to resend each time with request manually
            cookie = {cname: value}
        else:
            cookie = None
            log.msg('Could not get either cname of value from init js cookie setter.',
                    level=log.ERROR)
            exit()

        # Add cookie and reload
        yield Request(url='http://www.oddsring.com/', cookies=cookie,
                      callback=self.parseLeague, dont_filter=True)

    def parseLeague(self, response):

        # If need to can access the last cookie you set with
        # request.headers.getlist('Cookie')

        lnames = response.xpath('//ul[@id="sb-sportlist"]/li[1]/ul[@id="lg1"]/li/'
                                'div[@class="line"]/a/text()').extract()
        links = response.xpath('//ul[@id="sb-sportlist"]/li[1]/ul[@id="lg1"]/li/'
                               'div[@class="line"]/a/@href').extract()

        # Make pairs for easy filtering
        lpairs = zip(lnames, links)
        links = [link for (lname, link) in lpairs
                 if not linkFilter(self.name, lname)]
        # Build request for leagues
        # I seem to be having a problem with cookies
        # If you make the request w.o them you get 302 redirect
        # , which is not being coped with well. How do I cope with it?
        # or why are the cookies not working consistently?
        headers = {'Referer': 'http://www.oddsring.com',
                   'Host': 'www.oddsring.com'
                   }
        for link in links:
            yield Request(url=link, headers=headers,
                          callback=self.parseData, dont_filter=True)

    def parseData(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        # First row is just league heading,and you want to exclude
        # 'sep' class rows.
        eventSelection = response.xpath('//table[@class="ComingUPTable"]/tr'
                                        '[position()>1][not(@class="moreEvent")]')
        items = []
        for event in eventSelection:
            l = EventLoader(item=EventItem2(), response=response)
            l.add_value('sport', u'Football')
            l.add_value('bookie', self.name)

            dateTime = take_first(event.xpath('td[2]/text()').extract())
            l.add_value('dateTime', dateTime)

            eventName = take_first(event.xpath('td[3]/div/a/text()').extract())
            if eventName:
                teams = eventName.lower().split(' - ')
                l.add_value('teams', teams)

            # MO prices
            MOdict = {'marketName': 'Match Odds'}

            home_price = take_first(event.xpath('td[starts-with(@class, "home")]/'
                                                'div[@class="val"]/a/text()').extract())

            draw_price = take_first(event.xpath('td[starts-with(@class, "draw")]/'
                                                'div[@class="val"]/a/text()').extract())

            away_price = take_first(event.xpath('td[starts-with(@class, "away")]/'
                                                'div[@class="val"]/a/text()').extract())
            MOdict['runners'] = [{'runnerName': 'HOME',
                                  'price': home_price},
                                 {'runnerName': 'DRAW',
                                  'price': draw_price},
                                 {'runnerName': 'AWAY',
                                  'price': away_price},
                                 ]

            # Add markets
            l.add_value('markets', [MOdict, ])

            # Load item
            items.append(l.load_item())

        return items
