from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


class WilliamhillSpider(Spider):

    name = "Williamhill"
    allowed_domains = ["williamhill.com"]
    start_urls = ["http://sports.williamhill.com/bet/en-gb/betting/y/5/et/Football.html"]

    def parse(self, response):
        league_links = response.xpath('//ul[@class="matrixB"]/li/ul/li/a')
        league_pairs = [(take_first(l.xpath('@href').extract()), take_first(l.xpath('text()').extract()))
                        for l in league_links if not linkFilter(self.name, take_first(l.xpath('text()').extract()))]

        headers = {'Host': 'sports.williamhill.com',
                   'Referer': 'http://sports.williamhill.com/bet/en-gb/betting/y/5/et/Football.html',
                   }
        for pair in league_pairs:
            yield Request(url=pair[0], headers=headers, callback=self.parse_match)

    def parse_match(self, response):
        eventSelection = response.xpath('//table[@class="tableData"]/tbody/tr')

        if (response.url.endswith('Outright.html') or response.url.endswith('Trophy.html')):
            # Not interested, bail.
            # Can't filter this earlier, because of redirect name change of link.
            return []

        items = []
        for event in eventSelection:
            log.msg('Going to parse data for URL: %s' % response.url[20:],
                    level=log.INFO)

            l = EventLoader(item=EventItem2(), response=response)
            l.add_value('sport', u'Football')
            l.add_value('bookie', self.name)

            if response.meta.get('redirect_times') is not None:
                # WilliamHill redirects for markets with single event, must handle differently.
                log.msg('Scraping redirected site: %s' % response.url)

                dateTime = take_first(response.xpath('//div[@id="contentHead"]/'
                                                     'span[@id="eventDetailsHeader"]/nobr/'
                                                     'span/text()').extract())
                if not dateTime:
                    dateTime = ''
                l.add_value('dateTime', dateTime)

                team1 = take_first(event.xpath('td[1]/div/div[@class="eventselection"]/text()').extract())
                team2 = take_first(event.xpath('td[3]/div/div[@class="eventselection"]/text()').extract())
                if team1 and team2:
                    l.add_value('teams', [team1, team2])

            else:
                dateTime = take_first(event.xpath('td[1]/span/text()|td[1]/text()').extract())
                if not dateTime:
                    # Could be Live
                    dateTime = ''
                l.add_value('dateTime', dateTime)
                eventName = take_first(event.xpath('td[3]/a/span/text()').extract())
                if eventName:
                    teams = eventName.lower().split(' v ')
                    l.add_value('teams', teams)

            # MO market is same either way
            MOdict = {'marketName': 'Match Odds'}
            home_price = take_first(event.xpath('td[5]/div/div[@class="eventprice"]/text()').extract())
            draw_price = take_first(event.xpath('td[6]/div/div[@class="eventprice"]/text()').extract())
            away_price = take_first(event.xpath('td[7]/div/div[@class="eventprice"]/text()').extract())
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
