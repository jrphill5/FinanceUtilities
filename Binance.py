import os, collections
import requests, json
import hmac, hashlib, time
from datetime import datetime

# Create file called binanceapi.py and define api_sec, api_key strings
from binanceapi import api_sec, api_key

debug = False

units = collections.OrderedDict()
units["USD"]  = (12, 4)
units["BUSD"] = (15, 5)
units["USDT"] = (15, 5)
units["USDC"] = (15, 5)
units["BTC"]  = (15, 8)

api_url = "https://api.binance.us/api/v3/"

def verify_response(r):
    if r.status_code != 200:
        exit("ERROR (CODE %d)!" % r.status_code)

def print_used_requests(r):
    time_interval_map = {'s': 'second', 'm': 'minute', 'h': 'hour', 'd': 'day'}
    print("used-weight:")
    for head in r.headers:
        if head.startswith("x-mbx-used-weight"):
            if head == "x-mbx-used-weight":
                print("  %-9s -> %6d" % ("total", int(r.headers[head])))
            else:
                time_period = head[len("x-mbx-used-weight")+1:]
                time_unit   = time_period[ -1]
                time_value  = time_period[:-1]
                print("  %-2d %-6s -> %6d" % (int(time_value), time_interval_map[time_unit], int(r.headers[head])))

def request_data_without_key(endpoint, params=None):
    r = requests.get(os.path.join(api_url, endpoint), params=params)
    verify_response(r)
    j = json.loads(r.text)
    if debug: print_used_requests(r)
    return r, j

def sign_query(payload):
    query = '&'.join(["{}={}".format(k, v) for (k, v) in payload])
    m = hmac.new(api_sec.encode('utf-8'), query.encode('utf-8'), hashlib.sha256)
    return m.hexdigest()

def request_data_with_key(endpoint, params={}):
    headers = {"x-mbx-apikey": api_key}
    params['timestamp'] = int(round(time.time()) * 1000)
    payload = []
    for k in sorted(params):
        payload.append((k, params[k]))
    params['signature'] = sign_query(payload)
    r = requests.get(os.path.join(api_url, endpoint), params=params, headers=headers)
    verify_response(r)
    j = json.loads(r.text)
    if debug: print_used_requests(r)
    return r, j

def request_ticker_prices():
    r, j = request_data_without_key("ticker/price")

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

def request_account_info():
    print()
    print("================================= ACCOUNT INFO ================================")
    print()
    r, j = request_data_with_key('account')
    for item in sorted(j):
        if item == 'updateTime':
            print("%-{}s %s".format(16) % (item, datetime.fromtimestamp(int(j['updateTime'])/1000.)))
        elif item != 'balances':
            print("%-{}s %s".format(16) % (item, j[item]))
    return r, j

def get_holdings(j, prices=None):
    print("balances")

    eps = 1e-9
    bals = {}
    for d in j['balances']:
        if float(d['free'])+float(d['locked']) > eps:
            bals[d['asset']] = {'F': float(d['free']), 'L': float(d['locked']), 'T': float(d['free'])+float(d['locked'])}
            if prices is not None:
                try:
                    bals[d['asset']]['V'] = bals[d['asset']]['T'] * prices[d['asset']]['USD']
                except KeyError:
                    bals[d['asset']]['V'] = bals[d['asset']]['T']
    total = 0
    for k, d in bals.items():
        print(" %-5s -> " % k, end="")
        for i, (k, v) in enumerate(d.items()):
            print("%s: %12.6f" % (k, v), end="")
            if i < len(d) - 1: print(", ", end="")
        print(" USD")
        total += d['V']
    print("%-{}s %.6f USD".format(16) % ("totalValue", total))
    return bals

if __name__ == "__main__":

    print()
    print("=============================== EXCHANGE INFO =================================")
    print()
    r, j = request_data_without_key("exchangeInfo")
    for k in j:
        if k == 'timezone':
            print("%s: %s" % (k, j['timezone']))
        elif k == 'serverTime':
            print("%s: %s" % (k, datetime.fromtimestamp(int(j['serverTime'])/1000.)))
        elif k == 'exchangeFilters':
            if not j['exchangeFilters']:
                print("%s: %s" % (k, None))
            else:
                print("%s: %s" % (k, j['exchangeFilters']))
        elif k == 'rateLimits':
            print("%s:" % k)
            for l in j[k]:
                print("%9d %-15s PER %2d %s" % (int(l['limit']), l['rateLimitType'], int(l['intervalNum']), l['interval']))
        elif k == 'symbols':
            print("%s:" % k)
            print("  %-10s %2s  %-6s %2s  %-5s %2s  %-7s" % ('Symbol', 'P', 'Base', 'P', 'Quote', 'P', 'Status'))
            for i, sym in enumerate(j[k]):
                print("  %-10s %2d  %-6s %2d  %-5s %2d  %-7s" % (sym['symbol'], sym['quoteAssetPrecision'], sym['baseAsset'], sym['baseAssetPrecision'], sym['quoteAsset'], sym['quotePrecision'], sym['status']))
        else:
            print(k)

    prices = request_ticker_prices()
    print_ticker_table(prices)

    r, j = request_account_info()
    bals = get_holdings(j, prices)

    print("24hr history")
    for bal in bals:
        if bal == 'USD': continue
        r, j = request_data_without_key("ticker/24hr", params={'symbol': '%sUSD' % bal})
        print(" %-5s -> O: %12.6f, M: %12.6f, C: %12.6f, D: %+7.2f/%+7.2f%%" % (bal, float(j['prevClosePrice']), float(j['weightedAvgPrice']), float(j['lastPrice']), float(j['priceChange']), float(j['priceChangePercent'])))
