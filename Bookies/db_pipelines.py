# # Define your item pipelines here
# #
# # Don't forget to add your pipeline to the ITEM_PIPELINES setting
# # See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
# # import cleaner
#
# import os
# from scrapy.conf import settings
# LOG_DIR = settings['LOG_DIR']
# from sqlalchemy.orm import sessionmaker
# from models import Events, db_connect, create_events_table
#
#
# class DBPipeline(object):
#     '''
#     Write scraped data to database
#     '''
#
#     def __init__(self):
# 	'''
# 	Init db connection and sessionmaker
# 	create table
# 	'''
#      	engine = db_connect()
#         create_deals_table(engine)
#         self.Session = sessionmaker(bind=engine)
#         self.events_seen = set()
#
#     def process_item(self, item, spider):
#        """Save events in the database.
#
#         This method is called for every item pipeline component.
#
#         """
#         session = self.Session()
#         event = Events(**item)
#
#         try:
#             session.add(event)
#             session.commit()
#         except:
#             session.rollback()
#             raise
#         finally:
#             session.close()
#
#         return item
