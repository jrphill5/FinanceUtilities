import os, sys, glob
from datetime import datetime
import matplotlib.pyplot as plt

if len(sys.argv) == 1:
    directory = "BidAsk"
else:
    directory = sys.argv[1]

if not (os.path.exists(directory) and os.path.isdir(directory)):
    print("ERROR: '%s' not a valid directory!" % directory)
    exit(1)

dpi = 100

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

plt.figure(figsize=(1920/dpi, 1080/dpi), dpi=dpi)
plt.step(TSA, VSA, ".", where="post", label="Asks")
plt.step(TSB, VSB, ".", where="post", label="Bids")
plt.title("Size vs. Time [Last Updated %s]" % datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
plt.xlabel("Date/Time")
plt.ylabel("Size")
plt.legend()
plt.savefig(os.path.join(directory, "PlotSizeTime.png"), bbox_inches="tight")

plt.figure(figsize=(1920/dpi, 1080/dpi), dpi=dpi)
plt.step(TPA, VPA, ".", where="post", label="Asks")
plt.step(TPB, VPB, ".", where="post", label="Bids")
plt.title("Price vs. Time [Last Updated %s]" % datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
plt.xlabel("Time")
plt.ylabel("Price ($)")
plt.legend()
plt.savefig(os.path.join(directory, "PlotPriceTime.png"), bbox_inches="tight")

plt.show()
