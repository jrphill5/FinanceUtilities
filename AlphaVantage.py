import requests, pandas, os, sys
from matplotlib.dates import num2date, date2num
from datetime import datetime, timedelta

from avapi import apikey
import BasicFinance, FinanceDatabase, FinancePlot

class AlphaVantage:
	def __init__(self, symbol, dts = datetime.now() - timedelta(days=365), dte = datetime.now(), nl = 10, nh = 30):
		self.bf = BasicFinance.BasicFinance()
		self.fd = FinanceDatabase.FinanceDatabase(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'finance.db'), 'AlphaVantage')

		self.symbol = symbol
		
		self.dts = dts
		self.dte = dte

		self.nl = nl
		self.nh = nh

		# Create datetime object for the actual start time accounting for loss due to moving average:
		self.dd = (self.dte-self.dts).days
		self.dtp = self.dte - timedelta(days=self.dd+7.0/5.0*self.nh+self.dd/30.0*3.0) # Take weekends and holidays into account

		self.head = None
		self.data = None

		self.update()

	def update(self):
		if not self.fetchData():
			self.downloadData()

	def getData(self):
		return self.data

	def fetchData(self):
		return False
		# Attempt to read in data from database:
		#stored = self.fd.fetchAll(self.symbol)
		#if stored is None: return False

		# Define data structure for holding quote information:
		#data = { 'Date':     [], 'Open':     [], 'High':     [],
		#         'Low':      [], 'Close':    [], 'CloseAdj': [],
		#         'Volume':   [], 'Dividend': [], 'Split':    []  }

		# Populate data structure with information from database:
		#for d, c in zip(stored['Date'], stored['Close']):
		#	if d >= self.dtp and d <= self.dte:
		#		data['Date'].append(d)
		#		data['CloseAdj'].append(c)

		# Determine expected and actual trading days:
		#acts = [d.strftime('%D') for d in data['Date']]
		#exps = [d.strftime('%D') for d in self.bf.getTradingDays(self.dtp, self.dte)]

		# If not equal, data is missing, so download:
		#if acts == exps:
		#	self.data = data
		#	return True
		#else:
		#	return False

	# Send values to remote webserver and download CSV reply:
	def downloadData(self):
		url    = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=' + self.symbol + '&outputsize=full&apikey=' + apikey
		params = {'function': 'TIME_SERIES_DAILY_ADJUSTED', 'symbol': self.symbol, 'outputsize': 'full', 'apikey': apikey}
		resp   = requests.get(url, params=params)

		if resp.status_code == 200:
			# Read in JSON from response:
			raw  = resp.json()

			# Define date format used by Alpha Vantage
			datefmt = '%Y-%m-%d'

			# Store header and generate dict of lists for data:
			head = { 'Info':     raw['Meta Data']['1. Information'],
			         'Symbol':   raw['Meta Data']['2. Symbol'],
					 'Updated':  datetime.strptime(raw['Meta Data']['3. Last Refreshed'], datefmt),
					 'Output':   raw['Meta Data']['4. Output Size'],
					 'TimeZone': raw['Meta Data']['5. Time Zone']       }
			data = { 'Date':     [], 'Open':     [], 'High':     [],
			         'Low':      [], 'Close':    [], 'CloseAdj': [],
			         'Volume':   [], 'Dividend': [], 'Split':    []  }

			# Populate data structure with information in JSON response:
			for k, v in sorted(raw['Time Series (Daily)'].items()):
				date = datetime.strptime(k, datefmt)
				if date >= self.dtp and date <= self.dte:
					data['Date'].append(     date)
					data['Open'].append(     float(v['1. open']))
					data['High'].append(     float(v['2. high']))
					data['Low'].append(      float(v['3. low']))
					data['Close'].append(    float(v['4. close']))
					data['CloseAdj'].append( float(v['5. adjusted close']))
					data['Volume'].append(   int(  v['6. volume']))
					data['Dividend'].append( float(v['7. dividend amount']))
					data['Split'].append(    float(v['8. split coefficient']))

			# Store this data in the object:
			self.head = head
			self.data = data

			# Insert information into database:
			#self.fd.insertAll(self.symbol, self.data['Date'], self.data['CloseAdj'])
		
		else:
			self.data = None

	def printLatestCrossover(self, fund, crossovers):
		print()
		print(fund + ' fund latest crossover:')
		if crossovers:
			s, (t, p) = crossovers[-1]
			if s: sys.stdout.write('  B ')
			else: sys.stdout.write('  S ')
			dtc = self.bf.getNextTradingDay(num2date(t))
			sys.stdout.write(dtc.strftime('%m/%d/%Y ('))
			days = len(self.bf.getTradingDays(dtc, datetime.now().date()-timedelta(days=1)).tolist())
			sys.stdout.write(str(days))
			sys.stdout.write('|')
			sys.stdout.write(str(self.bf.daysSince(dtc)))
			sys.stdout.write(' days ago) @ $')
			sys.stdout.write('{0:.2f}'.format(p))
			return days == 0
		else:
			sys.stdout.write('  None within ' + str(self.dd) + ' days!')
			return False

if __name__ == "__main__":

	if len(sys.argv) < 2:
		symbols = ['SWTSX', 'SWISX']
	else:
		symbols = sys.argv[1:]

	symbols = [s.upper() for s in symbols]

	# Define image path in same directory as this script:
	imgpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images', 'av')

	for smb in symbols:
		av = AlphaVantage(smb)
		data = av.getData()

		# If data cannot be retreived, exit the program with an error:
		if data is None:
			print("Could not retrieve data from remote server for %s." % smb)
			continue

		# Plot all Alpha Vantage symbols:
		fp = FinancePlot.FinancePlot('Alpha Vantage', av.dd, imgpath)

		# Plot symbol and the SMAs and signals:
		fp.plotSignals(av, data['Date'], data['CloseAdj'], 0, smb, 'EWMA', av.head['Updated'])
