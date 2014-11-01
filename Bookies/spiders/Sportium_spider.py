from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
# import locale
take_first = TakeFirst()


class SportiumSpider(Spider):
    '''
    The fun quirk with this spider is that dates are abbreviated Spanish
    months, e.g. 'abr' for April. Set locale temporarily.
    N.B. need support on Ubuntu first `sudo locale-gen es_ES.UTF-8`
    '''
    name = "Sportium"
    allowed_domains = ["sportium.es"]

    # Visit the football homepage first
    def start_requests(self):
        yield Request(url='http://sports.sportium.es/es/football',
                      callback=self.parse_leagues
                      )

    def parse_leagues(self, response):

        league_links = response.xpath('//li[@data-title="Soccer"]/ul/li/ul/li/'
                                      'a/@href').extract()
        base_url = 'http://sports.sportium.es'
        headers = {'Host': 'sports.sportium.es',
                   'Referer': 'http://sports.sportium.es/es/football',
                   }
        for link in league_links:
            yield Request(url=base_url+link, headers=headers, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        events = response.xpath('//tr[starts-with(@class, "mkt mkt-")]')
        base_url = 'http://sports.sportium.es'
        headers = {'Host': 'sports.sportium.es',
                   'Referer': response.url,
                   }
        for event in events:
            moreLink = take_first(event.xpath('td[@class="mkt-count"]/a/@href').extract())
            # N.B. format is '29 abr' or '29 abril'
            dateTime = take_first(event.xpath('td[starts-with(@class, "time")]/'
                                              'div/span[@class="date"]/text()').extract())
            # Pass dateTime in meta since not available on detail page.
            yield Request(url=base_url+moreLink, headers=headers,
                          meta={'dateTime': dateTime}, callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.context['spiderlocale'] = 'es_ES.utf8'  # Set Spanish locale for dates
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = response.meta['dateTime']
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[@class="breadcrumbs-content"]/'
                                              'ul/li[@class="last-item"]/a/text()').extract())
        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # Markets
        # N.B. even appending ?show_all=Y to url still means unexpanded markets
        # need additional get market requests. Not worth it for now.
        mkts = response.xpath('//div[starts-with(@class, "expander ")]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('h6/span/text()').extract())
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt.xpath('div[@class="expander-content"]/table/tbody/tr/td')
            for runner in runners:
                runnername = take_first(runner.xpath('div/button/span/'
                                                     'span[@class="seln-name" or @class="seln-sort"]/'
                                                     'span/text()').extract())
                price = take_first(runner.xpath('div/button/span/'
                                                'span[@class="price dec"]/'
                                                'text()').extract())
                if runnername and price:
                    mdict['runners'].append({'runnerName': runnername, 'price': price})
            if mdict['marketName'] and mdict['runners']:
                allmktdicts.append(mdict)

        # Do some Sportium specific post processing and formating
        for mkt in allmktdicts:
            if '1-X-2' == mkt['marketName']:
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0] in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1] in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'X' == runner['runnerName']:
                        runner['runnerName'] = 'DRAW'
            elif 'Marcador exacto' == mkt['marketName']:
                mkt['marketName'] = 'Correct Score'
            elif 'Descanso/Final del Partido' == mkt['marketName']:
                mkt['marketName'] = 'HALF-TIME/FULL-TIME'

        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
