import requests, pandas, time, sys, os
from datetime import datetime, timedelta
from io import StringIO
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import date2num, num2date, MonthLocator, WeekdayLocator, DateFormatter

dd = 365 # Number of days to plot
nl = 10  # Time period in days for short term moving average
nh = 30  # Time period in days for long term moving average

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
	crossovers = [[[],[]],[[],[]]]

	# Detect change in sign at every point in the difference of two source lists:
	for i in np.argwhere(np.diff(np.sign((smanl-smanh)[nh:])) != 0).reshape(-1) + nh:
		# If short term SMA is below long term SMA, signal to buy:
		if smanl[i] < smanh[i]:
			j = 0
			sys.stdout.write("B: ")
		# If short term SMA is below long term SMA, signal to sell:
		else:
			j = 1
			sys.stdout.write("S: ")

		# Compute slopes for both short term and long term SMA:
		smanlm = (smanl[i+1]-smanl[i])/(dates[i+1]-dates[i])
		smanhm = (smanh[i+1]-smanh[i])/(dates[i+1]-dates[i])

		# Compute exact time and value of the crossover:
		t = (smanh[i]-smanl[i])/(smanlm-smanhm)+dates[i]
		p = smanlm*(t-dates[i])+smanl[i]

		# Append the crossover value to the data structure:
		crossovers[j][0].append(t)
		crossovers[j][1].append(p)

		# Print the crossover date:
		print(num2date(t).strftime("%m/%d/%Y"))

	# Return the completed data structure
	return crossovers

# Create datetime object for today
todaydt = datetime.now()

# Create datetime object for the day dd days in the past accounting for loss due to moving average:
startdt = datetime.now() - timedelta(days=dd+7.0/5.0*nh+1.0+3.0) # Take weekends and holidays into account

# Convert datetime objects into format required by TSP fields:
today = todaydt.strftime("%m/%d/%Y")
start = startdt.strftime("%m/%d/%Y")

# POST values to remote webserver and download CSV reply:
sys.stdout.write('Fetching TSP data from ' + start + ' to ' + today + ' ... ')
url = "https://www.tsp.gov/InvestmentFunds/FundPerformance/index.html"
data = {'whichButton': 'CSV', 'startdate': start, 'enddate': today}
response = requests.post(url, data=data)
print('Response ' + str(response.status_code))

# If data cannot be retreived, exit the program with an error:
if response.status_code != 200: sys.exit("Could not retrieve data from remote server.")

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

# Define locators and formatters for time axis of plots:
quarters = MonthLocator(range(1, 13), bymonthday=1, interval=3)
months = MonthLocator(range(1, 13), bymonthday=1, interval=1)
datefmt = DateFormatter("%b %Y")

# Define datasets for analysis:
dates = date2num(TSP['date'])

# Define figure and axes handles:
fig, ax = plt.subplots(figsize=(1920*10/1080.0, 10))

# Set relevant titles for window, figure, and axes:
fig.canvas.set_window_title('All TSP Funds')
ax.set_title('Thrift Savings Plan Funds from ' + (todaydt-timedelta(days=dd+1)).strftime("%m/%d/%Y") + ' to ' + TSP['date'][len(TSP['date'])-1].strftime("%m/%d/%Y"))
ax.set_xlabel('Close Date')
ax.set_ylabel('Share Value ($)')

# Set limits and tick intervals on the time axis:
ax.xaxis.set_major_locator(months)
ax.xaxis.set_major_formatter(datefmt)
ax.xaxis.set_minor_locator(months)
ax.set_xlim([date2num(todaydt-timedelta(days=dd+1)), date2num(TSP['date'][len(TSP['date'])-1])])

# Plot prices for all funds in list:
for fund in ['G', 'F', 'C', 'S', 'I']:
	ax.plot_date(dates, TSP[fund + ' Fund'], '-', label=fund + ' Fund')

# Display legend as well as major and minor gridlines:
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels, loc=8, ncol=len(labels), fontsize=12)
ax.grid(which='both')

# Create a directory to store images if it does not already exist:
imgpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
if not os.path.isdir(imgpath): os.mkdir(imgpath)
	
# Save a copy of the plot in the imgpath directory:
plt.savefig(os.path.join(imgpath, '00_AllTSPFunds.png'), bbox_inches='tight')
	
# Display the plot:
plt.show(block=True)
	
# Close the plot:
plt.close()

for img, fund in {1: 'G', 2: 'F', 3: 'C', 4: 'S', 5: 'I'}.items():
	# Define datasets for analysis:
	dates = np.array(date2num(TSP['date']))
	price = np.array(TSP[fund + ' Fund'])
	smanl = np.array(SMA(TSP[fund + ' Fund'], nl))
	smanh = np.array(SMA(TSP[fund + ' Fund'], nh))

	# Define figure and axes handles:
	fig, ax = plt.subplots(figsize=(1920*10/1080.0, 10))

	# Set relevant titles for window, figure, and axes:
	fig.canvas.set_window_title('TSP ' + fund + ' Fund')
	ax.set_title('Thrift Savings Plan ' + fund + ' Fund from ' + (todaydt-timedelta(days=dd+1)).strftime("%m/%d/%Y") + ' to ' + TSP['date'][len(TSP['date'])-1].strftime("%m/%d/%Y"))
	ax.set_xlabel('Close Date')
	ax.set_ylabel('Share Value ($)')

	# Set limits and tick intervals on the time axis:
	ax.xaxis.set_major_locator(months)
	ax.xaxis.set_major_formatter(datefmt)
	ax.xaxis.set_minor_locator(months)
	ax.set_xlim([date2num(todaydt-timedelta(days=dd+1)), date2num(TSP['date'][len(TSP['date'])-1])])

	# Plot price and short term and long term moving averages:
	ax.plot_date(dates, price, '-', label="Close Values")
	ax.plot_date(dates, smanl, '-', label=str(nl) + " Day SMA")
	ax.plot_date(dates, smanh, '-', label=str(nh) + " Day SMA")

	# Detect and print exact crossover signals:
	print(fund + ' fund crossover points:')
	crossovers = detectCrossovers(dates, smanl, smanh)

	# Plot buy and sell crossover signals:
	ax.plot(crossovers[0][0], crossovers[0][1], 'go', label="Buy Signals")
	ax.plot(crossovers[1][0], crossovers[1][1], 'ro', label="Sell Signals")

	# Display legend as well as major and minor gridlines:
	handles, labels = ax.get_legend_handles_labels()
	ax.legend(handles, labels, loc=8, ncol=len(labels), fontsize=12)
	ax.grid(which='both')

	# Save a copy of the plot in the imgpath directory:
	plt.savefig(os.path.join(imgpath, '0' + str(img) + '_TSP' + fund + 'Fund.png'), bbox_inches='tight')

	# Display the plot:
	plt.show(block=True)

	# Close the plot:
	plt.close()