import matplotlib, os

# Run matplotlib in headless mode if no X server exists:
try:
    os.environ['DISPLAY']
except KeyError:
    matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.dates import date2num, num2date, MonthLocator, WeekdayLocator, DateFormatter

import requests, pandas, time, sys
from datetime import datetime, timedelta
from io import StringIO
import numpy as np

dd = 365 # Number of days to plot
nl = 10  # Time period in days for short term moving average
nh = 30  # Time period in days for long term moving average

def daysSince(dt):
	return (num2date(date2num(datetime.now())) - dt).days

# Define a simple moving average that replaces invalid positions with NaN:
def SMA(list, n):
	# Start with empty list and fill invalid values first:
	ma = [np.nan]*n
	# Move through the valid positions in list and compute moving average:
	for i in range(n, len(list)):
		ma.append(np.mean(list[i-n:i]))
	# Return result"
	return ma

# Detect buy and sell crossovers of two SMA lists and return signals:
def detectCrossovers(dates, smanl, smanh):
	# Create empty data structure:
	crossovers = []

	# Detect change in sign at every point in the difference of two source lists:
	for i in np.where(np.diff(np.sign((smanl-smanh)[nh:])))[0].reshape(-1) + nh:
		# Compute slopes for both short term and long term SMA:
		smanlm = (smanl[i+1]-smanl[i])/(dates[i+1]-dates[i])
		smanhm = (smanh[i+1]-smanh[i])/(dates[i+1]-dates[i])

		# Compute exact time and value of the crossover:
		t = (smanh[i]-smanl[i])/(smanlm-smanhm)+dates[i]
		p = smanlm*(t-dates[i])+smanl[i]

		# Append the crossover value to the data structure:
		if t > date2num(todaydt-timedelta(days=dd+1)):
			# If short term SMA is below long term SMA, signal
			# to buy (True), otherwise signal to sell (False):
			crossovers.append((smanl[i] < smanh[i], (t, p)))

	# Return the completed data structure
	return crossovers

# POST values to remote webserver and download CSV reply:
def fetchTSPData(start, end):
	sys.stdout.write('Fetching TSP data from ' + start + ' to ' + end + ' ... ')
	url = "https://www.tsp.gov/InvestmentFunds/FundPerformance/index.html"
	data = {'whichButton': 'CSV', 'startdate': start, 'enddate': end}
	response = requests.post(url, data=data)
	print('Response ' + str(response.status_code))
	return response

# Create a clean dictionary with all CSV info from the TSP:
def parseTSPData(response):
	# Read in dataframe from CSV response and sort by date:
	df = pandas.read_csv(StringIO(response.text)).sort_values('date')

	# Clean up text in dataframe and create a dictionary:
	TSP = {}
	for k, v in df.to_dict('list').items():
		kn = k.strip()
		if len(kn) > 0:
			TSP[kn] = v

	# Convert all text dates into datetime objects:
	TSP['date'] = [datetime.strptime(date, '%Y-%m-%d') for date in TSP['date']]

	return TSP

def definePlotLegend(ax):
	# Display legend as well as major and minor gridlines:
	handles, labels = ax.get_legend_handles_labels()
	ax.legend(handles, labels, loc=8, ncol=len(labels), fontsize=12)
	ax.grid(which='both')

def setupPlot():
	# Define figure and axes handles:
	fig, ax = plt.subplots(figsize=(1920*10/1080.0, 10))

	# Set limits and tick intervals on the time axis:
	ax.xaxis.set_major_locator(months)
	ax.xaxis.set_major_formatter(datefmt)
	ax.xaxis.set_minor_locator(months)
	ax.set_xlim([date2num(todaydt-timedelta(days=dd+1)), date2num(TSP['date'][len(TSP['date'])-1])])

	# Create a directory to store images if it does not already exist:
	if not os.path.isdir(imgpath): os.mkdir(imgpath)

	# Set labels for axes:
	ax.set_xlabel('Close Date')
	ax.set_ylabel('Share Value ($)')

	return (fig, ax)

def genPlotTitle(fig, ax, fund):
	fig.canvas.set_window_title('TSP ' + fund)
	ax.set_title('Thrift Savings Plan ' + fund + ' from ' + (todaydt-timedelta(days=dd+1)).strftime("%m/%d/%Y") + ' to ' + TSP['date'][len(TSP['date'])-1].strftime("%m/%d/%Y"))

