import sqlite3
from datetime import datetime

class FinanceDatabase:
	def __init__(self, filename, table):

		self.db = sqlite3.connect(filename, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
		self.c = self.db.cursor()

		self.table = table
		self.create()

	def create(self):
		self.c.execute("CREATE TABLE IF NOT EXISTS " + self.table + "(id INTEGER PRIMARY KEY, symbol TEXT, date TIMESTAMP, close REAL, UNIQUE(symbol, date))")
		self.db.commit()

	def insert(self, symbol, date, close):
		self.c.execute("INSERT OR IGNORE INTO " + self.table + "(symbol, date, close) VALUES(?,?,?)", (symbol, date, close))
		self.db.commit()

	def insertAll(self, symbol, date, close):
		self.c.executemany("INSERT OR IGNORE INTO " + self.table + "(symbol, date, close) VALUES(?,?,?)", [[symbol, d, c] for d, c in zip(date, close)])
		self.db.commit()

	def fetchAll(self, symbol):
		self.c.execute("SELECT date, close FROM " + self.table + " WHERE symbol=? ORDER BY date ASC", (symbol, ))
		for row in self.c.fetchall():
			print('%s, $%.2f' % row)

	def close(self):
		self.db.close()
