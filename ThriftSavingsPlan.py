import matplotlib, os

# Run matplotlib in headless mode if no X server exists:
try:
	os.environ['DISPLAY']
except KeyError:
	matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from matplotlib.dates import date2num, num2date, MonthLocator, DateFormatter

import requests, pandas, time, sys
from datetime import datetime, timedelta
from io import StringIO
import numpy as np

class ThriftSavingsPlan:
	def __init__(self, dts = datetime.now() - timedelta(days=365), dte = datetime.now()):
		self.dts = dts
		self.dte = dte

		# Create datetime object for the actual start time accounting for loss due to moving average:
		dd = (self.dte-self.dts).days
		self.dtp = self.dte - timedelta(days=dd+7.0/5.0*nh+dd/30.0*3.0) # Take weekends and holidays into account

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
		s = self.formatDate(self.dtp)
		e = self.formatDate(self.dte)
		url = 'https://www.tsp.gov/InvestmentFunds/FundPerformance/index.html'
		data = {'whichButton': 'CSV', 'startdate': s, 'enddate': e}
		self.response = requests.post(url, data=data)

	# Create a clean dictionary with all CSV info from the TSP:
	def parseData(self):
		if self.response.status_code == 200:
			# Read in dataframe from CSV response and sort by date:
			df = pandas.read_csv(StringIO(self.response.text)).sort_values('date')

			# Clean up text in dataframe and create a dictionary:
			data = {}
			for k, v in df.to_dict('list').items():
				kn = k.strip()
				if len(kn) > 0:
					data[kn] = v

			# Convert all text dates into datetime objects:
			data['date'] = [datetime.strptime(date, '%Y-%m-%d') for date in data['date']]

			self.data = data
		else:
			self.data = None

	def formatDate(self, dt):
		return dt.strftime("%m/%d/%Y")

	# Detect buy and sell crossovers of two SMA lists and return signals:
	def detectCrossovers(self, dates, smanl, smanh):
		# Create empty data structure:
		crossovers = []

		# Detect change in sign at every point in the difference of two source lists:
		for i in np.where(np.diff(np.sign((smanl-smanh))))[0].reshape(-1):
			# Compute slopes for both short term and long term SMA:
			smanlm = (smanl[i+1]-smanl[i])/(dates[i+1]-dates[i])
			smanhm = (smanh[i+1]-smanh[i])/(dates[i+1]-dates[i])

			# Compute exact time and value of the crossover:
			t = (smanh[i]-smanl[i])/(smanlm-smanhm)+dates[i]
			p = smanlm*(t-dates[i])+smanl[i]

			# Append the crossover value to the data structure:
			if t > date2num(num2date(dates[len(dates)-1])-timedelta(days=dd+1)):
				# If short term SMA is below long term SMA, signal
				# to buy (True), otherwise signal to sell (False):
				crossovers.append((smanl[i] < smanh[i], (t, p)))

		# Return the completed data structure
		return crossovers

	# Calculate PIP following signals:
	def calcPIPFS(self, t, p, crossovers, verbose=False):
		bl = None
		sl = None
		if verbose: print()

		# Buy share on first day of period no matter what:
		if verbose: print('share bought on ' + num2date(t[0]).strftime('%m/%d/%y') + ' for $' + '{0:.2f}'.format(p[0]))
		bl = (t[0], p[0])

		gain = -p[0]
		for i, (s, (ts, ps)) in enumerate(crossovers):
			# If first signal is buy, ignore, otherwise sell:
			if i == 0:
				if s:
					if verbose: sys.stdout.write('buy signal ignored')
				else:
					if verbose: sys.stdout.write('share sold')
					sl = (ts, ps)
					gain += ps
			# Otherwise, handle intermediate signals
			else:
				if verbose: sys.stdout.write('share ')
				if s:
					if verbose: sys.stdout.write('bought')
					bl = (ts, ps)
					gain -= ps
				else:
					if verbose: sys.stdout.write('sold')
					sl = (ts, ps)
					gain += ps
			if verbose: print(' on ' + num2date(ts).strftime('%m/%d/%y') + ' for $' + '{0:.2f}'.format(ps))

		# If signals are over and share hasn't been sold yet, sell share on end date:
		if sl is None or bl[0] > sl[0]:
			if verbose: print('share sold on ' + num2date(t[len(t)-1]).strftime('%m/%d/%y') + ' for $' + '{0:.2f}'.format(p[len(p)-1]))
			gain += p[len(p)-1]

		if verbose: print('{0:+.2f}'.format(gain))

		return (gain, 100*gain/p[0])

	# Calculate PIP when fully invested:
	def calcPIPFI(self, t, p):
		return ((p[len(p)-1] - p[0]), 100*(p[len(p)-1] - p[0])/p[0])

	# Define a simple moving average that replaces invalid positions with NaN:
	def SMA(self, l, n):
		# Start with empty list and fill invalid values first:
		ma = [np.nan]*n
		# Move through the valid positions in list and compute moving average:
		for i in range(n, len(l)):
			ma.append(np.mean(l[i-n:i]))
		# Return result
		return ma

