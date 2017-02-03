import requests, pandas, os, sys
from matplotlib.dates import date2num, num2date
from datetime import datetime, timedelta
from io import StringIO

import BasicFinance, FinancePlot

class ThriftSavingsPlan:
	def __init__(self, dts = datetime.now() - timedelta(days=365), dte = datetime.now(), nl = 10, nh = 30):
		self.bf = BasicFinance.BasicFinance()

		self.dts = dts
		self.dte = dte

		self.nl = nl
		self.nh = nh

		# Create datetime object for the actual start time accounting for loss due to moving average:
		self.dd = (self.dte-self.dts).days
		self.dtp = self.dte - timedelta(days=self.dd+7.0/5.0*self.nh+self.dd/30.0*3.0) # Take weekends and holidays into account

		self.response = None
		self.data = None

		self.update()

	def update(self):
		self.fetchData()
		self.parseData()

	def getData(self):
		return self.data

	# POST values to remote webserver and download CSV reply:
	def fetchData(self):
		dateFormat = '%m/%d/%Y'
		url = 'https://www.tsp.gov/InvestmentFunds/FundPerformance/index.html'
		data = {'whichButton': 'CSV', 'startdate': self.dtp.strftime(dateFormat), 'enddate': self.dte.strftime(dateFormat)}
		self.response = requests.post(url, data=data)

	# Create a clean dictionary with all CSV info from the TSP:
	def parseData(self):
		if self.response.status_code == 200:
			# Read in dataframe from CSV response and sort by date:
			df = pandas.read_csv(StringIO(self.response.text))
			df['date'] = pandas.to_datetime(df['date'], format='%Y-%m-%d')
			df = df.sort_values('date')

			# Clean up text in dataframe and create a dictionary:
			data = {}
			for k, v in df.to_dict('list').items():
				kn = k.strip()
				if len(kn) > 0:
					data[kn] = v

			# Convert Pandas timestamps to datetime objects:
			data['date'] = [ts.to_pydatetime() for ts in data['date']]

			self.data = data
		else:
			self.data = None

	def printLatestCrossover(self, fund, crossovers):
		print()
		print(fund + ' fund latest crossover:')
		if crossovers:
			s, (t, p) = crossovers[-1]
			if s: sys.stdout.write('  B ')
			else: sys.stdout.write('  S ')
			sys.stdout.write(num2date(t).strftime('%m/%d/%Y ('))
			sys.stdout.write(str(self.bf.daysSince(num2date(t))).rjust(len(str(self.dd))))
			sys.stdout.write(' days ago) @ $')
			sys.stdout.write('{0:.2f}'.format(p))
			return self.bf.daysSince(num2date(t)) == 0
		else:
			sys.stdout.write('  None within ' + str(self.dd) + ' days!')
			return False

	def printAllCrossovers(self, fund, crossovers):
		print(fund + ' fund crossover points:')
		if crossovers:
			for s, (t, p) in crossovers:
				if s: sys.stdout.write('  B ')
				else: sys.stdout.write('  S ')
				sys.stdout.write(num2date(t).strftime('%m/%d/%Y ('))
				sys.stdout.write(str(self.bf.daysSince(num2date(t))).rjust(len(str(self.dd))))
				sys.stdout.write(' days ago) @ $')
				print('{0:.2f}'.format(p))
		else:
			print('  None within ' + str(dd) + ' days!')

if __name__ == "__main__":

	TSP = ThriftSavingsPlan()
	data = TSP.getData()

	# If data cannot be retreived, exit the program with an error:
	if data is None:
		sys.exit("Could not retrieve data from remote server.")

	# Define image path in same directory as this script:
	imgpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')

	# Plot all TSP funds:
	fp = FinancePlot.FinancePlot(TSP.dd, imgpath)
	fp.plotFunds(data, ['G', 'F', 'C', 'S', 'I'])

	# Plot each TSP fund and their SMAs and signals:
	for img, fund in {1: 'G', 2: 'F', 3: 'C', 4: 'S', 5: 'I'}.items():
		fp.plotSMASignals(TSP, data['date'], data[fund + ' Fund'], img, fund)
