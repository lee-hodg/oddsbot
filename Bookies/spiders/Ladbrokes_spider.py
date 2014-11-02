from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
from scrapy.http import FormRequest
take_first = TakeFirst()


class LadbrokesSpider(Spider):

    name = "Ladbrokes"
    allowed_domains = ["ladbrokes.com"]

    # Visit the football homepage first to set the
    # session cookie required.
    # Needed for subsequent ajax requests, otherwise server rejects
    # (would need to use sessions in python requests lib).
    def start_requests(self):
        yield Request(url='http://sportsbeta.ladbrokes.com/football',
                      callback=self.request_links
                      )

    # Get the football countries (lower left menu under all sports)
    def request_links(self, response):
        base_url = 'http://sportsbeta.ladbrokes.com/view/LeftNavExpandSportsController'
        headers = {'Host': 'sportsbeta.ladbrokes.com',
                   'Pragma': 'no-cache',
                   'Referer': 'http://sportsbeta.ladbrokes.com/football',
                   'X-Requested-With': 'XMLHttpRequest'
                   }
        data = {'id': '110000006', 'type': 'eventclass'}
        yield FormRequest(url=base_url, headers=headers, formdata=data, dont_filter=True,
                          callback=self.parse_countries)

    def parse_countries(self, response):
        country_ids = response.xpath('//li/@id').extract()
        base_url = 'http://sportsbeta.ladbrokes.com/view/LeftNavExpandSportsController'
        headers = {'Host': 'sportsbeta.ladbrokes.com',
                   'Pragma': 'no-cache',
                   'Referer': 'http://sportsbeta.ladbrokes.com/football',
                   'X-Requested-With': 'XMLHttpRequest'
                   }
        for countryId in country_ids:
            data = {'id': countryId, 'type': 'eventtype'}
            yield FormRequest(url=base_url, headers=headers, formdata=data, dont_filter=True,
                              callback=self.parse_leagues)

    def parse_leagues(self, response):
        base_url = 'http://sportsbeta.ladbrokes.com'
        headers = {'Host': 'sportsbeta.ladbrokes.com',
                   'Referer': 'http://sportsbeta.ladbrokes.com/football',
                   }
        league_links = response.xpath('//li/a/@href').extract()
        for link in league_links:
            yield Request(url=base_url+link, headers=headers, callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        eventSelection = response.xpath('//table[contains(@class, "event-type")]/tbody/tr')

        items = []
        for event in eventSelection:

            l = EventLoader(item=EventItem2(), response=response)
            l.add_value('sport', u'Football')
            l.add_value('bookie', self.name)

            dateTime = take_first(event.xpath('td[2]/text()').extract())
            # Sometimes just a time 13:30 if date is Today, the following -> ''
            if dateTime:
                dateTime = dateTime.strip()[:-5]
            else:
                dateTime = 'Today'
            if not dateTime or dateTime == ' ':
                dateTime = 'Today'
            l.add_value('dateTime', dateTime)

            eventName = take_first(event.xpath('td[@class="event"]/a/span/text()').extract())
            if eventName:
                teams = eventName.lower().split(' v ')
                l.add_value('teams', teams)

            # MO prices
            MOdict = {'marketName': 'Match Odds'}
            home_price = take_first(event.xpath('td[5][@class="price"]/a/strong/text()').extract())
            draw_price = take_first(event.xpath('td[6][@class="price"]/a/strong/text()').extract())
            away_price = take_first(event.xpath('td[7][@class="price"]/a/strong/text()').extract())
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