def printLatestCrossover(fund, crossovers):
	sys.stdout.write(fund + ' fund latest crossover: ')
	if crossovers:
		s, (t, p) = crossovers.pop()
		if s: sys.stdout.write('B ')
		else: sys.stdout.write('S ')
		sys.stdout.write(num2date(t).strftime('%m/%d/%Y ('))
		sys.stdout.write(str(daysSince(num2date(t))).rjust(len(str(dd))))
		sys.stdout.write(' days ago) @ $')
		print('{0:.2f}'.format(p))
	else:
		print('None within ' + str(dd) + ' days!')

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

def plotFunds(funds):
	# Define datasets for analysis:
	dates = date2num(TSP['date'])

	# Determine which datapoints are out of range:
	cut = 0
	for i, date in enumerate(dates):
		if date > date2num((todaydt-timedelta(days=dd+1))):
			cut = i - 1
			break

	# Initialize plot:
	fig, ax = setupPlot()

	# Set relevant titles for the window and figure:
	genPlotTitle(fig, ax, 'All Funds')

	# Trim all data points to be in range:
	dates = dates[cut:]

	# Plot prices for all funds in list:
	for fund in funds:
		ax.plot_date(dates, TSP[fund + ' Fund'][cut:], '-', label=fund + ' Fund')

	# Define plot legend and add gridlines:
	definePlotLegend(ax)

	# Save a copy of the plot in the imgpath directory:
	plt.savefig(os.path.join(imgpath, '00_AllTSPFunds.png'), bbox_inches='tight')

	# Display the plot:
	plt.show(block=True)

	# Close the plot:
	plt.close()

def plotSMASignals(t, p, img, fund):
	# Define datasets for analysis:
	dates = np.array(date2num(t))
	price = np.array(p)
	smanl = np.array(SMA(p, nl))
	smanh = np.array(SMA(p, nh))

	# Determine which datapoints are out of range:
	cut = 0
	for i, date in enumerate(dates):
		if date > date2num((todaydt-timedelta(days=dd+1))):
			cut = i - 1
			break

	# Initialize plot:
	fig, ax = setupPlot()

	# Set relevant titles for window, figure, and axes:
	genPlotTitle(fig, ax, fund + ' Fund')

	# Detect and print exact crossover signals:
	crossovers = detectCrossovers(dates, smanl, smanh)
	printLatestCrossover(fund, crossovers)

	# Trim all data points to be in range:
	dates = dates[cut:]
	price = price[cut:]
	smanl = smanl[cut:]
	smanh = smanh[cut:]

	# Plot price and short term and long term moving averages:
	ax.plot_date(dates, price, '-', label="Close Values")
	ax.plot_date(dates, smanl, '-', label=str(nl) + " Day SMA")
	ax.plot_date(dates, smanh, '-', label=str(nh) + " Day SMA")

	# Plot buy and sell crossover signals:
	if crossovers:
		ax.plot_date(*zip(*[s[1] for s in crossovers if     s[0]]), color='g', label="Buy Signals")
		ax.plot_date(*zip(*[s[1] for s in crossovers if not s[0]]), color='r', label="Sell Signals")

	# Define plot legend and add gridlines:
	definePlotLegend(ax)

	# Save a copy of the plot in the imgpath directory:
	plt.savefig(os.path.join(imgpath, '0' + str(img) + '_TSP' + fund + 'Fund.png'), bbox_inches='tight')

	# Display the plot:
	plt.show(block=True)

	# Close the plot:
	plt.close()
	
# Create datetime object for today
todaydt = datetime.now()

# Create datetime object for the day dd days in the past accounting for loss due to moving average:
startdt = datetime.now() - timedelta(days=dd+7.0/5.0*nh+dd/30.0*3.0) # Take weekends and holidays into account

# Convert datetime objects into format required by TSP fields:
today = todaydt.strftime("%m/%d/%Y")
start = startdt.strftime("%m/%d/%Y")

# Retrieve CSV data from TSP:
response = fetchTSPData(start, today)

# If data cannot be retreived, exit the program with an error:
if response.status_code != 200: sys.exit("Could not retrieve data from remote server.")

# Create dictionary from retrieved data:
TSP = parseTSPData(response)

# Define locators and formatters for time axis of plots:
quarters = MonthLocator(range(1, 13), bymonthday=1, interval=3)
months = MonthLocator(range(1, 13), bymonthday=1, interval=1)
datefmt = DateFormatter("%b %Y")

# Define image path in same directory as this script:
imgpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')

# Plot all TSP funds:
plotFunds(['G', 'F', 'C', 'S', 'I'])

# Plot each TSP fund and their SMAs and signals:
for img, fund in {1: 'G', 2: 'F', 3: 'C', 4: 'S', 5: 'I'}.items():
	plotSMASignals(TSP['date'], TSP[fund + ' Fund'], img, fund)
