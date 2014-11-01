from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from Bookies.help_func import linkFilter
from scrapy.http import Request
from scrapy.http import FormRequest
import json
take_first = TakeFirst()


class Bet188Spider(Spider):

    name = "Bet188"
    allowed_domains = ["188bet.co.uk"]

    # Sets ASP.NET_SessionId, sscd2 cookies
    # The response is basically the nav bar at top, footer,
    # css and some js vars.
    start_urls = ['http://www.188bet.co.uk/en-gb/sports']

    def parse(self, response):

        '''
        The next request. This sets an extra two empty
        cookies, mc, HighlightedSport, and adds
        ssc.SB with same val as sscd2.

        Looks like content is loaded from iframe:
        This has the empty <div id="tab-Menu" class=""> div, and some js
        that looks like it will fill it.
        Other than this there are some <!--templates--> 'textareas' which look like they may
        parse some variables from json, and build the HTML to go in the rel areas.
        e.g.  <!--Sport Menu-->
        '''

        # Lets load this to at the very least get some more cookies.
        # NB Referer same as req URL.
        base_url = ('http://sb.188bet.co.uk/en-gb/sports?theme=black&'
                    'q=&country=GB&currency=GBP&tzoff=-240')
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Referer': ('http://sb.188bet.co.uk/en-gb/sports?theme=black&'
                               'q=&country=GB&currency=GBP&tzoff=-240')
                   }

        yield Request(url=base_url, headers=headers,
                      callback=self.pre_leagues, dont_filter=True)

    def pre_leagues(self, response):

        # This should be the 'money request' for league data and comp ids:
        base_url = 'http://sb.188bet.co.uk/en-gb/Service/CentralService?GetData'
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Referer': 'http://sb.188bet.co.uk/en-gb/sports/1/select-competition/default'
                   }

        # Versions seem to change each time I get the cURL?
        # cURL shows form really needs nothing except reqUrl
        # ,referer header and ASP.NET and ssc.SB cookies
        # NB make sure you send url decoded here:
        formdata = {'reqUrl': '/en-gb/sports/1/select-competition/default'}
        # Need to make a post req (multi req to same url, dont_filter needed)
        yield FormRequest(url=base_url, formdata=formdata, headers=headers,
                          callback=self.parse_leagues, dont_filter=True)

    def parse_leagues(self, response):

        # Extract the needed params from the JSON response
        try:
            jResp = json.loads(response.body)
        except:
            log.msg('lostconn perhaps?', level=log.ERROR)
            log.msg('response dump: \n%s' % response.body, level=log.ERROR)
            yield []

        # Load the string from the mod key into json
        jsonCountries = json.loads(jResp['mod'])

        # Reap the comp ids (cids) (keep name too for filter)
        cids = [(comp['n'], comp['id']) for country in jsonCountries
                for comp in country['c']]

        # Filter the comps
        cids = [(cname, cid) for (cname, cid) in cids if not
                linkFilter(self.name, cname)]

        base_url = 'http://sb.188bet.co.uk/en-gb/Service/CentralService?GetData'
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                   'X-Requested-With': 'XMLHttpRequest'}

        for (name, cid) in cids:
            # Seems the referer also gets set to requested cid.
            # Would be nice if there was a way to test if 1x2 avail before making req,
            # otherwise in parse_Data there will be no keys needed.
            formdata = {'reqUrl': '/en-gb/sports/1/competition/1x2?competitionids='+str(cid)+'&'}
            headers['Referer'] = 'http://sb.188bet.co.uk/en-gb/sports/1/competition/1x2?competitionids='+str(cid)
            yield FormRequest(url=base_url, formdata=formdata, headers=headers,
                              meta={'league_name': name},
                              callback=self.parse_Data, dont_filter=True)

    def parse_Data(self, response):
        '''
        All the data is returned for different markets here, not just 1x2,
        so in theory should be relatively easy to upgrade to more markets
        '''
        # Get the league data we passed as arg through meta
        league_name = response.meta['league_name']

        log.msg('Going to parse data for league: %s' % league_name)

        # Parse JSON from body
        try:
            jResp = json.loads(response.body)
        except ValueError as e:
            log.msg(e, level=log.ERROR)
            log.msg('Response body not JSON for league: %s' % league_name)
            log.msg('response.body dump: \n%s' % response.body)

        # Traverse JSON
        try:
            if 'mod' in jResp.keys():
                jsonMOD = json.loads(jResp['mod'])
            else:
                log.msg("'mod' key not found for league: %s" % league_name)
                log.msg('jResp key dump: %s' % jResp.keys())
                return []
            # Data
            if 'd' in jsonMOD.keys():
                jsonData = jsonMOD['d']
            else:
                log.msg("'d' key not found for league: %s" % league_name)
                log.msg('jsonMOD key dump: %s ' % jsonMOD.keys())
                return []
            # Competitions, it seems if no 1x2 there won't be a c key.
            if 'c' in jsonData.keys():
                jsonComps = jsonData['c']
            else:
                log.msg("'c' key not found for league: %s" % league_name)
                log.msg('jsonData key dump: %s' % jsonData.keys())
                # It looks like jsonMOD['bt'] lists the mkt types avail for sel btn at top,so check with that:
                log.msg("No 1x2 mkt? jsonMOD['bt'] check: %s" % jsonMOD['bt'])
                return []

            # Events (I load the only one comp at once so safe to take zeroth)
            jsonEvents = jsonComps[0]['e']

        except KeyError as e:
            log.msg(e, level=log.ERROR)
            log.msg('Error response or 404? No 1x2 mkts? For league: %s' % league_name)
            return []

        items = []
        for jsonEvent in jsonEvents:

            l = EventLoader(item=EventItem2(), response=response)
            l.add_value('sport', u'Football')
            l.add_value('bookie', self.name)

            dateTime = jsonEvent['i'][4]  # u'09 / 06'
            l.add_value('dateTime', dateTime)

            homeName = jsonEvent['i'][0]
            awayName = jsonEvent['i'][1]
            if homeName and awayName:
                teams = [homeName, awayName]
                l.add_value('teams', teams)
            # MO prices
            MOdict = {'marketName': 'Match Odds'}
            home_price = jsonEvent['o']['1x2'][1]
            draw_price = jsonEvent['o']['1x2'][5]
            away_price = jsonEvent['o']['1x2'][3]
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
