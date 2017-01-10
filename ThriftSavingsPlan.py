import requests, pandas
from io import StringIO
from datetime import datetime, timedelta
import time
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
import numpy as np
	
def SMA(a, n):
	return np.convolve(a, np.ones((n,))/n, mode='valid')

today = datetime.now().strftime("%m/%d/%Y")
start = (datetime.now() - timedelta(days=365)).strftime("%m/%d/%Y")
	
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
	
	plt.title('Thrift Savings Plan Funds from ' + TSP['date'][0].strftime("%m/%d/%Y") + ' to ' + TSP['date'][len(TSP['date'])-1].strftime("%m/%d/%Y"))
	plt.plot_date(dates, TSP['G Fund'], '-', label="G Fund")
	plt.plot_date(dates, TSP['F Fund'], '-', label="F Fund")
	plt.plot_date(dates, TSP['C Fund'], '-', label="C Fund")
	plt.plot_date(dates, TSP['S Fund'], '-', label="S Fund")
	plt.plot_date(dates, TSP['I Fund'], '-', label="I Fund")
	
	#manager = plt.get_current_fig_manager()
	#manager.resize(*manager.window.maxsize())
	#manager.window.wm_geometry("+0+0")
	
	plt.xlabel('Date')
	plt.ylabel('Share Value ($)')
	
	plt.legend(loc=2)
	plt.show(block=True)
	
	plt.cla()
	
	nl = 10
	nh = 30
	
	for fund in ['G', 'F', 'C', 'S', 'I']:
		datesall = date2num(TSP['date'])
		datesnl = date2num(TSP['date'][nl - 1:])
		datesnh = date2num(TSP['date'][nh - 1:])
		
		plt.title('Thrift Savings Plan ' + fund + ' Fund from ' + TSP['date'][0].strftime("%m/%d/%Y") + ' to ' + TSP['date'][len(TSP['date'])-1].strftime("%m/%d/%Y"))
		plt.plot_date(datesall, TSP[fund + ' Fund'], '-', label=fund + " Fund")
		plt.plot_date(datesnl, SMA(TSP[fund + ' Fund'], nl), '-', label=fund + " Fund (" + str(nl) + " day)")
		plt.plot_date(datesnh, SMA(TSP[fund + ' Fund'], nh), '-', label=fund + " Fund (" + str(nh) + " day)")
		
		#manager = plt.get_current_fig_manager()
		#manager.resize(*manager.window.maxsize())
		#manager.window.wm_geometry("+0+0")

		plt.xlabel('Date')
		plt.ylabel('Share Value ($)')

		plt.legend(loc=2)
		plt.show(block=True)
