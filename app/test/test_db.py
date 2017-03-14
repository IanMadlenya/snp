import datetime

import psycopg2
import quandl

import db


SYMBOL = 'INDEX_GSPC'


def test_get_start_date_no_existing_data():
	""" Do I return none as a start date when there is no existing data?  """
	db.drop_ohlcv_table()
	assert db.get_start_date(SYMBOL) == None

def test_get_start_date_with_existing_data():
	""" Do I return the most recent date start date?  """
	test_ohlvc_data = quandl.get("YAHOO/{}".format(SYMBOL), start_date='2017-01-01', end_date='2017-02-01')
	db.save_stock_data(test_ohlvc_data, SYMBOL)
	assert db.get_start_date(SYMBOL) == datetime.date(2017, 2, 2)

