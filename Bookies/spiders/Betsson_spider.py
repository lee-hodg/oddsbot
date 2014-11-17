from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
import json
take_first = TakeFirst()


class BetssonSpider(Spider):
    '''
    Note compare this with Betssafe, Dhoze etc.
    Easy to expand to more markets in same way with one
    more JSON call. Don't have servers for extra load.
    '''
    # spider-specific delay
    # scrapy will mult by 0.5 and 1.5 to get low/upper
    # range for random delay.
    # A value of 2 makes the spider slow, but no timeout on test.
    download_delay = 0.4

    name = 'Betsson'
    allowed_domains = ['betsson.com', 'bpsgameserver.com']

    start_urls = ['https://sportsbook.betsson.com/en/']

    def parse(self, response):

        base_url = "https://sb.bpsgameserver.com"
        GETstr = "/?token=00000000-0000-0000-0000-000000000000&"
        GETstr += "sid=601&lc=en&tz=GMT+Standard+Time&dc=GBP&c=en-GB&"
        GETstr += "pagemenuheaderurl=https://sportsbook.betsson.com/en/PageMenuHeader.aspx&"
        GETstr += "mainpromourl=https://sportsbook.betsson.com/en/MainPromo.aspx&"
        GETstr += "articleurl=https://sportsbook.betsson.com/en/&"
        GETstr += "sidebarpromourl=https://sportsbook.betsson.com/en/SidebarPromo.aspx&"
        GETstr += "proxyurl=https://sportsbook.betsson.com/Script/Cross-frame/proxy.html&"
        GETstr += "minigamesurl=https://sportsbook.betsson.com/en/MiniGameLauncher.aspx"
        headers = {'Referer': 'https://sportsbook.betsson.com/en/',
                   'Host': 'sb.bpsgameserver.com'
                   }

        yield Request(url=base_url+GETstr, headers=headers, callback=self.parse_leagues)

    def parse_leagues(self, response):

        all_scripts = response.xpath('//script')
        wanted_script = take_first([script for script in all_scripts
                                    if 'firstLoadLeftMenuJsonData' in script.extract()])
        # Need to get the 'var firstLoadLeftMenuJsonData = ...' line (even though looks like many lines)
        # split on = then take after equals, then make valid JSON by chopping off start/end bits...
        wanted_line = take_first([line for line in wanted_script.extract().splitlines()
                                  if 'firstLoadLeftMenuJsonData' in line])
        jsonLeftMenu = json.loads(wanted_line.split('=', 1)[1][2:-2])

        # Get football menu
        footballMenu = take_first([menu for menu in jsonLeftMenu['FetchLeftMenuExtResult']['c_c']
                                   if menu['n'] == u'Football'])

        # Get sub-leagues, store as list of dicts of name, id.
        # since names may be useful for filtering later.
        leagueList = []
        for country in footballMenu['sc_r']:
            for league in country['sc_c']:
                leagueList.append(dict(name=league['n'], id=league['i_c']))

        base_url = ('https://sbfacade.bpsgameserver.com/PlayableMarketService/'
                    'PlayableMarketServicesV2.svc/json2/FetchBetGroupMatrixItems?')
        headers = {'Referer': 'https://sb.bpsgameserver.com/static/flash/json.swf?v=14.41.1',
                   'Host': 'sbfacade.bpsgameserver.com'
                   }
        # We will want bggi or betGroupGroupingID 36 for Match Winner only, not Outrights (143)
        # Trying an outright only subcat, e.g. England/Season Bets : subCategoryIDs=4863,
        # with bggi 36, will cause timeout? No just a null response.
        # First make request for matrix items, this tells us if Match Winner/36 is an option, if so hit it.
        for league in leagueList:
            GETstr = 'segmentId=601&languageCode=en&subCategoryIds='+str(league['id'])
            yield Request(url=base_url+GETstr, headers=headers,
                          meta={'league': league}, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):
        # Get the league data we passed as arg through meta
        league = response.meta['league']

        # Is Match Winner an option? or just outrights.
        jResp = json.loads(response.body)
        jData = jResp['FetchBetGroupMatrixItemsResult']

        headers = {'Referer': 'https://sb.bpsgameserver.com/static/flash/json.swf?v=14.41.1',
                   'Host': 'sbfacade.bpsgameserver.com'}
        base_url = ('https://sbfacade.bpsgameserver.com/PlayableMarketService/'
                    'PlayableMarketServicesV2.svc/json2/FetchSubcategoryBetgroupGroupings?')
        hit = False
        for mkt in jData:
            if mkt['gn'] == u'Match Winner':
                # if group name 'Match Winner' is avail, hit it.
                hit = True
        if hit:
            GETstr = 'segmentId=601&languageCode=en&subCategoryIDs='+str(league['id'])
            GETstr += '&betGroupGroupingID=36&timeZoneStandardName=GMT Standard Time'
            yield Request(url=base_url+GETstr, headers=headers,
                          meta={'league': league}, callback=self.parse_Data)
        else:
            log.msg('Filtering (no Match Winner) league: %s' % league)
            yield None

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        league = response.meta['league']
        jsonResp = json.loads(response.body)
        jsonData = jsonResp['FetchSubcategoryBetgroupGroupingsResult']

        if jsonData == 'null':
            log.msg('Null response for leauge %s at site: %s' % (league, response.url),
                    level=log.ERROR)
            return None

        try:
            jsonEvents = jsonData['scbgg_c'][0]['m_c']
        except (KeyError, TypeError):
            log.msg('No events for league %s with id %s'
                    '. Is jsonData empty?'
                    % (league['name'].encode('utf-8'), league['id']), level=log.ERROR)
            log.msg(jsonData, level=log.ERROR)
            return None

        items = []
        for jsonEvent in jsonEvents:

            l = EventLoader(item=EventItem2(), response=response)
            l.add_value('sport', u'Football')
            l.add_value('bookie', self.name)

            dateTime = jsonEvent['dd']
            l.add_value('dateTime', dateTime)

            eventName = jsonEvent['n']
            if eventName:
                teams = eventName.lower().split(' - ')
                l.add_value('teams', teams)

            # MO prices
            MOdict = {'marketName': 'Match Odds'}
            home_price = draw_price = away_price = None
            for jsonOdd in jsonEvent['ms_c']:
                    if jsonOdd['dn'] == u'1':
                        home_price = jsonOdd['os']
                    elif jsonOdd['dn'] == u'X':
                        draw_price = jsonOdd['os']
                    elif jsonOdd['dn'] == u'2':
                        away_price = jsonOdd['os']
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

        if not items:
            items = None
        return items