class FinancePlot:
	def __init__(self):
		self.fig = None
		self.ax = None
		self.imgpath = None
		self.t = None

	def getFig(self):
		return self.fig

	def getAx(self):
		return self.ax

	def setupPlot(self, t, imgpath):
		self.t = t
		self.imgpath = imgpath

		# Define figure and axes handles:
		self.fig, self.ax = plt.subplots(figsize=(1920*10/1080.0, 10))

		# Set limits and tick intervals on the time axis:
		self.ax.xaxis.set_major_locator(MonthLocator(range(1, 13), bymonthday=1, interval=1))
		self.ax.xaxis.set_major_formatter(DateFormatter("%b %Y"))
		#self.ax.xaxis.set_minor_locator(MonthLocator(range(1, 13), bymonthday=1, interval=1))
		self.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
		self.ax.set_xlim([date2num(self.t[len(self.t)-1]-timedelta(days=dd+1)), date2num(self.t[len(self.t)-1])])

		# Create a directory to store images if it does not already exist:
		if not os.path.exists(self.imgpath): os.mkdir(self.imgpath)

		# Set labels for axes:
		self.ax.set_xlabel('Close Date')
		self.ax.set_ylabel('Share Value ($)')

	def definePlotLegend(self):
		# Display legend as well as major and minor gridlines:
		handles, labels = self.ax.get_legend_handles_labels()
		self.ax.legend(handles, labels, loc=8, ncol=len(labels), fontsize=12)
		self.ax.grid(which='both')

	def genPlotTitle(self, fund):
		self.fig.canvas.set_window_title('TSP ' + fund)
		self.ax.set_title('Thrift Savings Plan ' + fund + ' from ' + (self.t[len(self.t)-1]-timedelta(days=dd+1)).strftime("%m/%d/%Y") + ' to ' + self.t[len(self.t)-1].strftime("%m/%d/%Y"))

	def plotFunds(self, TSP, funds):
		t = TSP['date']

		# Define datasets for analysis:
		dates = date2num(t)

		# Determine which datapoints are out of range:
		cut = 0
		for i, date in enumerate(dates):
			if date > date2num((t[len(t)-1]-timedelta(days=dd+1))):
				cut = i - 1
				break

		# Trim all data points to be in range:
		dates = dates[cut:]

		# Initialize plot:
		fp = FinancePlot()
		fp.setupPlot(t, imgpath)

		# Set relevant titles for the window and figure:
		fp.genPlotTitle('All Funds')

		fig = fp.getFig()
		ax = fp.getAx()

		# Plot prices for all funds in list:
		for fund in funds:
			ax.plot_date(dates, TSP[fund + ' Fund'][cut:], '-', label=fund + ' Fund')

		# Define plot legend and add gridlines:
		fp.definePlotLegend()

		# Save a copy of the plot in the imgpath directory:
		plt.savefig(os.path.join(imgpath, '00_AllTSPFunds.png'), bbox_inches='tight')

		# Display the plot:
		plt.show(block=True)

		# Close the plot:
		plt.close()

	def plotSMASignals(self, tsp, t, p, img, imgpath, fund, nl, nh, dd):
		# Define datasets for analysis:
		dates = np.array(date2num(t))
		price = np.array(p)
		smanl = np.array(tsp.SMA(p, nl))
		smanh = np.array(tsp.SMA(p, nh))

		# Determine which datapoints are out of range:
		cut = 0
		for i, date in enumerate(dates):
			if date > date2num((t[len(t)-1]-timedelta(days=dd+1))):
				cut = i - 1
				break

		# Trim all data points to be in range:
		dates = dates[cut:]
		price = price[cut:]
		smanl = smanl[cut:]
		smanh = smanh[cut:]

		# Initialize plot:
		fp = FinancePlot()
		fp.setupPlot(t, imgpath)

		# Set relevant titles for window, figure, and axes:
		fp.genPlotTitle(fund + ' Fund')

		fig = fp.getFig()
		ax = fp.getAx()

		# Detect and print exact crossover signals:
		crossovers = tsp.detectCrossovers(dates, smanl, smanh)
		if printLatestCrossover(fund, crossovers):
			print(' !!!')
		else: print('');

		# Print comparison between staying fully invested and following signals:
		print(fund + ' fund performance:')
		for desc, data in [('Invested', tsp.calcPIPFI(dates, price)), ('Signaled', tsp.calcPIPFS(dates, price, crossovers)), ('Variance', np.subtract(tsp.calcPIPFS(dates, price, crossovers), tsp.calcPIPFI(dates, price)))]:
			sys.stdout.write('  ' + desc + ' ')
			sys.stdout.write('{0:+7.2f}'.format(data[0]).replace('-', '-$').replace('+', '+$'))
			print('{0:+7.1f}%'.format(data[1]))
	
		# Plot price and short term and long term moving averages:
		ax.plot_date(dates, price, '-', label="Close Values")
		ax.plot_date(dates, smanl, '-', label=str(nl) + " Day SMA")
		ax.plot_date(dates, smanh, '-', label=str(nh) + " Day SMA")

		# Plot buy and sell crossover signals:
		if crossovers:
			ax.plot_date(*zip(*[s[1] for s in crossovers if     s[0]]), color='g', label="Buy Signals")
			ax.plot_date(*zip(*[s[1] for s in crossovers if not s[0]]), color='r', label="Sell Signals")

		# Define plot legend and add gridlines:
		fp.definePlotLegend()

		# Save a copy of the plot in the imgpath directory:
		plt.savefig(os.path.join(imgpath, '0' + str(img) + '_TSP' + fund + 'Fund.png'), bbox_inches='tight')

		# Display the plot:
		plt.show(block=True)

		# Close the plot:
		plt.close()
	
	def plotFunds(self, TSP, funds):
		t = TSP['date']

		# Define datasets for analysis:
		dates = date2num(t)

		# Determine which datapoints are out of range:
		cut = 0
		for i, date in enumerate(dates):
			if date > date2num((t[len(t)-1]-timedelta(days=dd+1))):
				cut = i - 1
				break

		# Trim all data points to be in range:
		dates = dates[cut:]

		# Initialize plot:
		fp = FinancePlot()
		fp.setupPlot(t, imgpath)

		# Set relevant titles for the window and figure:
		fp.genPlotTitle('All Funds')

		fig = fp.getFig()
		ax = fp.getAx()

		# Plot prices for all funds in list:
		for fund in funds:
			ax.plot_date(dates, TSP[fund + ' Fund'][cut:], '-', label=fund + ' Fund')

		# Define plot legend and add gridlines:
		fp.definePlotLegend()

		# Save a copy of the plot in the imgpath directory:
		plt.savefig(os.path.join(imgpath, '00_AllTSPFunds.png'), bbox_inches='tight')

		# Display the plot:
		plt.show(block=True)

		# Close the plot:
		plt.close()

	def plotSMASignals(self, tsp, t, p, img, imgpath, fund, nl, nh, dd):
		# Define datasets for analysis:
		dates = np.array(date2num(t))
		price = np.array(p)
		smanl = np.array(tsp.SMA(p, nl))
		smanh = np.array(tsp.SMA(p, nh))

		# Determine which datapoints are out of range:
		cut = 0
		for i, date in enumerate(dates):
			if date > date2num((t[len(t)-1]-timedelta(days=dd+1))):
				cut = i - 1
				break

		# Trim all data points to be in range:
		dates = dates[cut:]
		price = price[cut:]
		smanl = smanl[cut:]
		smanh = smanh[cut:]

		# Initialize plot:
		fp = FinancePlot()
		fp.setupPlot(t, imgpath)

		# Set relevant titles for window, figure, and axes:
		fp.genPlotTitle(fund + ' Fund')

		fig = fp.getFig()
		ax = fp.getAx()

		# Detect and print exact crossover signals:
		crossovers = tsp.detectCrossovers(dates, smanl, smanh)
		if printLatestCrossover(fund, crossovers):
			print(' !!!')
		else: print('');

		# Print comparison between staying fully invested and following signals:
		print(fund + ' fund performance:')
		for desc, data in [('Invested', tsp.calcPIPFI(dates, price)), ('Signaled', tsp.calcPIPFS(dates, price, crossovers)), ('Variance', np.subtract(tsp.calcPIPFS(dates, price, crossovers), tsp.calcPIPFI(dates, price)))]:
			sys.stdout.write('  ' + desc + ' ')
			sys.stdout.write('{0:+7.2f}'.format(data[0]).replace('-', '-$').replace('+', '+$'))
			print('{0:+7.1f}%'.format(data[1]))
	
		# Plot price and short term and long term moving averages:
		ax.plot_date(dates, price, '-', label="Close Values")
		ax.plot_date(dates, smanl, '-', label=str(nl) + " Day SMA")
		ax.plot_date(dates, smanh, '-', label=str(nh) + " Day SMA")

		# Plot buy and sell crossover signals:
		if crossovers:
			ax.plot_date(*zip(*[s[1] for s in crossovers if     s[0]]), color='g', label="Buy Signals")
			ax.plot_date(*zip(*[s[1] for s in crossovers if not s[0]]), color='r', label="Sell Signals")

		# Define plot legend and add gridlines:
		fp.definePlotLegend()

		# Save a copy of the plot in the imgpath directory:
		plt.savefig(os.path.join(imgpath, '0' + str(img) + '_TSP' + fund + 'Fund.png'), bbox_inches='tight')

		# Display the plot:
		plt.show(block=True)

		# Close the plot:
		plt.close()
	
