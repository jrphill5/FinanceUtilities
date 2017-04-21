import requests, pandas, os, sys
from matplotlib.dates import date2num, num2date
from datetime import datetime, timedelta
from io import StringIO

import BasicFinance, FinanceDatabase, FinancePlot

class ThriftSavingsPlan:
	def __init__(self, fund, dts = datetime.now() - timedelta(days=365), dte = datetime.now(), nl = 10, nh = 30):
		self.bf = BasicFinance.BasicFinance()
		self.fd = FinanceDatabase.FinanceDatabase(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'finance.db'), 'ThriftSavingsPlan')

		self.fund = fund

		self.dts = dts
		self.dte = dte

		self.nl = nl
		self.nh = nh

		# Create datetime object for the actual start time accounting for loss due to moving average:
		self.dd = (self.dte-self.dts).days
		self.dtp = self.dte - timedelta(days=self.dd+7.0/5.0*self.nh+self.dd/30.0*3.0) # Take weekends and holidays into account

		self.data = None

		self.update()

	def update(self):
		if not self.fetchData():
			self.downloadData()

	def getData(self):
		return self.data

	def fetchData(self):
		data = self.fd.fetchAll(self.fund)
		if data is None: return False

		data[self.fund] = data.pop('Close')

		dateFormat = '%D'

		ret = True

		for act, exp in zip(data['Date'], [ts.to_pydatetime() for ts in self.bf.getFederalTradingDays(self.dtp, self.dte)]):
			if act.strftime(dateFormat) != exp.strftime(dateFormat):
				ret = False

		if ret: self.data = data

		return ret

	# POST values to remote webserver and download CSV reply:
	def downloadData(self):
		dateFormat = '%m/%d/%Y'
		url = 'https://www.tsp.gov/InvestmentFunds/FundPerformance/index.html'
		data = {'whichButton': 'CSV', 'startdate': self.dtp.strftime(dateFormat), 'enddate': self.dte.strftime(dateFormat)}
		response = requests.post(url, data=data)

		if response.status_code == 200:
			# Read in dataframe from CSV response and sort by date:
			df = pandas.read_csv(StringIO(response.text))
			df['date'] = pandas.to_datetime(df['date'], format='%Y-%m-%d')
			df = df.sort_values('date')

			# Clean up text in dataframe and create a dictionary:
			data = {}
			for k, v in df.to_dict('list').items():
				kn = k.strip()
				if len(kn) > 0:
					data[kn] = v

			# Convert Pandas timestamps to datetime objects:
			data['Date'] = [ts.to_pydatetime() for ts in data['date']]
			del data['date']

			self.data = data

			for k, v in data.items():
				if k == 'Date': continue
				self.fd.insertAll(k, self.data['Date'], self.data[k])

		else:
			self.data = None

	def printLatestCrossover(self, fund, crossovers):
		print()
		print(fund + ' latest crossover:')
		if crossovers:
			s, (t, p) = crossovers[-1]
			if s: sys.stdout.write('  B ')
			else: sys.stdout.write('  S ')
			dtc = self.bf.getNextFederalTradingDay(num2date(t))
			sys.stdout.write(dtc.strftime('%m/%d/%Y ('))
			days = len(self.bf.getFederalTradingDays(dtc, datetime.now().date()-timedelta(days=1)).tolist())
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
		funds = ['G', 'F', 'C', 'S', 'I']
	else:
		funds = sys.argv[1:]

	funds = [fund + ' Fund' for fund in funds]

	# Define image path in same directory as this script:
	imgpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images', 'tsp')

	for fund in funds:
		TSP = ThriftSavingsPlan(fund)
		data = TSP.getData()

		# If data cannot be retreived, exit the program with an error:
		if data is None:
			print("Could not retrieve data from remote server.")
			continue

		# Plot all TSP funds:
		fp = FinancePlot.FinancePlot('Thrift Savings Plan', TSP.dd, imgpath)
		#fp.plotFunds(data, ['G Fund', 'F Fund', 'C Fund', 'S Fund', 'I Fund'])

		# Plot each TSP fund and their SMAs and signals:
		fp.plotSMASignals(TSP, data['Date'], data[fund], 0, fund)
