from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.spider import Spider
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
from Bookies.help_func import linkFilter
import re
take_first = TakeFirst()


class SportingbetSpider(Spider):
    name = "Sportingbet"
    allowed_domains = ["sportingbet.com"]

    # Visit the football homepage first, and get
    # some session cookies
    # def start_requests(self):
    #     yield Request(
    #     url ='http://www.sportingbet.com/services/Multiples.mvc/GetMostPopularSelections' ,
    #     callback=self.i_am_human
    #     )

    # def i_am_human(self,response):
    #     #Looks like Sportingbet have a new 'this-is-human' cookie, set by some js
    #     #The min working cURL is :
    #     #curl 'http://www.sportingbet.com/services/CouponTemplate.mvc/GetCoupon?couponAction
    #     #=EVENTCLASSCOUPON&sportIds=102&marketTypeId=&eventId=&bookId=&eventClassId=737635&sportId=102&eventTimeGroup=ETG_NextFewHours_0_0'
    #     # -H 'Cookie: this-is-human=QNDdscQWhtbhfDIJ4sp17fGLjkaEylIMHMAnsGoBBt9wemrgwfWwEKOySIDbzjMmTh7fOM49AAAAAQ==;'  --compressed
    #     #We can get this cookie simply enough from the redirect html itself!

    #     sel = Selector(response)

    #     human_script = sel.xpath('//body/script/text()').extract()
    #     cookie_line = human_script[0].splitlines()[1].strip()[:-1] #drop final js ';'
    #     human_cookie=cookie_line.split(';')[0]
    #     regex=re.compile(r"this-is-human=(?P<val>.+)")
    #     r = regex.search(human_cookie)
    #     vals = r.groupdict()
    #     try:
    #         cookies={'this-is-human': vals['val']}
    #     except KeyError as e:
    #         print "[ERROR %s]: \033[7m\033[31m KeyError: getting i-am-human cookie \033[0m" % (self.name)
    #         print "[ERROR %s]: \033[7m\033[31m challenge resp dump: %s" % (self.name, response.body)
    #         exit

    #     # With the challenge met, now request leagues
    #     # and proceed as usual
    #     base_url='http://www.sportingbet.com/sports-football/0-102-410.html'
    #     req=Request(url=base_url, cookies=cookies, callback=self.parse_leagues)
    #     req.meta['cookies']=cookies
    #     yield req

    # Looks like the ditched the i-am-human crap?
    def start_requests(self):
        yield Request(url='http://www.sportingbet.com/sports-football/0-102-410.html',
                      callback=self.parse_leagues
                      )

    def parse_leagues(self, response):

        sx = SgmlLinkExtractor(allow=[r'http://www.sportingbet.com/sports-football/'
                                      '[A-Za-z0-9-]+/1-102-\d+.html'
                                      ])

        league_links = sx.extract_links(response)

        # Remove unwanted links, returns True to filter out link
        league_links = [link for link in league_links
                        if not linkFilter(self.name, link.url)]

        eventClassIdList = []
        # Extract eventClassId from the link.url with regex
        for link in league_links:
            matches = re.findall(r'http://www.sportingbet.com/sports-football/'
                                 '[A-Za-z0-9-]+/1-102-(\d+?).html', link.url)
            if matches:
                eventClassIdList.append(matches[0])

        base_url = 'http://www.sportingbet.com/services/CouponTemplate.mvc/GetCoupon'
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'Referer': 'http://www.sportingbet.com/sports-football/0-102-410.html',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Host': 'www.sportingbet.com',
                   }
        # cookies =response.meta['cookies']
        for id in eventClassIdList:
            # Build GETstr
            GETstr = '?couponAction=EVENTCLASSCOUPON&'
            GETstr += 'sportIds=102&'
            GETstr += 'marketTypeId=&'
            GETstr += 'eventId=&'
            GETstr += 'bookId=&'
            GETstr += 'eventClassId='+str(id)+'&'
            GETstr += 'sportId=102&'
            GETstr += 'eventTimeGroup=ETG_NextFewHours_0_0'
            # make req

            yield Request(url=base_url+GETstr, headers=headers,
                          meta={'eventClassId': str(id)},
                          callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        # get eventClassId from meta
        eventClassId = response.meta['eventClassId']
        # Now using this and getting eventId make reqs for each event

        base_url = 'http://www.sportingbet.com/services/MarketTemplate.mvc/GetCoupon?'
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                   'Host': 'www.sportingbet.com',
                   'Referer': response.url,
                   'X-Requested-With': 'XMLHttpRequest',
                   }
        events = response.xpath('//div[@class="couponEvents"]/div[starts-with(@id, "e_")]')
        for event in events:
            eventId = take_first(event.xpath('@id').extract())
            eventId = eventId.replace('e_', '')
            # Detail page no datetime so pass on as meta
            dateTime = take_first(event.xpath('div[@class="columns"]/'
                                              'div[@class="eventInfo"]/'
                                              'span[@class="StartTime"]/'
                                              'text()').extract())
            GETstr = 'couponAction=EVALLMARKETS&sportIds=102&marketTypeId=&'
            GETstr += ('eventId=%s&bookId=&eventClassId=%s&sportId=102&eventTimeGroup='
                       % (eventId, eventClassId))
            yield Request(url=base_url+GETstr, headers=headers,
                          meta={'dateTime': dateTime}, dont_filter=True,
                          callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url, level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = response.meta['dateTime']
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//h2[@class="AllBetsEventName"]/'
                                              'text()').extract())
        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        mkts = response.xpath('//li[starts-with(@class, "m_item")]')
        # N.B. just like a filesystem path we go upward with '..', after
        # we find the ones with Match Result only
        MOdict = {'marketName': 'Match Odds', 'runners': []}
        MOrunners = mkts.xpath('./span[starts-with(@class, "headerSub")]/'
                               'span[text()="Match Prices"]/../../'
                               'ul')

        # MO prices
        home_price = take_first(MOrunners.xpath('.//div[@class="odds home"]/'
                                                'div[@id="isOffered"]/'
                                                'a/span[@class="priceText wide  UK"]/text()').extract())

        draw_price = take_first(MOrunners.xpath('.//div[@class="odds draw"]/'
                                                'div[@id="isOffered"]/'
                                                'a/span[@class="priceText wide  UK"]/text()').extract())
        away_price = take_first(MOrunners.xpath('.//div[@class="odds away"]/'
                                                'div[@id="isOffered"]/'
                                                'a/span[@class="priceText wide  UK"]/text()').extract())
        MOdict['runners'] = [{'runnerName': 'HOME',
                             'price': home_price},
                             {'runnerName': 'DRAW',
                              'price': draw_price},
                             {'runnerName': 'AWAY',
                              'price': away_price},
                             ]

        # Correct Score
        CSdict = {'marketName': 'Correct Score', 'runners': []}
        CSresults = mkts.xpath('./span[starts-with(@class, "headerSub")]/'
                               'span[text()="Correct Score"]/../../'
                               'ul//div[@class="m_event"]')
        CSdict = {'marketName': 'Correct Score', 'runners': []}
        for result in CSresults:
            # type i.e. home draw or away (used to decide whether needs reversing)
            CStype = take_first(result.xpath('div[@class="results"]/'
                                             'div[starts-with(@id, "s_")]/@class').extract())
            runnerName = take_first(result.xpath('div[@class="description"]/@title').extract())
            price = take_first(result.xpath('div[@class="results"]/'
                                            'div[starts-with(@id, "s_")]/'
                                            'div[@id="isOffered"]/a/'
                                            'span[@class="priceText wide  UK"]/text()').extract())
            if runnerName and price:
                if 'away' in CStype:
                    # Tag for score reversing by loader (e.g. if Team2 1-0 want
                    # just 0-1 to match Betfair format and avoid team name comp)
                    CSdict['runners'].append({'runnerName': runnerName,
                                              'price': price, 'reverse_tag': True})
                else:
                    CSdict['runners'].append({'runnerName': runnerName,
                                              'price': price, 'reverse_tag': False})

        # Add markets
        l.add_value('markets', [MOdict, CSdict])

        # Load item
        return l.load_item()
