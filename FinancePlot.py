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

# Set default font size for plots
plt.rcParams.update({'font.size': 12})

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
		self.ax.set_xlim([date2num(min(self.t)), date2num(max(self.t))])

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

	def genPlotTitle(self, fund, updated=None):
		title  = "%s %s from %s to %s" % (self.source, fund, self.bf.formatDate(min(self.t)), self.bf.formatDate(max(self.t)))
		if updated is not None:
			title += " [Updated " + self.bf.formatDate(updated)
			if self.bf.formatTime(updated) != self.bf.formatTime(datetime(1970, 1, 1)):
				title += " " + self.bf.formatTime(updated)
			title += "]"
		self.fig.canvas.set_window_title("%s %s" % (self.source, fund))
		self.ax.set_title(title)

	def plotSignals(self, finObj, t, p, img, fund, avgtype, updateTime=None):
		avgtypes = ['SMA', 'EWMA']
		if avgtype not in avgtypes: avgtype = 'SMA'

		# Define datasets for analysis:
		dates = np.array(date2num(t))
		price = np.array(p)
		if avgtype == 'SMA':
			nl = np.array(self.bf.SMA(p, finObj.nl))
			nh = np.array(self.bf.SMA(p, finObj.nh))
		elif avgtype == 'EWMA':
			nl = np.array(self.bf.EWMA(p, finObj.nl))
			nh = np.array(self.bf.EWMA(p, finObj.nh))

		# Determine which datapoints are out of range:
		cut = 0
		for i, date in enumerate(dates):
			if date > date2num(max(t)-timedelta(days=self.dd-1)):
				cut = i - 1
				if cut < 0: cut = 0
				break

		# Trim all data points to be in range:
		t = t[cut:]
		dates = dates[cut:]
		price = price[cut:]
		nl = nl[cut:]
		nh = nh[cut:]

		# Initialize plot:
		fp = FinancePlot(self.source, self.dd, self.imgpath)
		fp.setupPlot(t)

		# Set relevant titles for window, figure, and axes:
		fp.genPlotTitle(fund, updateTime)
		fig = fp.getFig()
		ax = fp.getAx()

		# Avoid duplication of word fund in name:
		if "fund" in fund.lower(): fundname = fund.capitalize()
		else:                      fundname = fund + " fund"

		# Print current price of fund:
		print()
		print('{0:36s}'.format(fundname + ' price as of %s:' % self.bf.formatDate(num2date(dates[-1]))) + '${0:.2f}'.format(price[-1]))

		# Detect and print exact crossover signals:
		crossovers = self.bf.detectCrossovers(dates, nl, nh, self.dd)
		if finObj.printLatestCrossover(fund, crossovers):
			print(' !!!')
		else: print('');

		# Print information about recent performance:
		print(fundname + ' recent performance:')
		for days in [1, 5, 20, 60]:
			sys.stdout.write('  {0:02d} day:'.format(days))
			try: sys.stdout.write('  {0:+9.2f}'.format(price[-1 - days]).replace('+', '$'))
			except IndexError: sys.stdout.write('  {0:>9s}'.format('+$X.XX'))
			try: sys.stdout.write('  {0:+7.2f}'.format(price[-1] - price[-1 - days]).replace('-', '-$').replace('+', '+$'))
			except IndexError: sys.stdout.write('  {0:>8s}'.format('+$X.XX'))
			try: sys.stdout.write('  {0:+7.2f}%'.format(100*(price[-1] - price[-1 - days])/price[-1 - days]))
			except IndexError: sys.stdout.write('  {0:>7s}%'.format('+X.XX'))
			print()

		# Print comparison between staying fully invested and following signals:
		print(fundname + ' full performance:')
		invested = self.bf.calcPIPFI(dates, price)
		signaled, crossadjust = self.bf.calcPIPFS(dates, price, crossovers, openend=finObj.openEnd)
		for desc, data in [('Invested', invested), ('Signaled', signaled), ('Variance', np.subtract(signaled, invested))]:
			sys.stdout.write('  ' + desc + ':           ')
			sys.stdout.write('{0:+7.2f}'.format(data[0]).replace('-', '-$').replace('+', '+$'))
			print('  {0:+7.2f}%'.format(data[1]))
	
		# Plot price and short term and long term moving averages:
		try: ax.plot_date(dates, price, '-', label="Close Values")
		except (ValueError, TypeError): print("[WARN] Exception during close value plotting")
		try: ax.plot_date(dates, nl,	'-', label="%d Day %s" % (finObj.nl, avgtype))
		except (ValueError, TypeError): print("[WARN] Exception during short term average plotting")
		try: ax.plot_date(dates, nh,	'-', label="%d Day %s" % (finObj.nh, avgtype))
		except (ValueError, TypeError): print("[WARN] Exception during long term average plotting")

		# Plot buy and sell crossover signals:
		if crossovers:
			try: ax.plot_date(*zip(*[s[1] for s in crossovers  if     s[0]]), mew=1, color='g', mec='k', marker='o', markersize=7.0, label="Buy Signaled")
			except (ValueError, TypeError): print("[WARN] Exception during buy signal plotting")
			try: ax.plot_date(*zip(*[s[1] for s in crossadjust if     s[0]]), mew=1, color='g', mec='k', marker='X', markersize=8.5, label="Buy Settled")
			except (ValueError, TypeError): print("[WARN] Exception during buy settle plotting")
			try: ax.plot_date(*zip(*[s[1] for s in crossovers  if not s[0]]), mew=1, color='r', mec='k', marker='o', markersize=7.0, label="Sell Signaled")
			except (ValueError, TypeError): print("[WARN] Exception during sell signal plotting")
			try: ax.plot_date(*zip(*[s[1] for s in crossadjust if not s[0]]), mew=1, color='r', mec='k', marker='X', markersize=8.5, label="Sell Settled")
			except (ValueError, TypeError): print("[WARN] Exception during sell settle plotting")

		# Define plot legend and add gridlines:
		fp.definePlotLegend()

		# Save a copy of the plot in the imgpath directory:
		plt.savefig(os.path.join(self.imgpath, (fund + '.png').replace(' ', '')), bbox_inches='tight')

		# Display the plot:
		plt.show(block=True)

		# Close the plot:
		plt.close()
