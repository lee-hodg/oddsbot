from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()

#
#  It seems that Interwetten has a cookie system that persists
#  the state of leagues you selected so far. This is a pain,
#  as it means after visiting say Prem league then serie-A, you
#  end up with not just serie-A but also Prem league, then duplicate scrape.
#  1) Vist all links with HEAD method of req to just set cookies,
#     then scrape data on last link, when cookies set should ensure
#     we get a page with all the leagues visited so far.
#     (works pretty well but could the HEAD req get me banned?)
#  2) Pop the _lb cookie that keeps track after each league.
#  3) The new method here instead makes the mosts of the `select all`
#     method from the fussball page of leagues, which just captures league ids
#     from input checkboxes and requests them all at once as usual.
#


class InterwettenSpider(Spider):

    # Custom settings for Interwetten to stop timeouts
    download_timeout = 40  # Make this longer than settings for Interwetten
    download_delay = 1
    max_concurrent_requests = 2

    name = "Interwetten"
    allowed_domains = ["interwetten.com"]
    start_urls = ['https://www.interwetten.com/en/sportsbook/o/10/fussball']

    #  First get the league links
    def parse(self, response):

        log.msg('Grabbing all checkbox ids..')
        cbids = response.xpath('//table[@id="TBL_Content_Leagues"]'
                               '/tr/td/input/@id').extract()
        leagueids = [cbid[2:] for cbid in cbids]  # drop cb prefix
        leaguenames = response.xpath('//table[@id="TBL_Content_Leagues"]'
                                     '/tr/td/a/text()').extract()
        lpairs = zip(leagueids, leaguenames)
        # Remove unwanted links, returns True to filter out link
        leagueids = [id for (id, name) in lpairs
                     if not linkFilter(self.name, name)]

        base_url = 'https://www.interwetten.com/en/SportsBook/Betting/BettingOffer.aspx'
        GETstr = '?leagueid='+','.join(leagueids)+'&type=0&ogPreselect=1'
        headers = {'Host': 'www.interwetten.com',
                   'Referer': 'https://www.interwetten.com/en/sportsbook/o/10/fussball',
                   }

        yield Request(url=base_url+GETstr, headers=headers,
                      callback=self.parse_ListMatches, dont_filter=True)

    def parse_ListMatches(self, response):

        log.msg('Now on page with all matches, grab more bets links then traverse',
                level=log.INFO)
        links = response.xpath('//table[starts-with(@id, "TBL_Content_")]/'
                               'tr/td[@class="more"]/a/@href').extract()
        headers = {'Host': 'www.interwetten.com',
                   'Referer': response.url, }
        for link in links:
            yield Request(url='https://www.interwetten.com'+link,
                          headers=headers, callback=self.parseEvent)

    def parseEvent(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//table[starts-with(@id, "TBL_Content")]/'
                                             'tr[1]/td[@class="playtime"]/p/text()').extract())

        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//td[@class="colmiddle"]/div[@class="bets shadow"]'
                                              '/h2[@class="header gradient"]/'
                                              'span[@class="text"]/span/text()').extract())

        if eventName:
            teams = eventName.lower().split(' - ')
            l.add_value('teams', teams)

        # MO market first
        # Get table associated with the td that has a p with text "Match"
        # (remember xpath .. means move up just like linux fs)
        MOdict = {'marketName': 'Match Odds'}
        MOtable = response.xpath('//tr/td[@class="bets"]/p[@class="info"]'
                                 '[text()="Match"]/../table')
        home_price = take_first(MOtable.xpath('tr/td[1]/p/strong/text()').extract())
        draw_price = take_first(MOtable.xpath('tr/td[2]/p/strong/text()').extract())
        away_price = take_first(MOtable.xpath('tr/td[3]/p/strong/text()').extract())
        MOdict['runners'] = [{'runnerName': 'HOME',
                             'price': home_price},
                             {'runnerName': 'DRAW',
                              'price': draw_price},
                             {'runnerName': 'AWAY',
                              'price': away_price},
                             ]

        # CS market
        CSdict = {'marketName': 'Correct Score', 'runners': []}
        CStable = response.xpath('//tr/td[@class="bets"]/p[@class="info"]'
                                 '[text()="Correct Score"]/../table')
        CSresults = CStable.xpath('tr/td/p')
        for result in CSresults:
            # Deal with ':' in name in loaders
            runnerName = take_first(result.xpath('span/text()').extract())
            price = take_first(result.xpath('strong/text()').extract())
            CSdict['runners'].append({'runnerName': runnerName,
                                      'price': price, 'reverse_tag': False})

        # Add markets
        l.add_value('markets', [MOdict, CSdict])

        # Load item
        return l.load_item()
