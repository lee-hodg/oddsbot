from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
import json
import re
take_first = TakeFirst()

# Another bpsgameserver like Dhoze and Betsson.


class DhozeSpider(Spider):
    name = "Dhoze"
    allowed_domains = ["dhoze.com", "bpsgameserver.com"]

    # Set session cookie
    start_urls = ['https://apostas.dhoze.com/en/']

    # First make the leagues request to bpsgameserver
    def parse(self, response):

        base_url = ('https://sbfacade.bpsgameserver.com/'
                    'PlayableMarketService/PlayableMarketServicesV2.svc/'
                    'jsonp/FetchLeftMenuJSONP?')
        GETstr = 'unique=15_39_&segmentId=501&languageCode=en&callback=_jqjsp'

        yield Request(url=base_url+GETstr, callback=self.parse_leagues)

    def parse_leagues(self, response):

        # Extract the needed params from the JSON response
        # JSON is between _jqjsp(....); so extract with regex
        matches = re.findall(r'_jqjsp\((.+?)\);', response.body)
        if matches:
            jsonResp = json.loads(matches[0])

        # Now we have the left sidebar in JSON format,
        # get needed football league ids
        idList = []
        for country in jsonResp['FetchLeftMenuJSONPResult']['c_c'][0]['sc_r']:
            for league in country['sc_c']:
                # print league['i_c'], league['mc'], league['n'], league['rid']
                idList.append(league['i_c'])
        base_url = ('https://sbfacade.bpsgameserver.com/PlayableMarketService/'
                    'PlayableMarketServicesV2.svc/jsonp/'
                    'FetchPrematchFullMarketsWithSortOrderJSONP?')
        for id in idList:
            # 'unique' param looks like it is set in the jquery script
            # (http://jsbeautifier.org/ is nice to search these scripts)
            # It seems to increase with each req, but for now I leave fixed,
            # seems fine. segmentid seems always fixed.
            # I increase noOfEventsPerPageMain to 200
            # (as is possible on the drop down).
            GETstr = "unique=15_48_&subCategoryIds="+str(id)+"&segmentid=201&languageCode=en&clientTimeZone=UTC%2B02.00&"
            GETstr += "noOfEventsPerPageProView=50&noOfEventsPerPageMain=200&noOfEventsPerPagePopular=50&"
            GETstr += "noOfEventsPerPage1stHalf=50&noOfEventsPerPageHandicap=50&noOfEventsPerPageGoals=50&"
            GETstr += "noOfEventsPerPageSpecials=50&noOfEventsPerPageOutrights=50&noOfhrsForStartingSoon=0&callback=_jqjsp"
            # Arguably we should inc referer in the header here. Seems to work without
            # might have to work on this in future if becomes a prob
            yield Request(url=base_url+GETstr, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        # JSON is between _jqjsp(....); so extract with regex
        matches = re.findall(r'_jqjsp\((.+?)\);', response.body)
        if matches:
            jsonResp = json.loads(matches[0])

        try:
            jsonData = jsonResp['FetchPrematchFullMarketsWithSortOrderJSONPResult']['mmEv']['mListEvts']
        except KeyError as e:
            log.msg('KeyError: %s' % (self.name, e), level=log.ERROR)
            log.msg('Error response or 404?' % (self.name), level=log.ERROR)
            log.msg('response dump: %s ' % (self.name, jsonResp), level=log.ERROR)
            yield []

        base_url = ('https://sbfacade.bpsgameserver.com/PlayableMarketService/'
                    'PlayableMarketServicesV2.svc/jsonp/'
                    'FetchPrematchEventMarketsByEventIdJSONP')

        # After mListEvts the events are in a list ordered by date
        for eventBlock in jsonData:
            for event in eventBlock['PrmEvts']:

                eid = event['Id']
                sid = event['SubCategoryId']
                GETstr = ('?unique=0_0_&subcategoryId=%s&eventId=%s&'
                          'languageCode=en&segmentid=501&callback=_jqjsp' % (sid, eid))
                yield Request(url=base_url+GETstr, callback=self.parseData)

    def parseData(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        # JSON is between _jqjsp(....); so extract with regex
        matches = re.findall(r'_jqjsp\((.+?)\);', response.body)
        if matches:
            jsonResp = json.loads(matches[0])

        try:
            jsonData = jsonResp['FetchPrematchEventMarketsByEventIdJSONPResult']
        except KeyError as e:
            log.msg('KeyError: %s' % (self.name, e), level=log.ERROR)
            log.msg('Error response or 404?' % (self.name), level=log.ERROR)
            log.msg('response dump: %s ' % (self.name, jsonResp), level=log.ERROR)
            return []

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = jsonData['DeadlineUTC']
        l.add_value('dateTime', dateTime)

        eventName = jsonData['Name']
        if eventName:
            teams = eventName.lower().split(' - ')
            l.add_value('teams', teams)

        # Markets
        mkts = jsonData['Markets']
        allmktdicts = []
        for mkt in mkts:
            marketName = mkt['Name']
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt['Selections']
            for runner in runners:
                runnername = runner['Name']
                price = runner['Odds']
                mdict['runners'].append({'runnerName': runnername, 'price': price})
            allmktdicts.append(mdict)

        # Do some Dhoze specific post processing and formating
        for mkt in allmktdicts:
            if mkt['marketName'] == 'Match Winner':
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if runner['runnerName'] == u'1':
                        runner['runnerName'] = 'HOME'
                    elif runner['runnerName'] == u'2':
                        runner['runnerName'] = 'AWAY'
                    elif runner['runnerName'] == u'X':
                        runner['runnerName'] = 'DRAW'
        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
