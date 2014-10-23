from scrapy.spider import Spider
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
import datetime
import re
take_first = TakeFirst()


class ApollobetSpider(Spider):
    name = "Apollobet"

    # The initial visit to /Betting will set X-mapping nd SessionId
    # cookies, but it is only when the sports tab is clicked that it calls
    # the js function ShowSports('') and in turn this sets cookie with
    # SetCookie func seensplash-sports=1 with exp date of 30 days
    start_urls = ['http://www.apollobet.com/Betting']

    def parse(self, response):
        # Set the seen-splash cookie
        yield Request(url="http://www.apollobet.com/Betting",
                      cookies={'seensplash-sports': '1'},
                      headers={'Referer': 'http://www.apollobet.com/Betting'},
                      callback=self.pre_parse_countries)

    def pre_parse_countries(self, response):

        stamp = datetime.datetime.now().time().strftime('%H%M%S')

        # Make request for league links
        base_url = 'http://www.apollobet.com/SportsBook/GetMenuItem'
        GETstr = ('?navigationID=127797.1&level=2&name=A%20-%20Z&'
                  'parentName=23.1&parentNames=Football/&parentIds=23.1,')
        headers = {'Referer': 'http://www.apollobet.com/Betting/Football?navigationid=top,23.1&time=%s' % stamp,
                   'X-Requested-With': 'XMLHttpRequest'}

        # Scrapy seems to now take care of seensplash-sports cookie
        # and the __RequestVerificationToken_Lw__ cookie
        yield Request(url=base_url+GETstr,
                      # cookies={'seensplash-sports': '1'},
                      headers=headers,
                      callback=self.parse_countries)

    def parse_countries(self, response):

        # Get js onclick methods e.g.
        # u"expandMenu('127875.1','3','England','A - Z','Football/A_-_Z/','23.1,127797.1,')"
        # expandMenu(navID, menuLevel, name, parentName, parentNames, parentsIds) (see sportsbook.js?vers2.1)
        country_methods = response.xpath('//ul[@id="leftNav"]//li/span/a/@onclick').extract()
        p = re.compile(r"expandMenu\(\'(?P<navID>.+)\',\'(?P<menuLevel>.+)\'"
                       ",\'(?P<name>.+)\',\'(?P<parentName>.+)\',"
                       "\'(?P<parentNames>.+)\',\'(?P<parentIDs>.+)\'\)")
        countryList = []
        for c in country_methods:
            m = p.match(c)
            country = {}
            country['navID'] = m.group('navID')
            country['menuLevel'] = m.group('menuLevel')
            country['name'] = m.group('name')
            country['parentName'] = m.group('parentName')
            country['parentNames'] = m.group('parentNames')
            country['parentIDs'] = m.group('parentIDs')
            countryList.append(country)

        # For each country we make a further request to get submenu of leagues
        base_url = 'http://www.apollobet.com/SportsBook/GetMenuItem'
        headers = {'Referer': 'http://www.apollobet.com/Betting/Football?navigationid=top,23.1&time=160234',
                   'X-Requested-With': 'XMLHttpRequest'}

        for country in countryList:
            GETstr = '?navigationID='+country['navID']+'&level='+country['menuLevel']+'&name='+country['name']+'&'
            GETstr += 'parentName='+country['parentName']+'&parentNames='+country['parentNames']+'&parentIds='+country['parentIDs']
            yield Request(url=base_url+GETstr, headers=headers, callback=self.parse_leagues)

    def parse_leagues(self, response):

        stamp = datetime.datetime.now().time().strftime('%H%M%S')

        # We could do a similar thing now to traverse all leagues, but the matches href is sufficient
        matches_link = take_first(response.xpath('//ul[@id="leftNav"]//li/span/a/@href').extract())
        if matches_link:
            url = 'http://www.apollobet.com'+matches_link
            headers = {'Referer': 'http://www.apollobet.com/Betting/Football?navigationid=top,23.1&time=%s' % stamp}
            yield Request(url=url, headers=headers, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        base_url = 'http://www.apollobet.com/SportsBook/GetMoreMarkets?'
        headers = {'Referer': response.url,
                   'X-Requested-With': 'XMLHttpRequest'
                   }
        moreBets = response.xpath('//table[@class="markettable"]//tr'
                                  '/td[@class="betscol"]/span/@onclick').extract()

        p = re.compile(r"GetMoreMarkets\(\'(?P<eventID>.+)\',\'(?P<marketGroupID>.+)\',\'(?P<oddsType>.*)\'\);")
        for moreBet in moreBets:
            m = p.match(moreBet)
            eventID = m.group('eventID')
            markeGroupID = m.group('marketGroupID')
            oddsType = m.group('oddsType')
            GETstr = 'eventID=%s&marketGroupID=%s&oddsType=%s' % (eventID, markeGroupID, oddsType)
            yield Request(url=base_url+GETstr, headers=headers, dont_filter=True,
                          callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        # The dateTime scrape returns
        # [u'\r\n        ', u' - 7:45pm, 29th October\r\n        ']
        dateTime = response.xpath('//div[@class="match wide"]/'
                                  'div[@class="match-header"]'
                                  '/text()').extract()
        dateTime = ''.join([d.strip() for d in dateTime])
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[@class="match wide"]/'
                                              'div[@class="match-header"]/'
                                              'span[@class="teams"]/text()').extract())

        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # Get MO market
        MOmarket = response.xpath('//div[@id="MoreMarketMainDiv"]/div[@class="menugroupitem"]'
                                  '/div[2]/div[starts-with(@id,"market")]'
                                  '/table/tr[1]/th[text()="Match Betting"]/../../tr[2]')

        # MO prices
        MOdict = {'marketName': 'Match Odds'}
        home_price = take_first(MOmarket.xpath('td[1]/div[starts-with(@id, "input")]'
                                               '/p[@class="oddsbigbtn"]/text()').extract())
        draw_price = take_first(MOmarket.xpath('td[2]/div[starts-with(@id, "input")]'
                                               '/p[@class="oddsbigbtn"]/text()').extract())
        away_price = take_first(MOmarket.xpath('td[3]/div[starts-with(@id, "input")]'
                                               '/p[@class="oddsbigbtn"]/text()').extract())
        MOdict['runners'] = [{'runnerName': 'HOME',
                             'price': home_price},
                             {'runnerName': 'DRAW',
                              'price': draw_price},
                             {'runnerName': 'AWAY',
                              'price': away_price},
                             ]
        # CS market
        CSmarket = response.xpath('//div[@id="MoreMarketMainDiv"]/div[@class="menugroupitem"]'
                                  '/div[2]/div[starts-with(@id,"market")]'
                                  '/table/tr[1]/th[text()="Correct Score"]/../..')
        CSresults = CSmarket.xpath('tr/td/div[starts-with(@id, "input")]')
        CSdict = {'marketName': 'Correct Score', 'runners': []}
        for result in CSresults:
            price = take_first(result.xpath('p[@class="oddsbigbtn"]/text()').extract())
            runnerName = take_first(result.xpath('p[2][not(@class="oddsbigbtn")]/text()').extract())
            # log.msg('runnerName %s and price %s' % (runnerName, price), level=log.DEBUG)
            # stop = raw_input('e2c')
            if runnerName and price:
                if teams[1] in runnerName.lower():
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
