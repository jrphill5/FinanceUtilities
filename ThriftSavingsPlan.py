import requests, pandas
from io import StringIO
from datetime import datetime, timedelta
import time
import matplotlib.pyplot as plt
from matplotlib.dates import date2num, num2date, MonthLocator, WeekdayLocator, DateFormatter
import numpy as np
import sys, os

dd = 365; # number of days to plot
nl = 10 # time period in days for short term moving average
nh = 30 # time period in days for long term moving average

imgpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
if not os.path.isdir(imgpath): os.mkdir(imgpath)

def SMA(list, n):
	ma = [np.nan]*n
	for i in range(n, len(list)):
		ma.append(np.mean(list[i-n:i]))
	return ma

todaydt = datetime.now()
startdt = datetime.now() - timedelta(days=dd+7.0/5.0*nh+1.0+3.0) # account for weekends and holidays

today = todaydt.strftime("%m/%d/%Y")
start = startdt.strftime("%m/%d/%Y")

quarters = MonthLocator(range(1, 13), bymonthday=1, interval=3)
months = MonthLocator(range(1, 13), bymonthday=1, interval=1)
datefmt = DateFormatter("%b %Y")

url = "https://www.tsp.gov/InvestmentFunds/FundPerformance/index.html"
data = {'whichButton': 'CSV', 'startdate': start, 'enddate': today}

response = requests.post(url, data=data)

if response.status_code != 200:
	print("Error " + response.status_code)
else:
	df = pandas.read_csv(StringIO(response.text)).sort_values('date')
	
	TSP = {}

	for k, v in df.to_dict('list').items():
		kn = k.strip()
		if len(kn) > 0:
			TSP[kn] = v

	TSP['date'] = [datetime.strptime(date, '%Y-%m-%d') for date in TSP['date']]

	dates = date2num(TSP['date'])

	fig, ax = plt.subplots()
	
	fig.canvas.set_window_title('All TSP Funds')
	
	ax.set_title('Thrift Savings Plan Funds from ' + (todaydt-timedelta(days=dd+1)).strftime("%m/%d/%Y") + ' to ' + TSP['date'][len(TSP['date'])-1].strftime("%m/%d/%Y"))
	ax.set_xlabel('Date')
	ax.set_ylabel('Share Value ($)')
	
	ax.plot_date(dates, TSP['G Fund'], '-', label="G Fund")
	ax.plot_date(dates, TSP['F Fund'], '-', label="F Fund")
	ax.plot_date(dates, TSP['C Fund'], '-', label="C Fund")
	ax.plot_date(dates, TSP['S Fund'], '-', label="S Fund")
	ax.plot_date(dates, TSP['I Fund'], '-', label="I Fund")

	#manager = plt.get_current_fig_manager()
	#manager.resize(*manager.window.maxsize())
	#manager.window.wm_geometry("+0+0")

	ax.xaxis.set_major_locator(quarters)
	ax.xaxis.set_major_formatter(datefmt)
	ax.xaxis.set_minor_locator(months)
	
	ax.set_xlim([date2num(todaydt-timedelta(days=dd+1)), date2num(TSP['date'][len(TSP['date'])-1])])

	ax.legend(loc=2)
	
	plt.grid(which='both')

	plt.savefig(os.path.join(imgpath, '00_AllTSPFunds.png'), bbox_inches='tight')

	plt.show(block=True)

	plt.close()

	for img, fund in {1: 'G', 2: 'F', 3: 'C', 4: 'S', 5: 'I'}.items():
		datesall = date2num(TSP['date'])
		datesnl = date2num(TSP['date'][nl - 1:])
		datesnh = date2num(TSP['date'][nh - 1:])

		t = np.array(date2num(TSP['date']))
		f = np.array(SMA(TSP[fund + ' Fund'], nl))
		g = np.array(SMA(TSP[fund + ' Fund'], nh))

		idx = np.argwhere(np.diff(np.sign(f-g))[nh:] != 0).reshape(-1) + nh
		
		fig, ax = plt.subplots()
		
		fig.canvas.set_window_title('TSP ' + fund + ' Fund')
		
		ax.set_title('Thrift Savings Plan ' + fund + ' Fund from ' + (todaydt-timedelta(days=dd+1)).strftime("%m/%d/%Y") + ' to ' + TSP['date'][len(TSP['date'])-1].strftime("%m/%d/%Y"))
		ax.set_xlabel('Date')
		ax.set_ylabel('Share Value ($)')

		ax.plot_date(datesall, TSP[fund + ' Fund'], '-', label=fund + " Fund")
		ax.plot_date(datesall, SMA(TSP[fund + ' Fund'], nl), '-', label=fund + " Fund (" + str(nl) + " day)")
		ax.plot_date(datesall, SMA(TSP[fund + ' Fund'], nh), '-', label=fund + " Fund (" + str(nh) + " day)")

		crossovers = [[[],[]],[[],[]]]
		print(fund + ' fund crossover points:')
		for i in idx:
			if f[i] < g[i]:
				j = 0 # buy
				sys.stdout.write("B: ")
			else:
				j = 1 # sell
				sys.stdout.write("S: ")
			
			fm = (f[i+1]-f[i])/(t[i+1]-t[i])
			gm = (g[i+1]-g[i])/(t[i+1]-t[i])
			
			te = (g[i]-f[i])/(fm-gm)+t[i]
			fe = fm*(te-t[i])+f[i]
			
			crossovers[j][0].append(te)
			crossovers[j][1].append(fe)
			
			print(num2date(te).strftime("%m/%d/%Y"))
		
		ax.plot(crossovers[0][0], crossovers[0][1], 'go')
		ax.plot(crossovers[1][0], crossovers[1][1], 'ro')
		
		#manager = plt.get_current_fig_manager()
		#manager.resize(*manager.window.maxsize())
		#manager.window.wm_geometry("+0+0")

		ax.xaxis.set_major_locator(quarters)
		ax.xaxis.set_major_formatter(datefmt)
		ax.xaxis.set_minor_locator(months)
	
		ax.set_xlim([date2num(todaydt-timedelta(days=dd+1)), date2num(TSP['date'][len(TSP['date'])-1])])
		
		ax.legend(loc=2)
		
		plt.grid(which='both')
		
		plt.savefig(os.path.join(imgpath, '0' + str(img) + '_TSP' + fund + 'Fund.png'), bbox_inches='tight')
		
		plt.show(block=True)
		
		plt.close()