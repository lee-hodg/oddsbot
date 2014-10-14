# from sqlalchemy import create_engine, Column, Integer, String, Date, Time, Float
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.engine.url import URL
#
# import settings
#
#
# DeclarativeBase = declarative_base()
#
#
# def db_connect():
#     """
#     Performs database connection using database settings from settings.py.
#     Returns sqlalchemy engine instance
#     """
#     return create_engine(URL(**settings.DATABASE))
#
#
# def create_deals_table(engine):
#     """"""
#     DeclarativeBase.metadata.create_all(engine)
#
#
# class ThreeWayEvents(DeclarativeBase):
#     """Sqlalchemy threeway events model"""
#     __tablename__ = "threeway_events"
#
#     id = Column(Integer, primary_key=True)
#     sport = Column('sport', String)
#     market = Column('market', String)
#     bookie = Column('bookie', String)
#     exchange = Column('exchange', String)
#     date = Column('date', Date)
#     time = Column('time', Time, nullable=True)
#     eventName = Column('Event Name', String)
#     odd1 = Column('odd1', Float, nullable=True)
#     odd2 = Column('odd2', Float, nullable=True)
#     odd3 = Column('odd3', Float, nullable=True)
#
