import os, sys
from iexfinance.stocks import Stock
from pprint import pprint

production = False

if len(sys.argv) == 1: symbol = "AAPL"
else:                  symbol = sys.argv[1]

if production:
    from FinanceAuth import tokenIEXCloudProd as token
    os.environ['IEX_API_VERSION'] = "iexcloud-v1"
    print("Using production API token ... ")
else:
    from FinanceAuth import tokenIEXCloudSand as token
    os.environ['IEX_API_VERSION'] = "iexcloud-sandbox"
    print("Using sandbox API token ... ")

os.environ['IEX_OUTPUT_FORMAT'] = "json"
os.environ['IEX_TOKEN'] = token

a = Stock(symbol)
pprint(a.get_book())
