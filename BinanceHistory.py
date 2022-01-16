import sqlite3, sys, zlib
from Binance import request_ticker_prices, request_account_info, get_holdings

con = sqlite3.connect('binance.db')
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS binance (id TEXT PRIMARY KEY UNIQUE, datetime TEXT, category TEXT, operation TEXT, pass TEXT, pqty REAL, pval REAL, bass TEXT, bqty REAL, bval REAL, qass TEXT, qqty REAL, qval REAL, fass TEXT, fqty REAL, fval real)")

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

head = []
data = {}
with open(filename, 'r', encoding='utf-8-sig') as fh:
    head = [x.strip() for x in fh.readline().split(',')]
    for item in head:
        data[item] = []
    print("-----DATE/TIME-----  --CATEGORY--  ---OPERATION---  ----------PRIMARY_ASSET----------  -----------BASE_ASSET------------  -----------QUOTE_ASSET-----------  ------------FEE_ASSET------------")
    for line in fh:
        if not line.strip(): continue
        if 'EXIT' in line: break
        datum = [x.strip().replace('""', '') for x in line.split(',')]
        print("%-21s" % datum[head.index('Time')].split('.')[0], end='')
        print("%-14s" % datum[head.index('Category')], end='')
        print("%-15s" % datum[head.index('Operation')], end='')
        row = [datum[head.index('Time')].split('.')[0], datum[head.index('Category')], datum[head.index('Operation')]]
        for asset in assets:
            parse_float(datum, asset_prefix+asset,              1e-16)
            parse_float(datum, asset_prefix+asset+asset_suffix, 1e-16)
            print_cell(asset_prefix+asset,              14, 8, asset, 4)
            print_cell(asset_prefix+asset+asset_suffix, 12, 6, 'USD', 3)
            row.append(datum[head.index(asset)])
            row.append(datum[head.index(asset_prefix+asset)])
            row.append(datum[head.index(asset_prefix+asset+asset_suffix)])
        print()
        for asset in assets:
            if head.index(asset) not in datum:
                wallet[datum[head.index(asset)]] = 0.
                invest[datum[head.index(asset)]] = 0.
                basis[datum[head.index(asset)]] = 0.
        for i, v in enumerate(datum):
            data[head[i]].append(datum[i])
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
print("============== WALLET ==============")
print("       ---OFFLINE---   ---BINANCE---")
for k, v in wallet.items():
    if k:
        print("%-4s %15.8f " % (k, v), end='')
        if k in bals:
            print("%15.8f" % bals[k]['T'], end='')
            if abs(bals[k]['T'] - v) > 1e-8: print(" *", end='')
        else:
            print("%15.8f" % 0, end='')
            if v > 1e-8: print(" *", end='')
        print()

print()
print("========================== INVESTED =========================")
print("       ----INPUT----  ----VALUE----  ----DELTA----  --DELTA--")
for k, v in invest.items():
    if k == 'USD': continue
    if k:
        print(("%-4s %+14.6f" % (k, v)).replace("+", "+$").replace("-", "-$"), end='')
        if k in bals:
            print(("%+14.6f" % bals[k]['V']).replace("+", "+$").replace("-", "-$"), end='')
            print(("%+14.6f" % (bals[k]['V']-v)).replace("+", "+$").replace("-", "-$"), end='')
            if abs(v) < 1e-8: print()
            else: print("%+10.2f%%" % (100.*(bals[k]['V']-v)/v))
        else:
            print(("%+14.6f" % 0.).replace("+", "+$").replace("-", "-$"), end='')
            print(("%+14.6f" % -v).replace("+", "+$").replace("-", "-$"))

print()
print("======================== PERFORMANCE ========================")
print("       ----BASIS----  ----VALUE----  ----DELTA----  --DELTA--")
for k, v in basis.items():
    if k == 'USD': continue
    if k:
        print(("%-4s %+14.6f" % (k, v)).replace('-', '-$').replace('+', '+$'), end='')
        if k in bals:
            print(("%+14.6f" % bals[k]['V']).replace("+", "+$").replace("-", "-$"), end='')
            print(("%+14.6f" % (bals[k]['V']-v)).replace("+", "+$").replace("-", "-$"), end='')
            print("%+10.2f%%" % (100.*(bals[k]['V']-v)/v))
        else:
            print(("%+14.6f" % 0.).replace("+", "+$").replace("-", "-$"), end='')
            print(("%+14.6f" % -v).replace("+", "+$").replace("-", "-$"))
