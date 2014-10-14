# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
# import cleaner

from scrapy.exceptions import DropItem
from scrapy.conf import settings
LOG_DIR = settings['LOG_DIR']


class BookiesPipeline(object):
    #
    # Primary function is to drop duplicates
    # If eventName and eventDate and eventTime match
    # we consider it to be a duplicate.
    #

    def __init__(self):
        self.events_seen = set()

    def process_item(self, item, spider):

        # Firstly, require eventName, eventDate key and markets
        if ('teams' not in item.keys() or 'dateTime' not in item.keys() or 'markets' not in item.keys()):
            raise DropItem('[WARNING %s]: \033[7m\033[31m No teams'
                           ' or no dateTime or no markets'
                           ' so junked \033[0m' % spider.name)

        teams = item['teams']
        dateTime = item['dateTime']

        # Drop events with no teams
        if len(teams) == 0:
            raise DropItem('[WARNING %s]: \033[7m\033[31m No teams vals found'
                           'so junked \033[0m' % spider.name)

        # Drop duplicates
        if tuple(teams)+(dateTime, ) in self.events_seen:
            raise DropItem('[WARNING %s]: \033[7m\033[31m Duplicate item found:'
                           ' (%s,%s) \033[0m'
                           % (spider.name, teams, dateTime))
        else:
            # add tuple to already seen set
            self.events_seen.add(tuple(teams)+(dateTime, ))

        return item
