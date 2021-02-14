import collections
import requests, json
import hmac, hashlib, time
from datetime import datetime

# Create file called binanceapi.py and define api_sec, api_key strings
from binanceapi import api_sec, api_key

units = collections.OrderedDict()
units["USD"]  = (12, 4)
units["BUSD"] = (15, 5)
units["USDT"] = (15, 5)
units["USDC"] = (15, 5)
units["BTC"]  = (15, 8)

def verify_response(r):
    if r.status_code != 200:
        exit("ERROR (CODE %d)!" % r.status_code)

def request_data_without_key(url, params=None):
    r = requests.get(url, params=None)
    verify_response(r)
    j = json.loads(r.text)
    return r, j

def sign_query(payload):
    query = '&'.join(["{}={}".format(k, v) for (k, v) in payload])
    m = hmac.new(api_sec.encode('utf-8'), query.encode('utf-8'), hashlib.sha256)
    return m.hexdigest()

def request_data_with_key(url, params={}):
    headers = {"X-MBX-APIKEY": api_key}
    params['timestamp'] = int(round(time.time()) * 1000)
    payload = []
    for k in sorted(params):
        payload.append((k, params[k]))
    params['signature'] = sign_query(payload)
    r = requests.get(url, params=params, headers=headers)
    verify_response(r)
    j = json.loads(r.text)
    return r, j

def request_ticker_prices():
    r, j = request_data_without_key("https://api.binance.us/api/v3/ticker/price")

    data = {}
    for item in j:
        symbolto = ""
        for unit in sorted(units, key=len):
            if item['symbol'].endswith(unit) and len(item['symbol'][:-len(unit)]) > 2:
                symbolto = unit
        symbolfrom = item['symbol'][:-len(symbolto)]
        if symbolfrom not in data: data[symbolfrom] = {}
        data[symbolfrom][symbolto] = float(item['price'])
    return data

def print_ticker_table(prices):
    print()
    print("================================ CURRENT PRICES ================================")
    print()
    print("%-8s" % '', end="")
    for unit, (l, p) in units.items():
        print("%{}s".format(l) % unit, end="")
    print()
    for symbol in sorted(prices):
        print("%-8s" % symbol, end="")
        for unit, (l, p) in units.items():
            if unit not in prices[symbol]:
                print("%{}s".format(l) % '', end="")
            else:
                print("%{}.{}f".format(l, p) % prices[symbol][unit], end="")
        print()

prices = request_ticker_prices()
print_ticker_table(prices)

def request_account_info():
    r, j = request_data_with_key('https://api.binance.us/api/v3/account')
    print()
    print("================================= ACCOUNT INFO ================================")
    print()
    for item in sorted(j):
        if item == 'updateTime':
            print("%-{}s %s".format(16) % (item, datetime.fromtimestamp(int(j['updateTime']/1000.))))
        elif item != 'balances':
            print("%-{}s %s".format(16) % (item, j[item]))
    return r, j

def get_holdings(j, prices=None):
    print("balances")

    eps = 1e-9
    bals = {}
    for d in j['balances']:
        bals[d['asset']] = {'F': float(d['free']), 'L': float(d['locked']), 'T': float(d['free'])+float(d['locked'])}
        if prices is not None:
            try:
                bals[d['asset']]['V'] = bals[d['asset']]['T'] * prices[d['asset']]['USD']
            except KeyError:
                bals[d['asset']]['V'] = bals[d['asset']]['T']
    total = 0
    for k, d in bals.items():
        if d['T'] > eps:
            print(" %-5s -> " % k, end="")
            for i, (k, v) in enumerate(d.items()):
                print("%s: %12.6f" % (k, v), end="")
                if i < len(d) - 1: print(", ", end="")
            print(" USD")
            total += d['V']
    print("%-{}s %.6f USD".format(16) % ("totalValue", total))
    return bals

r, j = request_account_info()
bals = get_holdings(j, prices)
