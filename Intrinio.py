import intrinio_sdk
from datetime import datetime, timedelta

production = False

if production:
    from FinanceAuth import tokenIntrinioProd as token
    print("Using production API token ... ")
else:
    from FinanceAuth import tokenIntrinioSand as token
    print("Using sandbox API token ... ")

intrinio_sdk.ApiClient().configuration.api_key['api_key'] = token

security_api = intrinio_sdk.SecurityApi()

numdays = 30
datefmt = "%Y-%m-%d"
symbol = "AAPL"

dtt = datetime.today()
dts = dtt - timedelta(days=numdays)
dte = dtt

dss = dts.strftime(datefmt)
dse = dte.strftime(datefmt)

try:
    api_response = security_api.get_security_stock_prices(symbol, start_date=dss, end_date=dse, frequency="daily", page_size=numdays)
    print(api_response)
except intrinio_sdk.rest.ApiException as e:
    print("SDK Exception: %s" % e)
