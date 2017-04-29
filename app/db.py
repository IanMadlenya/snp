import os
from datetime import timedelta, date
from contextlib import contextmanager

import quandl
from quandl.errors.quandl_error import NotFoundError
import psycopg2
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import exists, func
from sqlalchemy.orm import sessionmaker


Session = sessionmaker()
Base = declarative_base()


def connect():
    """ connect to the database """
    if os.environ.get('ENV_MODE') == 'test':
        db = 'testsnp'
    else:
        db = 'snp'

    engine = create_engine("postgresql://{0}@{1}:5432/{2}".format(
        os.environ.get('DB_USER'),
        os.environ.get('DB_HOST'),
        db))
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)
    engine.connect()


@contextmanager
def session_scope():
    """ generator for handling sessions for database interactions"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        print  e
        session.rollback()
    finally:
        session.close()


class OHLCV(Base):
    __tablename__ = 'ohlcv'

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    symbol = Column(String)
    open = Column(String)
    high = Column(String)
    low = Column(String)
    close = Column(String)
    volume = Column(String)


def symbol_exists(symbol):
    """ check if the stock symbol exists in the database """
    return session.query(exists().where(OHLCV.symbol==symbol))[0]


def get_recent_ohlvc(symbol):
    """ get the last 10 days of data for a stock symbol """
    lastTenDays = []
    with session_scope() as session:
        data = session.query(OHLCV). \
            filter_by(symbol=symbol). \
            order_by(OHLCV.date.desc()). \
            limit(10)

    for day in data:
        dayDict = dict(
            date=day.date,
            symbol=day.symbol,
            open=day.open,
            high=day.high,
            low=day.low,
            close=day.close,
            volume=day.volume
            )
        lastTenDays.append(dayDict)

    return lastTenDays


def get_recent_data_date(symbol):
    """ get the most recent date that we have daily stock data """
    start_date = ''
    with session_scope() as session:
        for date in session.query(func.max(OHLCV.date)). \
                            filter_by(symbol=symbol):
            if date[0]:
                start_date = date[0]
    return start_date


def save_stock_data(data, symbol):
    """ save daily stock data """
    with session_scope() as session:
        for record in data.itertuples():
            session.add(OHLCV(symbol=symbol,
                date=record[0],
                open=record[1],
                high=record[2],
                low=record[3],
                close=record[4],
                volume=record[5]))
        session.flush()


def drop_ohlcv_table():
    """ drop ohlcv data but only when using the test database """
    assert os.environ.get('ENV_MODE') == 'test', 'Not using test database, but trying to drop the ohlvc table'
    with session_scope() as session:
        OHLCV.__table__.drop()


def need_recent_data(symbol):
    """ do we have stock data from the most recent business day? """
    today = date.today()
    weekday = today.isoweekday()
    recent_data_date = get_recent_data_date(symbol)
    if weekday == 6: # is today saturday?
        last_data_day = today - timedelta(days=1)
    elif weekday == 7: # is today sunday?
        last_data_day = today - timedelta(days=2)
    else:
        last_data_day = today
    delta_date = recent_data_date - last_data_day
    return delta_date != timedelta(0)


def is_valid_symbol(symbol):
    try:
        quandl.get("YAHOO/{}".format(symbol), row=1)
        return True
    except NotFoundError:
        return False
