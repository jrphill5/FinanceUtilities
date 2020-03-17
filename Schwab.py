import os, sys, csv, glob
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dateutil import tz

from AlphaVantage import AlphaVantage

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
    blines = 0
    alines = 0
    strings = string.split('\n')
    for i in range(len(strings)):
        s = strings.pop(0)
        if s == '': blines += 1
        else:
            string = s
            for j in range(len(strings)):
                if strings.pop() == '':
                    alines += 1
                else: break
        if len(strings) == 0: break
    if space: string = " %s " % string
    strlen = len(string)
    padlen = length - strlen
    outstr = ""
    for i in range(blines-1):        outstr += '\n'
    for i in range(padlen//2):       outstr += padchar
    outstr += string
    if padlen % 2 == 0:
        for i in range(padlen//2):   outstr += padchar
    else:
        for i in range(padlen//2+1): outstr += padchar
    for i in range(alines-1):        outstr += '\n'
    return outstr

def print_csvdata(csvdata, csvinfo=None, csvhead=None, csvtail=None):
    headfmt = "%-11s %-11s %-29s %-10s %-39s %9s %9s %12s %12s"
    datafmt = "%-11s %-11s %-29s %-10s %-39s %9.3f %9.2f %12.2f %+12.2f"
    tailfmt = "%-21s %-1s %-29s %-10s %-39s %9.3f %9.2f %12.2f %+12.2f"
    print()
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
    print()
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
    print(center_string("", 35, "=", False))
    print(center_string("Total Contributions: $%.2f" % conttotl, 35, " "))
    print(center_string("", 35, "=", False))
    return contdate, contvalu, conttotl

def parse_positions(csvdata):
    positions = {'Sweep': []}
    for row in csvdata:
        if row[3]:
            if row[3] == "NO NUMBER":
                positions['Sweep'].append(row)
                continue
            elif row[3] not in positions:
                positions[row[3]] = []
            positions[row[3]].append(row)
        else:
            positions['Sweep'].append(row)
    return positions

def print_file_info(trnfile, posfile, balfile):
    lentrnfile = 0; lenposfile = 0; lenbalfile = 0
    if trnfile is not None: lentrnfile = len(trnfile)
    if posfile is not None: lenposfile = len(posfile)
    if balfile is not None: lenbalfile = len(balfile)
    print(center_string("File Information", max(lentrnfile, lenposfile, lenbalfile)+15, "=", True))
    print("Transactions : %s" % trnfile)
    print("Positions    : %s" % posfile)
    print("Balances     : %s" % balfile)
    print(center_string("", max(lentrnfile, lenposfile, lenbalfile)+15, "=", False))

def add_series(T1, V1, T2, V2, scale=1, zl=True, zr=False, verbose=False):

    T1 = T1.copy(); V1 = V1.copy()
    T2 = T2.copy(); V2 = V2.copy()
    TS = [];        VS = []
    i1 = 0;         i2 = 0

    if T1 != sorted(T1): print("[ERROR] first time series not sorted")
    if T2 != sorted(T2): print("[ERROR] second time series not sorted")

    T1min = T1[0]; T1max = T1[-1]
    T2min = T2[0]; T2max = T2[-1]
    TSmin = min(T1min, T2min)
    TSmax = max(T1max, T2max)

    if T1min != T2min and verbose: print("[WARN] time series do not share same start date (%s, %s)" % (T1min, T2min))
    if T1max != T2max and verbose: print("[WARN] time series do not share same end date (%s, %s)" % (T1max, T2max))

    if T1min > T2min:
        T1.insert(0, T2min)
        if zl: val = 0.
        else:  val = V1[0]
        V1.insert(0, val)
        if verbose: print("[WARN] expanding first time series to left with value of %.2f" % val)
    elif T2min > T1min:
        T2.insert(0, T1min)
        if zl: val = 0.
        else:  val = V2[0]
        V2.insert(0, val)
        if verbose: print("[WARN] expanding second time series to left with value of %.2f" % val)

    if T1max < T2max:
        T1.append(T2max)
        if zr: val = 0.
        else:  val = V1[-1]
        V1.append(val)
        if verbose: print("[WARN] expanding first time series to right with value of %.2f" % val)
    elif T2max < T1max:
        T2.append(T1max)
        if zr: val = 0.
        else:  val = V2[-1]
        V2.append(val)
        if verbose: print("[WARN] expanding second time series to right with value of %.2f" % val)

    while True:
        try:
            if T1[i1] == T2[i2]:
                TS.append(T1[i1])
                VS.append(V1[i1] + scale*V2[i2])
                i1 += 1
                i2 += 1
            elif T1[i1] < T2[i2]:
                TS.append(T1[i1])
                VS.append(V1[i1] + scale*V2[i2-1])
                i1 += 1
            elif T1[i1] > T2[i2]:
                TS.append(T2[i2])
                VS.append(V1[i1-1] + scale*V2[i2])
                i2 += 1
        except IndexError:
            break

    return remove_duplicates(TS, VS)

def remove_duplicates(T, V):
    Tnew = []; Vnew = []

    tp = 0; vp = 0
    for i, (t, v) in enumerate(zip(T, V)):
        v = round(v, 2)
        if i != len(T)-1:
            if vp != v:
                Tnew.append(t)
                Vnew.append(v)
        else:
            Tnew.append(t)
            Vnew.append(v)
        tp = t; vp = v

    T = Tnew; V = Vnew
    data = {}

    for i in range(len(T)):
        if T[i] not in data: data[T[i]] = []
        data[T[i]].append(V[i])

    T = sorted(data)
    Tnew = []; Vnew = []
    for i in range(len(T)):
        if len(data[T[i]]) > 1:
            Vmin = min(data[T[i]])
            Vmax = max(data[T[i]])
            diff = [abs(Vmin - np.mean(data[T[i-1]])), abs(Vmax - np.mean(data[T[i-1]])), abs(Vmin - np.mean(data[T[i+1]])), abs(Vmax - np.mean(data[T[i+1]]))]
            if   np.argmin(diff) == 0 or np.argmin(diff) == 1: data[T[i]] = data[T[i-1]]
            elif np.argmin(diff) == 2 or np.argmin(diff) == 3: data[T[i]] = data[T[i+1]]
        Tnew.append(T[i])
        Vnew.append(data[T[i]][0])

    return Tnew, Vnew

if __name__ == "__main__":

    avenable = True

    delim = ","

    datadir = os.path.join("Data", "Schwab")

    trnfile = None
    posfile = None
    balfile = None

    try: trnfile = sorted(glob.glob(os.path.join(datadir, "*Transactions*")), reverse=True)[0]
    except IndexError: pass

    try: posfile = sorted(glob.glob(os.path.join(datadir, "*Positions*")), reverse=True)[0]
    except IndexError: pass

    try: balfile = sorted(glob.glob(os.path.join(datadir, "*Balances*")), reverse=True)[0]
    except IndexError: pass

    print_file_info(trnfile, posfile, balfile)

    with open(trnfile) as fh:
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

    #print_csvdata(csvdata, csvinfo, csvhead, csvtail)
    contdate, contvalu, conttotl = parse_contribs(csvdata, csvinfo)

    TS = []; VS = []
    positions = parse_positions(csvdata)
    shareplot = {}
    basisplot = {}
    valueplot = {}
    costbasis = {}
    for symbol in sorted(positions.keys()):
        print()
        shareplot[symbol] = {'t': [], 'v': []}
        basisplot[symbol] = {'t': [], 'v': []}
        valueplot[symbol] = {'t': [], 'v': []}
        #print_csvdata(positions[symbol], "%s %s" % (symbol, csvinfo), csvhead)
        share = 0.0
        basis = 0.0
        value = 0.0
        headfmt = "O %-11s %-29s %12s %12s %12s %12s %12s"
        datafmt = "%1s %-11s %-29s %12.3f %+12.2f %12.3f %+12.2f %+12.2f"
        if symbol == 'Sweep': print(center_string("%s"     %  "Bank Sweep"                    , 108, "=", True))
        else:                 print(center_string("%s: %s" % (symbol, positions[symbol][0][4]), 108, "=", True))
        print(headfmt % (csvhead[0], csvhead[2], csvhead[5], csvhead[8], "Shares", "Basis", "Value"))
        for pos in reversed(positions[symbol]):
            share += -sign(pos[8])*pos[5]
            value += pos[8]
            if pos[2] not in ["Reinvest Dividend", "Cash Dividend", "Long Term Cap Gain Reinvest", "Short Term Cap Gain Reinvest", "Security Transfer", "Bank Interest", "Funds Received"]:
                basis += pos[8]
                warn   = " "
            else:
                warn   = "*"
            shareplot[symbol]['t'].append(mpl.dates.date2num(datetime.strptime(pos[0], "%m/%d/%Y")))
            basisplot[symbol]['t'].append(mpl.dates.date2num(datetime.strptime(pos[0], "%m/%d/%Y")))
            valueplot[symbol]['t'].append(mpl.dates.date2num(datetime.strptime(pos[0], "%m/%d/%Y")))
            if symbol == 'Sweep': shareplot[symbol]['v'].append(basis)
            else:                 shareplot[symbol]['v'].append(share)
            basisplot[symbol]['v'].append(basis)
            valueplot[symbol]['v'].append(value)
            print(datafmt % (warn, pos[0], pos[2], pos[5], pos[8], share, basis, value))
        costbasis[symbol] = basis
        shareplot[symbol]['t'].append(mpl.dates.date2num(datetime.strptime(" ".join(csvinfo.split()[-3:-1]), "%m/%d/%Y %H:%M:%S")))
        if symbol == 'Sweep': shareplot[symbol]['v'].append(basis)
        else:                 shareplot[symbol]['v'].append(share)
        basisplot[symbol]['t'].append(mpl.dates.date2num(datetime.strptime(" ".join(csvinfo.split()[-3:-1]), "%m/%d/%Y %H:%M:%S")))
        basisplot[symbol]['v'].append(basis)
        valueplot[symbol]['t'].append(mpl.dates.date2num(datetime.strptime(" ".join(csvinfo.split()[-3:-1]), "%m/%d/%Y %H:%M:%S")))
        valueplot[symbol]['v'].append(value)
        print(center_string("", 108, "=", False))
        print(datafmt % (" ", "Total", "", 0.0, 0.0, share, basis, value))
        print(center_string("", 108, "=", False))

        avdata = None
        if symbol == 'Sweep': pass
        elif avenable:
            try:
                av = AlphaVantage(symbol, dts=datetime.strptime(positions[symbol][-1][0], "%m/%d/%Y"), dte=datetime.strptime(" ".join(csvinfo.split()[-3:-1]), "%m/%d/%Y %H:%M:%S"))
                avdata = av.getData()
            except KeyError: pass

        if not avenable:        print(center_string("AlphaVantage Data Disabled!", 108, "=", True))
        elif symbol == 'Sweep': print(center_string("AlphaVantage Data Not Available for Bank Sweep", 108, "=", True))
        elif avdata is None:    print(center_string("AlphaVantage Data for %s Not Found!" % symbol, 108, "=", True))

        T = []
        V = []

        if avdata is None or len(avdata['Date']) == 0:
            print(center_string("Assuming %s Share Value Is $1.00" % symbol, 108, "=", True))
            dts = datetime.strptime(positions[symbol][-1][0], "%m/%d/%Y")
            dte = datetime.strptime(" ".join(csvinfo.split()[-3:-2]), "%m/%d/%Y")
            MT  = [dts + timedelta(days=x) for x in range(0, (dte-dts+timedelta(days=1)).days)]
            MV  = [1.0 for x in range(0, (dte-dts+timedelta(days=1)).days)]
            avdata = None
        else:
            MT  = avdata['Date']
            MV  = avdata['Close']

        if avdata is not None:
            print(center_string("AlphaVantage Update Time: %s" % MT[-1].strftime("%Y/%m/%d"), 108, "=", True))
        print(center_string("", 108, "=", False))
        
        for j, (mt, mv) in enumerate(zip(mpl.dates.date2num(MT), MV)):
            for i, pt in enumerate(shareplot[symbol]['t']):
                if pt > mt:
                    t = mt
                    if i == 0: v = 0
                    else:      v = mv*shareplot[symbol]['v'][i-1]
                    T.append(t)
                    V.append(v)
                    break

        if symbol != 'Sweep':
            if not TS and not VS:
                TS = T; VS = V
            else:
                TS, VS = add_series(TS, VS, T, V, zl=True, zr=False, verbose=False)

            plt.figure("Share Prices")
            plt.step(MT, MV, where="post", label=symbol)
            plt.title("Share Prices")
            plt.xlabel("Date")
            plt.ylabel("Share Price ($)")
            plt.legend()

            plt.figure("Portfolio Market Value")
            plt.step(mpl.dates.num2date(T, tz=tz.tzutc()), V, where="post", label=symbol)
            plt.title("Portfolio Market Value")
            plt.xlabel("Date")
            plt.ylabel("Value ($)")
            plt.legend()

    #valuetotal = 0.
    #for symbol in basisplot.keys():
    #    valuetotal += valueplot[symbol]['v'][-1]
    #    print("%-5s : %+9.2f %+9.2f" % (symbol, basisplot[symbol]['v'][-1], valueplot[symbol]['v'][-1]))
    #print("%-5s :           %+9.2f" % ("Avail", valuetotal))

    for symbol, plot in shareplot.items():
        if symbol == 'Sweep': continue
        plt.figure("Share Quantity")
        plt.step(mpl.dates.num2date(plot['t'], tz=tz.tzutc()), plot['v'], where="post", label=symbol)
        plt.title("Share Quantity")
        plt.xlabel("Date")
        plt.ylabel("Shares")
        plt.legend()

    basisTS = []; basisVS = []
    for symbol, plot in basisplot.items():
        if not basisTS and not basisVS:
            basisTS = plot['t']; basisVS = plot['v']
        else:
            basisTS, basisVS = add_series(basisTS, basisVS, plot['t'], plot['v'], zl=True, zr=False, verbose=False)
        plt.figure("Portfolio Basis")
        plt.step(mpl.dates.num2date(plot['t'], tz=tz.tzutc()), plot['v'], where="post", label=symbol)
        plt.title("Portfolio Basis")
        plt.xlabel("Date")
        plt.ylabel("Value ($)")
        plt.legend()
    plt.figure("Portfolio Basis")
    plt.step(mpl.dates.num2date(basisTS, tz=tz.tzutc()), basisVS, where="post", label="Total")
    plt.legend()

    valueTS = []; valueVS = []
    for symbol, plot in valueplot.items():
        if not valueTS and not valueVS:
            valueTS = plot['t']; valueVS = plot['v']
        else:
            valueTS, valueVS = add_series(valueTS, valueVS, plot['t'], plot['v'], zl=True, zr=False, verbose=False)
    plt.figure("Available Cash")
    plt.step(mpl.dates.num2date(valueTS, tz=tz.tzutc()), valueVS, where="post")
    plt.title("Available Cash ($%.2f)" % valueVS[-1])
    plt.xlabel("Date")
    plt.ylabel("Value ($)")

    TS, VS = add_series(TS, VS, valueTS, valueVS, zl=True, zr=False, verbose=False)
    plt.figure("Portfolio Market Value")
    plt.step(mpl.dates.num2date(valueTS, tz=tz.tzutc()), valueVS, where="post", label="Cash")
    plt.step(mpl.dates.num2date(TS, tz=tz.tzutc()), VS, where="post", label="Total")
    plt.legend()

    plt.figure("Account Contributions")
    plt.step(mpl.dates.num2date(contdate, tz=tz.tzutc()), contvalu, where="post")
    plt.title("Account Contributions ($%.2f)" % conttotl)
    plt.xlabel("Date")
    plt.ylabel("Contributed Value ($)")

    earnTS, earnVS = add_series(TS, VS, contdate, contvalu, scale=-1, zl=True, zr=False, verbose=False)
    plt.figure("Portfolio Earnings")
    plt.step(mpl.dates.num2date(earnTS, tz=tz.tzutc()), earnVS, where="post")
    plt.title(("Portfolio Earnings (%+.2f)" % earnVS[-1]).replace("+", "+$").replace("-", "-$"))
    plt.xlabel("Date")
    plt.ylabel("Earnings ($)")

    plt.figure("Portfolio Performance")
    plt.step(mpl.dates.num2date(TS, tz=tz.tzutc()), VS, where="post", label="Total")
    plt.step(mpl.dates.num2date(contdate, tz=tz.tzutc()), contvalu, where="post", label="Contributions")
    plt.step(mpl.dates.num2date(earnTS, tz=tz.tzutc()), earnVS, where="post", label="Earnings")
    plt.title("Portfolio Performance")
    plt.xlabel("Date")
    plt.ylabel("Value ($)")
    plt.legend()

    plt.show()
