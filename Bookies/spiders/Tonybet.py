from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


class TonybetSpider(Spider):

    name = "Tonybet"

    # Visit the football homepage first
    def start_requests(self):
        yield Request(url='https://tonybet.com/football',
                      callback=self.parseLeague)

    def parseLeague(self, response):
        # Probably most efficient to scrape all tournIds
        # then build one big request for all leagues
        # after filtering bad leagues.

        lnames = response.xpath('//li[@id="sport_2"]/div[@class="subCategories"]'
                                '/ul/li/label/text()').extract()
        lids = response.xpath('//li[@id="sport_2"]/div[@class="subCategories"]'
                              '/ul/li/input/@id').extract()
        # checkboxTournament_5406 is format of lids, chop:
        lids = [id[19:] for id in lids]
        # Make pairs for easy filtering
        lpairs = zip(lnames, lids)

        lids = [lid for (lname, lid) in lpairs
                if not linkFilter(self.name, lname)]

        # Build request for leagues
        base_url = 'https://tonybet.com/cached_sports/football?'
        GETstr = 'country=gb&eo_format=eu&'
        for lid in lids:
            GETstr += 'tournaments_ids[]=%s&' % lid
        GETstr += 't=t'
        headers = {'Referer': 'https://tonybet.com/football',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Host': 'tonybet.com'}
        yield Request(url=base_url+GETstr, headers=headers,
                      callback=self.pre_parseData)

    def pre_parseData(self, response):

        # First row is just league heading,and you want to exclude
        # 'sep' class rows.
        eventSelection = response.xpath('//table[@class="events singleRow"]/tr'
                                        '[position()>1][not(@class="sep")]')
        base_url = 'https://tonybet.com'
        headers = {'Host': 'tonybet.com',
                   'Referer': 'https://tonybet.com/football',
                   }
        for event in eventSelection:
            moreLink = take_first(event.xpath('td[@class="showAll"]/a/@href').extract())
            yield Request(url=base_url+moreLink, headers=headers, callback=self.parseData)

    def parseData(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//table[@class="liveEventInfo"]/tr/td/'
                                             'h1/span[@class="clock"]/text()').extract())
        # Remove the (#686) stuff
        dateTime = dateTime[:dateTime.find('(')]
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//table[@class="liveEventInfo"]/'
                                              'tr/td/h1/text()').extract())
        if eventName:
            teams = eventName.lower().split('vs.')
            l.add_value('teams', teams)

        # Markets
        marketNames = response.xpath('//div[@id="event-filters"]/'
                                     'h3[@class="capsTableHead"]/text()').extract()
        # Sometimes a single row head gives an extra blank
        marketNames = [mName.strip() for mName in marketNames if mName.strip()]
        marketContent = response.xpath('//div[@id="event-filters"]/table')
        mkts = zip(marketNames, marketContent)
        allmktdicts = []
        for mkt in mkts:
            marketName = mkt[0]
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt[1].xpath('tr/td')
            for runner in runners:
                runnername = runner.xpath('./text()').extract()
                runnername = take_first([rName.strip() for rName in runnername if rName.strip()])
                handicapname = take_first(runner.xpath('em[@class="purple"]/text()').extract())
                if handicapname:
                    runnername += ' '+handicapname.strip()
                price = take_first(runner.xpath('span/text()').extract())
                mdict['runners'].append({'runnerName': runnername, 'price': price})
            allmktdicts.append(mdict)

        # Do some Tonybet specific post processing and formating
        for mkt in allmktdicts:
            if '2-3 Way' in mkt['marketName']:
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0].strip() in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1].strip() in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'X' == runner['runnerName']:
                        runner['runnerName'] = 'DRAW'
        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
