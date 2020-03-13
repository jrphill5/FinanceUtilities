import os, sys, glob
from datetime import datetime
import matplotlib.pyplot as plt

if len(sys.argv) == 1: directory = "BidAsk"
else:                  directory = sys.argv[1]

if not (os.path.exists(directory) and os.path.isdir(directory)):
    print("ERROR: '%s' not a valid directory!" % directory)
    exit(1)

dpi = 100

updated = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

PA = {}; SA = {}
PB = {}; SB = {}
for i, filename in enumerate(sorted(glob.glob(os.path.join(directory, "*.txt")))):

    string = ""
    with open(filename, 'r') as fh:
        fh.readline()
        for line in fh:
            string += line.strip()

    data = eval(string)

    asks = data['asks']
    bids = data['bids']

    for ask in asks:
        t = datetime.fromtimestamp(ask['timestamp']/1000.)
        PA[t] = ask['price']
        SA[t] = ask['size']

    for bid in bids:
        t = datetime.fromtimestamp(bid['timestamp']/1000.)
        PB[t] = bid['price']
        SB[t] = bid['size']

TPA = sorted(PA); VPA = []
TSA = sorted(SA); VSA = []
TPB = sorted(PB); VPB = []
TSB = sorted(SB); VSB = []

for t in TPA: VPA.append(PA[t])
for t in TSA: VSA.append(SA[t])
for t in TPB: VPB.append(PB[t])
for t in TSB: VSB.append(SB[t])

if len(TPA) > 0 or len(TPB) > 0:
    dprecent = sorted(TPA+TPB)[-1].strftime("%Y/%m/%d %H:%M:%S")
else: dprecent = None
if len(TSA) > 0 or len(TSB) > 0:
    dsrecent = sorted(TSA+TSB)[-1].strftime("%Y/%m/%d %H:%M:%S")
else: dsrecent = None
if len(VPA) > 0: askprice = VPA[-1]
else:            askprice = None
if len(VPB) > 0: bidprice = VPB[-1]
else:            bidprice = None
if len(VSA) > 0: asksize  = VSA[-1]
else:            asksize  = None
if len(VSB) > 0: bidsize  = VSB[-1]
else:            bidsize  = None

plt.figure(figsize=(1920/dpi, 1080/dpi), dpi=dpi)
plt.step(TSA, VSA, "-", where="post", label="Asks")
plt.step(TSB, VSB, "-", where="post", label="Bids")
sizetitle = "Size Time Series [Ask: "
if asksize is not None: sizetitle += "%d" % asksize
else:                   sizetitle += "None"
sizetitle += "] [Bid: "
if bidsize is not None: sizetitle += "%d" % bidsize
else:                   sizetitle += "None"
sizetitle += "] [Spread: "
if asksize is not None and bidsize is not None:
    sizetitle += "%d" % (asksize - bidsize)
else:
    sizetitle += "None"
sizetitle += "] [Recent: %s] [Updated: %s]" % (dprecent, updated)
plt.title(sizetitle)
plt.xlabel("Time")
plt.ylabel("Size")
plt.legend()
plt.savefig(os.path.join(directory, "PlotSizeTime.png"), bbox_inches="tight")

plt.figure(figsize=(1920/dpi, 1080/dpi), dpi=dpi)
plt.step(TPA, VPA, "-", where="post", label="Asks")
plt.step(TPB, VPB, "-", where="post", label="Bids")
pricetitle = "Price Time Series [Ask: "
if askprice is not None: pricetitle += "$%.2f" % askprice
else:                    pricetitle += "None"
pricetitle += "] [Bid: "
if bidprice is not None: pricetitle += "$%.2f" % bidprice
else:                    pricetitle += "None"
pricetitle += "] [Spread: "
if askprice is not None and bidprice is not None:
    pricetitle += "$%.2f" % (askprice - bidprice)
else:
    pricetitle += "None"
pricetitle += "] [Recent: %s] [Updated: %s]" % (dprecent, updated)
plt.title(pricetitle)
plt.xlabel("Time")
plt.ylabel("Price ($)")
plt.legend()
plt.savefig(os.path.join(directory, "PlotPriceTime.png"), bbox_inches="tight")

plt.show()
