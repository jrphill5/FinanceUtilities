import sqlite3, zlib
from Binance import request_ticker_prices, request_account_info, get_holdings, get_historical_value
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

def print_cell(value, column_width, precision, asset, asset_width):
    if value is None:
        print("%{}s".format(column_width) % '', end='')
    else:
        print("%{}.{}f".format(column_width, precision) % value, end='')
    if asset is None or value is None:
        print(" %-{}s".format(asset_width) % '', end='')
    else:
        print(" %-{}s".format(asset_width) % asset, end='')

def parse_float(value, tolerance):
    try:
        value = float(value)
        if abs(value) < tolerance: raise ValueError
    except ValueError:
        value = None
    return value

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

with open(filename, 'r', encoding='utf-8-sig') as fh:
    head = [x.strip() for x in fh.readline().split(',')]
    for line in fh:
        if not line.strip(): continue
        if 'EXIT' in line: break
        datum = [x.strip().replace('""', '') for x in line.split(',')]
        dt = datetime.strptime(datum[head.index('Time')].split('.')[0], datefmt).replace(tzinfo=timezone.utc)
        datum[head.index('Time')] = dt.strftime(datefmt)
        row = []; hashrow = []
        for idx in ['Time', 'Category', 'Operation']:
            row.append(datum[head.index(idx)])
            hashrow.append(datum[head.index(idx)])
        for asset in assets:
            row.append(datum[head.index(asset)])
            for idx, ass, colwid, pre, asswid, hashinc in [(asset_prefix+asset, asset, 14, 8, 4, True), (asset_prefix+asset+asset_suffix, 'USD', 12, 6, 3, False)]:
                datum[head.index(idx)] = parse_float(datum[head.index(idx)], 1e-16)
                row.append(datum[head.index(idx)])
                if hashinc: hashrow.append(datum[head.index(idx)])
        h = ["%08X" % zlib.crc32(b','.join([str(x).encode() for x in hashrow]))]
        cur.execute("INSERT OR IGNORE INTO binance VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", h+row)

con.commit()

cur.execute("SELECT * FROM binance ORDER BY datetime")
for h, t, c, o, pa, pq, pv, ba, bq, bv, qa, qq, qv, fa, fq, fv in cur.fetchall():
    if pa and not pv and pa != 'USD':
        print("[WARN] %s %s on %s has no basis (assuming " % (pa, o, t), end='')
        dt = datetime.strptime(t, datefmt).replace(tzinfo=timezone.utc)
        value = get_historical_value('%sUSD' % pa, year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute, second=dt.second)[4]
        pv = float(value)*float(pq)
        print("%.8f %s = $%.8f)" % (pq, pa, pv))
        cur.execute("UPDATE binance SET pval = ? WHERE id = ?", (pv, h))

con.commit()

for i, (col, wid) in enumerate([("DATE/TIME", 19), ("CATEGORY", 12), ("OPERATION", 15), ("PRIMARY_ASSET", 33), ("BASE_ASSET", 33), ("QUOTE_ASSET", 33), ("FEE_ASSET", 33)]):
    if i != 0: print(' '*2, end='')
    print_centered(col, wid, end='')
print()

cur.execute("SELECT * FROM binance ORDER BY datetime")
for h, t, c, o, pa, pq, pv, ba, bq, bv, qa, qq, qv, fa, fq, fv in cur.fetchall():

    if pa not in wallet: wallet[pa] = invest[pa] = basis[pa] = 0.
    if ba not in wallet: wallet[ba] = invest[ba] = basis[ba] = 0.
    if qa not in wallet: wallet[qa] = invest[qa] = basis[qa] = 0.
    if fa not in wallet: wallet[fa] = invest[fa] = basis[fa] = 0.

    for fmt, val in [("%-21s", t), ("%-14s", c), ("%-15s", o)]:
        print(fmt % val, end='')
    print_cell(pq, 14, 8, pa, 4); print_cell(pv, 12, 6, 'USD', 3)
    print_cell(bq, 14, 8, ba, 4); print_cell(bv, 12, 6, 'USD', 3)
    print_cell(qq, 14, 8, qa, 4); print_cell(qv, 12, 6, 'USD', 3)
    print_cell(fq, 14, 8, fa, 4); print_cell(fv, 12, 6, 'USD', 3)
    print()

    sign = None;
    for verb in ['Sell', 'Send', 'Withdrawal']:
        if verb in o: sign = -1
    for verb in ['Buy',  'Receive', 'Deposit', 'Rewards', 'Earn']:
        if verb in o: sign = +1
    if sign is None:
        sign = +1
        print("[WARN] %s operation not defined" % o)

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

con.close()

print()
value = sum([v['V'] for k, v in bals.items()])
print(("Cash: $%.2f $%.2f $%+.2f " % (basis['USD'], value, value-basis['USD'])).replace("$+", "+$").replace("$-", "-$"), end='')
if abs(basis['USD']) > 1e-8: print("%+.2f%%" % (100.*(value-basis['USD'])/basis['USD']))

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
