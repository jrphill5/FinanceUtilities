import requests, pandas
from StringIO import StringIO
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
import numpy as np
	
def SMA(a, n):
	return np.convolve(a, np.ones((n,))/n, mode='valid')

url = "https://www.tsp.gov/InvestmentFunds/FundPerformance/index.html"
data = {'whichButton': 'CSV', 'startdate': '01/01/2016', 'enddate': '01/10/2017'}

response = requests.post(url, data=data)

if response.status_code != 200:
	print("Error " + response.status_code)
else:
	df = pandas.read_csv(StringIO(response.text)).sort_values('date')
	
	TSP = {}
	
	for k, v in df.to_dict('list').iteritems():
		kn = k.strip()
		if len(kn) > 0:
			TSP[kn] = v
	
	TSP['date'] = [datetime.strptime(date, '%Y-%m-%d') for date in TSP['date']]
	
	dates = date2num(TSP['date'])
	
	plt.plot_date(dates, TSP['G Fund'], '-', label="G Fund")
	plt.plot_date(dates, TSP['F Fund'], '-', label="F Fund")
	plt.plot_date(dates, TSP['C Fund'], '-', label="C Fund")
	plt.plot_date(dates, TSP['S Fund'], '-', label="S Fund")
	plt.plot_date(dates, TSP['I Fund'], '-', label="I Fund")
	
	manager = plt.get_current_fig_manager()
	manager.resize(*manager.window.maxsize())
	manager.window.wm_geometry("+0+0")
	
	plt.legend(loc=2)
	plt.show(block=True)
	
	plt.cla()
	
	nl = 10
	nh = 30
	
	for fund in ['G', 'F', 'C', 'S', 'I']:
		datesall = date2num(TSP['date'])
		datesnl = date2num(TSP['date'][nl - 1:])
		datesnh = date2num(TSP['date'][nh - 1:])
		
		plt.plot_date(datesall, TSP[fund + ' Fund'], '-', label=fund + " Fund")
		plt.plot_date(datesnl, SMA(TSP[fund + ' Fund'], nl), '-', label=fund + " Fund (" + str(nl) + " day)")
		plt.plot_date(datesnh, SMA(TSP[fund + ' Fund'], nh), '-', label=fund + " Fund (" + str(nh) + " day)")
		
		manager = plt.get_current_fig_manager()
		manager.resize(*manager.window.maxsize())
		manager.window.wm_geometry("+0+0")
		
		plt.legend(loc=2)
		plt.show(block=True)