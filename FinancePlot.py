import matplotlib, os

# Run matplotlib in headless mode if no X server exists:
try:
	os.environ['DISPLAY']
except KeyError:
	matplotlib.use('Agg')

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import date2num, num2date, MonthLocator, DateFormatter
from matplotlib.ticker import FormatStrFormatter
from datetime import datetime, timedelta

import BasicFinance

class FinancePlot:
	def __init__(self, source, dd, imgpath):
		self.source = source
		self.bf = BasicFinance.BasicFinance()
		self.dd = dd
		self.fig = None
		self.ax = None
		self.imgpath = imgpath
		self.t = None

	def getFig(self):
		return self.fig

	def getAx(self):
		return self.ax

	def setupPlot(self, t):
		self.t = t

		# Define figure and axes handles:
		self.fig, self.ax = plt.subplots(figsize=(1920*10/1080.0, 10))

		# Set limits and tick intervals on the time axis:
		self.ax.xaxis.set_major_locator(MonthLocator(range(1, 13), bymonthday=1, interval=1))
		self.ax.xaxis.set_major_formatter(DateFormatter("%b %Y"))
		#self.ax.xaxis.set_minor_locator(MonthLocator(range(1, 13), bymonthday=1, interval=1))
		self.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
		self.ax.set_xlim([date2num(self.t[len(self.t)-1]-timedelta(days=self.dd+1)), date2num(self.t[len(self.t)-1])])

		# Create a directory to store images if it does not already exist:
		if not os.path.exists(self.imgpath): os.makedirs(self.imgpath)

		# Set labels for axes:
		self.ax.set_xlabel('Close Date')
		self.ax.set_ylabel('Share Value ($)')

	def definePlotLegend(self):
		# Display legend as well as major and minor gridlines:
		handles, labels = self.ax.get_legend_handles_labels()
		self.ax.legend(handles, labels, loc=8, ncol=len(labels), fontsize=12)
		self.ax.grid(which='both')

	def genPlotTitle(self, fund):
		self.fig.canvas.set_window_title(self.source + ' ' + fund)
		self.ax.set_title(self.source + ' ' + fund + ' from ' + self.bf.formatDate(self.t[len(self.t)-1]-timedelta(days=self.dd+1)) + ' to ' + self.bf.formatDate(self.t[len(self.t)-1]))

	def plotFunds(self, finData, funds):
		t = finData['Date']

		# Define datasets for analysis:
		dates = date2num(t)

		# Determine which datapoints are out of range:
		cut = 0
		for i, date in enumerate(dates):
			if date > date2num((t[len(t)-1]-timedelta(days=self.dd+1))):
				cut = i - 1
				if cut < 0: cut = 0
				break

		# Trim all data points to be in range:
		dates = dates[cut:]

		# Initialize plot:
		fp = FinancePlot(self.source, self.dd, self.imgpath)
		fp.setupPlot(t)

		# Set relevant titles for the window and figure:
		fp.genPlotTitle('Funds')

		fig = fp.getFig()
		ax = fp.getAx()

		# Plot prices for all funds in list:
		for fund in funds:
			ax.plot_date(dates, finData[fund][cut:], '-', label=fund)

		# Define plot legend and add gridlines:
		fp.definePlotLegend()

		# Save a copy of the plot in the imgpath directory:
		plt.savefig(os.path.join(self.imgpath, '00_AllFunds.png'), bbox_inches='tight')

		# Display the plot:
		plt.show(block=True)

		# Close the plot:
		plt.close()

	def plotSMASignals(self, finObj, t, p, img, fund):
		# Define datasets for analysis:
		dates = np.array(date2num(t))
		price = np.array(p)
		smanl = np.array(self.bf.SMA(p, finObj.nl))
		smanh = np.array(self.bf.SMA(p, finObj.nh))

		# Determine which datapoints are out of range:
		cut = 0
		for i, date in enumerate(dates):
			if date > date2num((t[len(t)-1]-timedelta(days=self.dd+1))):
				cut = i - 1
				if cut < 0: cut = 0
				break

		# Trim all data points to be in range:
		dates = dates[cut:]
		price = price[cut:]
		smanl = smanl[cut:]
		smanh = smanh[cut:]

		# Initialize plot:
		fp = FinancePlot(self.source, self.dd, self.imgpath)
		fp.setupPlot(t)

		# Set relevant titles for window, figure, and axes:
		fp.genPlotTitle(fund + ' Fund')

		fig = fp.getFig()
		ax = fp.getAx()

		# Detect and print exact crossover signals:
		crossovers = self.bf.detectCrossovers(dates, smanl, smanh, self.dd)
		if finObj.printLatestCrossover(fund, crossovers):
			print(' !!!')
		else: print('');

		# Print comparison between staying fully invested and following signals:
		print(fund + ' fund performance:')
		for desc, data in [('Invested', self.bf.calcPIPFI(dates, price)), ('Signaled', self.bf.calcPIPFS(dates, price, crossovers)), ('Variance', np.subtract(self.bf.calcPIPFS(dates, price, crossovers), self.bf.calcPIPFI(dates, price)))]:
			sys.stdout.write('  ' + desc + ' ')
			sys.stdout.write('{0:+7.2f}'.format(data[0]).replace('-', '-$').replace('+', '+$'))
			print('{0:+7.1f}%'.format(data[1]))
	
		# Plot price and short term and long term moving averages:
		ax.plot_date(dates, price, '-', label="Close Values")
		ax.plot_date(dates, smanl, '-', label=str(finObj.nl) + " Day SMA")
		ax.plot_date(dates, smanh, '-', label=str(finObj.nh) + " Day SMA")

		# Plot buy and sell crossover signals:
		if crossovers:
			ax.plot_date(*zip(*[s[1] for s in crossovers if     s[0]]), color='g', label="Buy Signals")
			ax.plot_date(*zip(*[s[1] for s in crossovers if not s[0]]), color='r', label="Sell Signals")

		# Define plot legend and add gridlines:
		fp.definePlotLegend()

		# Save a copy of the plot in the imgpath directory:
		plt.savefig(os.path.join(self.imgpath, '0' + str(img) + '_' + fund + 'Fund.png'), bbox_inches='tight')

		# Display the plot:
		plt.show(block=True)

		# Close the plot:
		plt.close()
