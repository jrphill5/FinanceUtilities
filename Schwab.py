import os, sys, csv
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dateutil import tz

from AlphaVantage import AlphaVantage

delim = ","

datadir = os.path.join("Data", "Schwab")

def sign(val):
    if   val < 0.0: return -1
    elif val > 0.0: return +1
    else:           return  0

def remove_trailing_delims(fh, delim=","):
    for row in fh:
        row = row.strip()
        if row[-1] == delim: yield row[:-1]
        else:                yield row

def center_string(string, length=80, padchar=" ", space=False):
    if space: string = " %s " % string
    strlen = len(string)
    padlen = length - strlen
    outstr = ""
    for i in range(padlen//2):       outstr += padchar
    outstr += string
    if padlen % 2 == 0:
        for i in range(padlen//2):   outstr += padchar
    else:
        for i in range(padlen//2+1): outstr += padchar
    return outstr

def print_csvdata(csvdata, csvinfo=None, csvhead=None, csvtail=None):
    headfmt = "%-11s %-11s %-29s %-10s %-39s %9s %9s %12s %12s"
    datafmt = "%-11s %-11s %-29s %-10s %-39s %9.3f %9.2f %12.2f %+12.2f"
    tailfmt = "%-21s %-1s %-29s %-10s %-39s %9.3f %9.2f %12.2f %+12.2f"
    if csvinfo is not None: print(center_string(csvinfo, 150, "=", True))
    if csvhead is not None: print(headfmt % tuple(csvhead))
    for i, row in enumerate(csvdata):
        if len(row) == 9:   print(datafmt % tuple(row))
        else:               print(row)
    print(center_string("", 150, "=", False))
    if csvtail is not None:
        print(tailfmt % tuple(csvtail))
        print(center_string("", 150, "=", False))

def parse_contribs(csvdata, csvinfo=None, initvalu=0.0, verbose=False):
    conttotl = initvalu
    contdate = []
    contvalu = []
    if verbose:
        print(center_string("Contributions", 35, "=", True))
        print("%-10s %11s %12s" % ("Date", "Transfer", "Balance"))
    for i, row in enumerate(reversed(csvdata)):
        if i == 0:
            contdate.append(mpl.dates.date2num(datetime.strptime(row[0], "%m/%d/%Y")))
            contvalu.append(conttotl)
        if row[2] == "MoneyLink Deposit" or row[2] == "MoneyLink Transfer":
            conttotl += row[8]
            contdate.append(mpl.dates.date2num(datetime.strptime(row[0], "%m/%d/%Y")))
            contvalu.append(conttotl)
            if verbose: print("%-10s %+11.2f %12.2f" % (row[0], row[8], conttotl))
    if csvinfo is not None:
        contdate.append(mpl.dates.date2num(datetime.strptime(" ".join(csvinfo.split()[-3:-1]), "%m/%d/%Y %H:%M:%S")))
        contvalu.append(conttotl)
    if verbose:
        print(center_string("", 35, "=", False))
        print(center_string("Total Contributions: $%.2f" % conttotl, 35, " "))
        print(center_string("", 35, "=", False))
    return contdate, contvalu, conttotl

def parse_positions(csvdata, verbose=False):
    positions = {}
    for row in csvdata:
        if row[3]:
            if row[3] not in positions: positions[row[3]] = []
            positions[row[3]].append(row)
    return positions

datafil = os.path.join(datadir, sorted(os.listdir(datadir), reverse=True)[0])
print(center_string(datafil, 150, "=", True))

with open(datafil) as fh:
    csvread = csv.reader(remove_trailing_delims(fh, delim), delimiter=delim, quotechar='"')
    csvdata = []
    for i, row in enumerate(csvread):
        if i == 0:
            csvinfo = ','.join([x.replace("  ", " ") for x in row])
            continue
        elif i == 1:
            row.insert(1, "Effective")
            csvhead = row
            continue
        elif len(row) == 8:
            dateinfo = row[0].split(" as of ")
            row[0] = dateinfo[0]
            if len(dateinfo) == 1: row.insert(1, "")
            else:                  row.insert(1, dateinfo[1])
            for i in range(5, 9, 1):
                try:               row[i] = float(row[i].replace('$', ''))
                except ValueError: row[i] = 0.0
        else:
            print("Warning on row %d of input file!" % i)
            continue
        csvdata.append(row)
    csvtail = csvdata.pop()

print_csvdata(csvdata, csvinfo, csvhead, csvtail)
contdate, contvalu, conttotl = parse_contribs(csvdata, csvinfo, verbose=True)

positions = parse_positions(csvdata)
shareplot = {}
for symbol in sorted(positions.keys()):
    shareplot[symbol] = {'t': [], 'v': []}
    #print_csvdata(positions[symbol], "%s %s" % (symbol, csvinfo), csvhead)
    share = 0.0
    value = 0.0
    headfmt = "%-11s %-29s %12s %12s %12s %12s"
    datafmt = "%-11s %-29s %12.3f %+12.2f %12.3f %+12.2f"
    print(center_string("%s: %s" % (symbol, positions[symbol][0][4]), 93, "=", True))
    print(headfmt % (csvhead[0], csvhead[2], csvhead[5], csvhead[8], "Cum Share", "Cum Value"))
    for pos in reversed(positions[symbol]):
        share += -sign(pos[8])*pos[5]
        value +=               pos[8]
        shareplot[symbol]['t'].append(mpl.dates.date2num(datetime.strptime(pos[0], "%m/%d/%Y")))
        shareplot[symbol]['v'].append(share)
        print(datafmt % (pos[0], pos[2], pos[5], pos[8], share, value))
    shareplot[symbol]['t'].append(mpl.dates.date2num(datetime.strptime(" ".join(csvinfo.split()[-3:-1]), "%m/%d/%Y %H:%M:%S")))
    shareplot[symbol]['v'].append(share)
    print(center_string("", 93, "=", False))
    print(datafmt % ("Total", "", 0.0, 0.0, share, value))
    print(center_string("", 93, "=", False))

    av = AlphaVantage(symbol, dts=datetime.strptime(positions[symbol][-1][0], "%m/%d/%Y"), dte=datetime.strptime(" ".join(csvinfo.split()[-3:-1]), "%m/%d/%Y %H:%M:%S"))
    avdata = av.getData()
    if avdata is None:
        print("Data for %s could not be found!" % symbol)
        continue

    T = []
    V = []

    if len(avdata['Date']) == 0:
        print("Assuming %s share value is $1.00" % symbol)
        dts = datetime.strptime(positions[symbol][-1][0], "%m/%d/%Y")
        dte = datetime.strptime(" ".join(csvinfo.split()[-3:-2]), "%m/%d/%Y")
        MT  = [dts + timedelta(days=x) for x in range(0, (dte-dts+timedelta(days=1)).days)]
        MV  = [1.0 for x in range(0, (dte-dts+timedelta(days=1)).days)]
    else:
        MT  = avdata['Date']
        MV  = avdata['Close']
    
    for j, (mt, mv) in enumerate(zip(mpl.dates.date2num(MT), MV)):
        for i, pt in enumerate(shareplot[symbol]['t']):
            if pt > mt:
                t = mt
                if i == 0: v = 0
                else:      v = mv*shareplot[symbol]['v'][i-1]
                T.append(t)
                V.append(v)
                break

    plt.figure()
    plt.step(MT, MV, where="post")
    plt.title("%s Share Prices" % symbol)
    plt.xlabel("Date")
    plt.ylabel("Share Price ($)")

    plt.figure()
    plt.step(mpl.dates.num2date(T, tz=tz.tzutc()), V, where="post")
    plt.title("%s Portfolio Value" % symbol)
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value ($)")

for symbol, plot in shareplot.items():
    plt.figure()
    plt.step(mpl.dates.num2date(plot['t'], tz=tz.tzutc()), plot['v'], where="post")
    plt.title("%s Share Quantity" % symbol)
    plt.xlabel("Date")
    plt.ylabel("Shares")

plt.figure()
plt.step(mpl.dates.num2date(contdate, tz=tz.tzutc()), contvalu, where="post")
plt.title("Account Contributions")
plt.xlabel("Date")
plt.ylabel("Contributed Value ($)")
plt.show()
