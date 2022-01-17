import sqlite3, zlib
from Binance import request_ticker_prices, request_account_info, get_holdings
from datetime import datetime, timezone

datefmt = '%Y-%m-%d %H:%M:%S'

con = sqlite3.connect('binance.db')
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS binance (id TEXT PRIMARY KEY UNIQUE, datetime TEXT, category TEXT, operation TEXT, pass TEXT, pqty REAL, pval REAL, bass TEXT, bqty REAL, bval REAL, qass TEXT, qqty REAL, qval REAL, fass TEXT, fqty REAL, fval REAL)")

bals = get_holdings(request_account_info(), request_ticker_prices())

print()
print("===============================================================================")
print()

filename = "BinanceStatement.csv"

omit = ['User_Id', 'Order_Id', 'Transaction_Id', 'Withdrawal_Method', 'Additional_Note', 'Payment_Method']

assets = ['Primary_Asset', 'Base_Asset', 'Quote_Asset', 'Fee_Asset']
asset_prefix = 'Realized_Amount_For_'
asset_suffix = '_In_USD_Value'

basis  = {}
invest = {}
wallet = {}

def print_cell(column, column_width, precision, asset, asset_width):
    if datum[head.index(column)] is None:
        print("%{}s".format(column_width) % '', end='')
        print(" %-{}s".format(asset_width) % '', end='')
    else:
        print("%{}.{}f".format(column_width, precision) % datum[head.index(column)], end=''),
        if asset in head:
            print(" %-{}s".format(asset_width) % datum[head.index(asset)], end='')
        else:
            print(" %-{}s".format(asset_width) % asset, end='')

def parse_float(datum, column, tolerance):
    try:
        datum[head.index(column)] = float(datum[head.index(column)])
        if abs(datum[head.index(column)]) < tolerance: raise ValueError
    except ValueError:
        datum[head.index(column)] = None

def print_centered(string, width, char='-', end=None):
    pad = (width-len(string))//2
    print("%s%s%s" % (char*pad, string, char*(pad+(width-len(string))%2)), end=end)

def print_table_header(cols, char, sep, ind=0):
    for i, (col, wid) in enumerate(cols):
        if i == 0: print(' '*ind, end='')
        else:      print(' '*sep, end='')
        print_centered(col, wid, char, end='')
    print()

def print_value(val, wid, pre, bef='', aft='', end=None):
    print(("%+{}.{}f%s".format(wid, pre) % (val, aft)).replace("+", "+{}".format(bef)).replace("-", "-{}".format(bef)), end=end)

head = []
data = {}
with open(filename, 'r', encoding='utf-8-sig') as fh:
    head = [x.strip() for x in fh.readline().split(',')]
    for item in head: data[item] = []
    for i, (col, wid) in enumerate([("DATE/TIME", 19), ("CATEGORY", 12), ("OPERATION", 15), ("PRIMARY_ASSET", 33), ("BASE_ASSET", 33), ("QUOTE_ASSET", 33), ("FEE_ASSET", 33)]):
        if i != 0: print("  ", end='')
        print_centered(col, wid, end='')
    print()
    for line in fh:
        if not line.strip(): continue
        if 'EXIT' in line: break
        datum = [x.strip().replace('""', '') for x in line.split(',')]
        dt = datetime.strptime(datum[head.index('Time')].split('.')[0], datefmt).replace(tzinfo=timezone.utc)
        datum[head.index('Time')] = dt.strftime(datefmt)
        row = []
        for fmt, idx in [("%-21s", 'Time'), ("%-14s", 'Category'), ("%-15s", 'Operation')]:
            print(fmt % datum[head.index(idx)], end='')
            row.append(datum[head.index(idx)])
        for asset in assets:
            row.append(datum[head.index(asset)])
            for idx, ass, colwid, pre, asswid in [(asset_prefix+asset, asset, 14, 8, 4), (asset_prefix+asset+asset_suffix, 'USD', 12, 6, 3)]:
                parse_float(datum, idx, 1e-16)
                print_cell(idx, colwid, pre, ass, asswid)
                row.append(datum[head.index(idx)])
            if head.index(asset) not in datum:
                wallet[datum[head.index(asset)]] = 0.
                invest[datum[head.index(asset)]] = 0.
                basis[datum[head.index(asset)]] = 0.
        print()
        for i, v in enumerate(datum):
            data[head[i]].append(v)
        h = ["%08X" % zlib.crc32(b','.join([str(x).encode() for x in row]))]
        cur.execute("INSERT OR IGNORE INTO binance VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", h+row)

con.commit()

cur.execute("SELECT * FROM binance ORDER BY datetime")
names = [desc[0] for desc in cur.description]
for row in cur.fetchall():
    h, t, c, o, pa, pq, pv, ba, bq, bv, qa, qq, qv, fa, fq, fv = row
    sign = None;
    for verb in ['Sell', 'Send', 'Withdrawal']:
        if verb in o: sign = -1
    for verb in ['Buy',  'Receive', 'Deposit', 'Rewards', 'Earn']:
        if verb in o: sign = +1
    if sign is None:
        sign = +1
        print("[WARN] %s not defined" % o)

    if "USD" in qa: inv = -1
    else:           inv = +1

    if qv: invest[ba] +=     sign*float(qv)
    if fv: invest[ba] +=          float(fv)

    if pq: wallet[pa] +=     sign*float(pq)
    if bq: wallet[ba] +=     sign*float(bq)
    if qq: wallet[qa] += inv*sign*float(qq)
    if fq: wallet[fa] -=          float(fq)

    if pv: basis[pa]  +=     sign*float(pv)
    if qv: basis[ba]  +=     sign*float(qv)
    if fv: basis[ba]  +=          float(fv)

    if pa and not pv and "Deposit" not in o:
        print("[WARN] %s %s on %s has no basis" % (pa, o, t))

con.close()

print()
value = sum([v['V'] for k, v in bals.items()])
print(("Cash: $%.2f $%.2f $%+.2f %+.2f%%" % (basis['USD'], value, value-basis['USD'], 100.*(value-basis['USD'])/basis['USD'])).replace("$+", "+$").replace("$-", "-$"))

print()
print_centered(" WALLET ", 35, '=')
print_table_header([("OFFLINE", 13), ("BINANCE", 13)], '-', 2, 7)
for k, v in wallet.items():
    if k:
        print("%-4s " % k, end='')
        print_value(v, 15, 8, end='')
        if k in bals:
            print_value(bals[k]['T'], 15, 8, end='')
            if abs(bals[k]['T']-v) > 1e-8: print(" *", end='')
        else:
            print_value(0, 15, 8, end='')
            if abs(v) > 1e-8: print(" *", end='')
        print()

for title, collection in [(" INVESTED ", invest), (" PERFORMANCE ", basis)]:
    print()
    print_centered(title, 61, '=')
    print_table_header([("INPUT", 13), ("VALUE", 13), ("DELTA", 13), ("DELTA", 9)], '-', 2, 7)
    for k, v in collection.items():
        if k:
            if k == 'USD': continue
            print("%-4s " % k, end='')
            print_value(v, 15, 6, end='')
            if k in bals:
                print_value(bals[k]['V'],   14, 6, bef='$', end='')
                print_value(bals[k]['V']-v, 14, 6, bef='$', end='')
                if abs(v) > 1e-8:
                    print_value(100.*(bals[k]['V']-v)/v, 10, 2, aft='%', end='')
            else:
                print_value(0., 14, 6, bef='$', end='')
                print_value(-v, 14, 6, bef='$', end='')
            print()
