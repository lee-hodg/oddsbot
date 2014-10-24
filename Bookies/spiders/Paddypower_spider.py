from scrapy.spider import Spider
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
import json
take_first = TakeFirst()

#
# The data seems to come with the initial GET request,
# but it is stored in the `lb_fb_cpn_init(...)` function
# , which presumably creates some HTML from it. Thus we seem
# to have two choices: 1) rip the JSON like data from between
# the <script> tags of the initial GET, then parse them with some
# python, or 2) use Selenium webdriver to get the js version of the
# response (slow)
#


class PaddypowerSpider(Spider):
    name = "Paddypower"
    allowed_domains = ["paddypower.com"]

    start_urls = ['http://www.paddypower.com/football/football-matches']

    # First get the league links
    def parse(self, response):
        # Get leagues from script (this saves all junk from quicknav)
        all_scripts = response.xpath('//script')
        wanted_script = take_first([script for script in all_scripts
                                    if 'fb_hp_other_nav_ls_init' in script.extract()])
        jsonLeaguesData = json.loads(wanted_script.extract().splitlines()[6][:-1])
        headers = {'Host': 'www.paddypower.com',
                   'Referer': 'http://www.paddypower.com/football/football-matches',
                   }
        for league in jsonLeaguesData:
            if 'coupon_url' in league.keys():
                # not an solely outright competition
                link = league['coupon_url']
                yield Request(url=link, headers=headers, callback=self.pre_parseData)

    def pre_parseData(self, response):

        all_scripts = response.xpath('//script')
        wanted_script = take_first([script for script in all_scripts
                                    if 'lb_fb_cpn_init' in script.extract()])

        jsonEventsData = json.loads(wanted_script.extract().splitlines()[14][:-1])
        headers = {'Host': 'www.paddypower.com',
                   'Referer': response.url,
                   }
        for event in jsonEventsData:
            moreLink = event['url']
            yield Request(url=moreLink, headers=headers, callback=self.parseData)

    def parseData(self, response):
        log.msg('Going to parse data for URL: %s' % response.url, level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//div[@class="time"]/text()').extract())
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[starts-with(@class, "super-nav-left")]/'
                                              'ul/li[1]/a/span[1]/text()').extract())
        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # Markets
        # Markets are duplicated
        allMktDicts = []
        already_seen = set()
        # First get id and name then later get prices for this marketId
        mkts = response.xpath('//div[starts-with(@id, "contents_mkt_id")]')
        for mkt in mkts:
            marketId = take_first(mkt.xpath('@data-ev-mkt-id').extract())
            if not marketId:
                continue
            if marketId in already_seen:
                continue
            else:
                already_seen.add(marketId)

            marketName = take_first(mkt.xpath('h3/a/span[@class="sub_market_name"]/text()').extract())
            mDict = {'marketName': marketName, 'runners': []}
            # Now using marketId get prices (note sometimes the market is listed
            # several times (e.g. in top markets and win markets say) so we just
            # take the first in list.
            mktData = take_first(response.xpath('//div[starts-with(@class, "fb-market-content")]/'
                                                'div[@class="fb-sub-content" and @data-ev-mkt-id="%s"]' % marketId))
            runners = mktData.xpath('div[@class="fb-odds-group item"]/span[@class="odd"]/a')
            for runner in runners:
                runnerName = take_first(runner.xpath('span[@class="odds-label"]/text()').extract())
                price = take_first(runner.xpath('span[@class="odds-value"]/text()').extract())
                mDict['runners'].append({'runnerName': runnerName,
                                         'price': price,
                                         })

            allMktDicts.append(mDict)

        # Do some PP specific post processing and formating
        for mkt in allMktDicts:
            if 'Win-Draw-Win' in mkt['marketName'].strip():
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0] in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1] in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'Draw' in runner['runnerName']:
                        runner['runnerName'] = 'DRAW'
            elif 'Correct Score' == mkt['marketName'].strip():
                mkt['marketName'] = 'Correct Score'
                for runner in mkt['runners']:
                    if teams[1] in runner['runnerName'].lower():
                        runner['reverse_tag'] = True
                    else:
                        runner['reverse_tag'] = False

        # Add markets
        l.add_value('markets', allMktDicts)

        # Load item
        return l.load_item()