def daysSince(dt):
	return (num2date(date2num(datetime.now())) - dt).days

def printLatestCrossover(fund, crossovers):
	print()
	print(fund + ' fund latest crossover:')
	if crossovers:
		s, (t, p) = crossovers[-1]
		if s: sys.stdout.write('  B ')
		else: sys.stdout.write('  S ')
		sys.stdout.write(num2date(t).strftime('%m/%d/%Y ('))
		sys.stdout.write(str(daysSince(num2date(t))).rjust(len(str(dd))))
		sys.stdout.write(' days ago) @ $')
		sys.stdout.write('{0:.2f}'.format(p))
		return daysSince(num2date(t)) == 0
	else:
		sys.stdout.write('  None within ' + str(dd) + ' days!')
		return False

def printAllCrossovers(fund, crossovers):
	print(fund + ' fund crossover points:')
	if crossovers:
		for s, (t, p) in crossovers:
			if s: sys.stdout.write('  B ')
			else: sys.stdout.write('  S ')
			sys.stdout.write(num2date(t).strftime('%m/%d/%Y ('))
			sys.stdout.write(str(daysSince(num2date(t))).rjust(len(str(dd))))
			sys.stdout.write(' days ago) @ $')
			print('{0:.2f}'.format(p))
	else:
		print('  None within ' + str(dd) + ' days!')

if __name__ == "__main__":

	dd = 365
	nl = 10
	nh = 30

	TSP = ThriftSavingsPlan()
	data = TSP.getData()

	fp = FinancePlot()

	# If data cannot be retreived, exit the program with an error:
	if data is None:
		sys.exit("Could not retrieve data from remote server.")

	# Define image path in same directory as this script:
	imgpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')

	# Plot all TSP funds:
	fp.plotFunds(data, ['G', 'F', 'C', 'S', 'I'])

	# Plot each TSP fund and their SMAs and signals:
	for img, fund in {1: 'G', 2: 'F', 3: 'C', 4: 'S', 5: 'I'}.items():
		fp.plotSMASignals(TSP, data['date'], data[fund + ' Fund'], img, imgpath, fund, nl, nh, dd)
