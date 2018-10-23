import pytz
import numpy as np
from datetime import datetime, timedelta
from matplotlib.dates import num2date, date2num
import pandas as pd
from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import AbstractHolidayCalendar, USFederalHolidayCalendar, Holiday, nearest_workday, USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay, USLaborDay, USThanksgivingDay

class USTradingCalendar(AbstractHolidayCalendar):
	rules = [
		Holiday('NewYearsDay', month=1, day=1, observance=nearest_workday),
		USMartinLutherKingJr,
		USPresidentsDay,
		GoodFriday,
		USMemorialDay,
		Holiday('USIndependenceDay', month=7, day=4, observance=nearest_workday),
		USLaborDay,
		USThanksgivingDay,
		Holiday('ChristmasDay', month=12, day=25, observance=nearest_workday)
    ]

class TSPTradingCalendar(AbstractHolidayCalendar):
	rules = USFederalHolidayCalendar().rules
	rules.append(GoodFriday)

class BasicFinance:
	def __init__(self):
		pass

	def getFederalTradingDays(self, dts, dte):
		inst = CustomBusinessDay(calendar=TSPTradingCalendar())
		return pd.DatetimeIndex(start=dts, end=dte, freq=inst)

	def getNextFederalTradingDay(self, dts):
		return (self.getFederalTradingDays(dts.date()+timedelta(days=1), (dts+timedelta(days=7)).date()).tolist()[0]).date()

	def getTradingDays(self, dts, dte):
		inst = CustomBusinessDay(calendar=USTradingCalendar())
		return pd.DatetimeIndex(start=dts, end=dte, freq=inst)

	def getNextTradingDay(self, dts):
		return (self.getTradingDays(dts.date()+timedelta(days=1), (dts+timedelta(days=7)).date()).tolist()[0]).date()

	def formatDate(self, dt):
		return dt.strftime("%Y/%m/%d")

	def formatTime(self, dt):
		return dt.strftime("%H:%M:%S")

	def daysSince(self, dt):
		return (datetime.now().date() - dt).days

	# Define a simple moving average that replaces invalid positions with NaN:
	def SMA(self, l, n):
		# Start with empty list and fill invalid values first:
		ma = [np.nan]*n
		# Move through the valid positions in list and compute moving average:
		for i in range(n, len(l)):
			ma.append(np.mean(l[i-n:i]))
		# Return result
		return ma

	# Define an exponential weighted moving average:
	def EWMA(self, data, window):
		if type(data) == list:
			data = np.array(data)

		alpha = 2 / (window + 1.)
		alpha_rev = 1 - alpha

		scale = 1 / alpha_rev
		n = data.shape[0]

		r = np.arange(n)
		scale_arr = scale ** r
		offset = data[0] * alpha_rev ** (r + 1)
		pw0 = alpha * alpha_rev ** (n - 1)

		mult = data * pw0 * scale_arr
		cumsums = mult.cumsum()

		return offset + cumsums * scale_arr[::-1]

	# Detect buy and sell crossovers of two SMA lists and return signals:
	def detectCrossovers(self, dates, smanl, smanh, dd):
		# Create empty data structure:
		crossovers = []

		# Detect change in sign at every point in the difference of two source lists:
		for i in np.where(np.diff(np.sign((smanl-smanh))))[0].reshape(-1):
			# If prices are the same, not a signal
			if smanl[i] == smanh[i]: continue

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
					ps = p[list(t).index(max(filter(lambda x: x < ts, t)))]
					gain -= ps
				else:
					if verbose: sys.stdout.write('sold')
					sl = (ts, ps)
					ps = p[list(t).index(max(filter(lambda x: x < ts, t)))]
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
