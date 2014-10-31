from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


# Need UK VPN and bo-navigation (c.f. betfred)
class StanjamesSpider(Spider):

    name = "Stanjames"
    allowed_domains = ["stanjames.com"]

    # Visit the football homepage first
    # to set session cookies
    def start_requests(self):
        url = ('http://www.stanjames.com/UK/541/betting#bo-navigation='
               '58974.2,153744.2&action=market-group-list')
        yield Request(url=url, callback=self.pre_parse_countries)

    def pre_parse_countries(self, response):
        # Make request to GET XML with all country market ids
        base_url = 'http://www.stanjames.com/cache/boNavigationList/541/UK/58974.2.xml'
        headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                   'Referer': 'http://www.stanjames.com/UK/541/betting'}
        yield Request(url=base_url, headers=headers, callback=self.parse_countries)

    def parse_countries(self, response):

        # Build ajax request that we'll use to request the country market group
        # ids (u'Bulgarian Football', u'58996.2') in XML format

        countryNames = response.xpath('//bonavigationnodes/bonavigationnode/name/text()').extract()
        mGroupIds = response.xpath('//bonavigationnodes/bonavigationnode/idfwbonavigation/text()').extract()
        # Geep only English Football, etc..
        country_pairs = [(country, id) for (country, id) in zip(countryNames, mGroupIds)
                         if country.endswith('Football')]

        headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                   'Referer': 'http://www.stanjames.com/UK/541/betting'}
        for pair in country_pairs:
            # for each marketId (i.e. each country) built ajax GET request, to
            # receive back leagues for that country in XML format.
            base_url = 'http://www.stanjames.com/cache/boNavigationList/541/UK/'+str(pair[1])+'.xml'
            yield Request(url=base_url, headers=headers, callback=self.parse_leagues)

    def parse_leagues(self, response):

        # Build ajax request that we'll use to request the league market group
        # ids (u'Bulgarian Football', u'58996.2') in XML format
        # leagueNames = response.xpath('//marketgroups//marketgroup/name/text()').extract()
        leagueIds = response.xpath('//marketgroups//marketgroup/idfwmarketgroup/text()').extract()
        headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                   'Referer': 'http://www.stanjames.com/UK/541/betting'}
        for id in leagueIds:
            # for each marketId (i.e. each league) built ajax GET request, to
            # receive back event data for that league in XML format. (lightMarketGroup
            # has no price data)
            base_url = 'http://www.stanjames.com/cache/MarketGroup/UK/'+str(id)+'.xml'
            yield Request(url=base_url, headers=headers, callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        eventSelection = response.xpath('//markets//market')
        items = []
        for event in eventSelection:

            l = EventLoader(item=EventItem2(), response=response)
            l.add_value('sport', u'Football')
            l.add_value('bookie', self.name)

            dateTime = take_first(event.xpath('tsstart/text()').extract())
            l.add_value('dateTime', dateTime)

            eventName = take_first(event.xpath('eventname/text()').extract())
            if eventName:
                teams = eventName.lower().split(' v ')
                l.add_value('teams', teams)

            MOdict = {'marketName': 'Match Odds', 'runners': []}
            runners = event.xpath('selections//selection')
            for runner in runners:
                runType = runner.xpath('hadvalue/text()').extract()
                odd_up = runner.xpath('currentpriceup/text()').extract()
                odd_down = runner.xpath('currentpricedown/text()').extract()
                if odd_up and odd_down:
                    if runType == [u'H']:
                        MOdict['runners'].append({'runnerName': 'HOME',
                                                 'price': odd_up[0]+'/'+odd_down[0]})
                    elif runType == [u'D']:
                        MOdict['runners'].append({'runnerName': 'DRAW',
                                                 'price': odd_up[0]+'/'+odd_down[0]})
                    elif runType == [u'A']:
                        MOdict['runners'].append({'runnerName': 'AWAY',
                                                 'price': odd_up[0]+'/'+odd_down[0]})

            l.add_value('markets', [MOdict, ])

            items.append(l.load_item())
        return items
