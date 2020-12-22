import requests, json, sys, re, os
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.ticker

# Include to avoid FutureWarning
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

# Import convenience functions from Schwab.py
from Schwab import add_series, remove_duplicates

# Create a file called auth.py containing a definition for the token
try: from FinanceAuth import tokenYNAB as token
except ImportError: token = None

# Define account indices to omit from computation
omitidx = []

# Define cache directory for JSON files
cachedir = "cache"

# Define timeouts for file freshness in minutes
# Keep in mind limit of 200 API calls per hour
# Each run of the script could potentially call three times
# Check budget, accounts, and transactions slower than once every 0.9 minutes
# Check budget hourly or slower and accounts and transactions slower than once every 0.603 minutes
budgtout = 60
accttout =  5
trantout =  5

# Compute number of API calls per hour and warn user if rate too fast
apicalls = 0.
if budgtout >= 60: apicalls += 1.
else:              apicalls += 60./budgtout
if accttout >= 60: apicalls += 1.
else:              apicalls += 60./accttout
if trantout >= 60: apicalls += 1.
else:              apicalls += 60./trantout
if apicalls > 200: print("[WARN] Rate of %.0f API calls per hour will be limited!" % apicalls)

# Check for API token
if token is None:
    print("Please request a Personal Access Token from YNAB and define in auth.py as follows:")
    print('    token = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"')
    exit(1)

# Private method for converting JSON values to dollars
def _convert_currency(j):
    for item in j:
        for key in ['balance', 'cleared_balance', 'uncleared_balance', 'amount']:
            if key in item.keys(): item[key] /= 1000.
    return j

# Convenience function to prettyprint JSON string
def print_json(j):
    print(json.dumps(j, indent=4))

# Request JSON information from YNAB RESTful API
# Parameter 'endpoint' is array split on '/' character
# Parameter 'token' is the API token loaded in earlier
def ynab_request(endpoint, token):
    h = {'Authorization' : "Bearer %s" % token}
    r = requests.get("https://api.youneedabudget.com/v1/%s" % '/'.join(endpoint), headers=h)
    use, tot = [int(x) for x in r.headers['X-Rate-Limit'].split('/')]
    if (tot - use)/tot < 0.5:
        print("[WARN] Over 50% of hourly requests used! (%d left)" % (tot - use))
    elif (tot - use)/tot < 0.25:
        print("[WARN] Over 75% of hourly requests used! (%d left)" % (tot - use))
    j = json.loads(r.text)
    if 'error' in j:
        print("[ERROR] Code %s: %s" % (j['error']['id'], j['error']['detail']))
        return None
    else:
        return _convert_currency(j['data'][endpoint[-1]])

# Attempt to load JSON information from file if fresh enough
# Parameter 'endpoint' is array split on '/' character
# Parameter 'token' is the API token loaded in earlier
# Parameter 'timeout' is number of minutes data considered fresh
def load_cache(endpoint, token, timeout):
    if not os.path.exists(cachedir): os.mkdir(cachedir)
    filename = os.path.join(cachedir, "ynab-%s.json" % '-'.join(endpoint))
    jsoninfo = None
    if os.path.exists(filename) and os.path.isfile(filename) and (timeout is None or datetime.now() - timedelta(minutes=timeout) < datetime.fromtimestamp(os.path.getmtime(filename))):
        sys.stdout.write("Saved JSON info for %s fresh, reading from file ... " % endpoint[-1])
        with open(filename, "r") as fh:
            jsoninfo = json.load(fh)
            print("done!")
    else:
        sys.stdout.write("Saved JSON info for %s stale, requesting from server ... " % endpoint[-1])
        jsoninfo = ynab_request(endpoint, token)
        with open(filename, "w+") as fh:
            json.dump(jsoninfo, fh)
            print("done!")
    return jsoninfo

def reformat_ticks_K(val, pos):
    return reformat_ticks(val, pos, 'K')

def reformat_ticks_M(val, pos):
    return reformat_ticks(val, pos, 'M')

def reformat_ticks_B(val, pos):
    return reformat_ticks(val, pos, 'B')

def reformat_ticks(val, pos, divisor=''):
    format_dict = {'K': 1e3, 'M': 1e6, 'B': 1e9}
    if divisor in format_dict.keys():
        return '{:}'.format(round(val/format_dict[divisor], 1))
    else:
        return '{:}'.format(round(val, 1))

def scale_yaxis(l):
    max_val = max(abs(max(l)), abs(min(l)))
    if max_val >= 1e9:
        div = 'B'
        plt.gca().yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(reformat_ticks_B));
    elif max_val >= 1e6:
        div = 'M'
        plt.gca().yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(reformat_ticks_M));
    elif max_val >= 1e3:
        div = 'K'
        plt.gca().yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(reformat_ticks_K));
    else:
        div = ''
    return div

# Cache budget JSON information
budgjson = load_cache(['budgets'], token, budgtout)
if budgjson is None: exit(2)
if len(budgjson) != 1:
    print("[WARN] More than one budget detected!")
budgetid = budgjson[0]['id']

# Cache account JSON information
acctjson = load_cache(['budgets', budgetid, 'accounts'], token, accttout)
if acctjson is None: exit(3)

# Cache transaction JSON information
tranjson = load_cache(['budgets', budgetid, 'transactions'], token, trantout)
if tranjson is None: exit(4)

# Iterate through all transactions and store in dictionary
data = {}
for transaction in tranjson:
    # Query account name and transaction date and amount
    acctname = transaction['account_name']
    trandate = datetime.strptime(transaction['date'], "%Y-%m-%d").date()
    tranamnt = transaction['amount']

    # Add all transactions to one array and track the sum on a daily basis
    if acctname not in data: data[acctname] = {'trans': {}}
    if trandate not in data[acctname]['trans']: data[acctname]['trans'][trandate] = {'amounts': [], 'change': 0.}
    data[acctname]['trans'][trandate]['amounts'].append(tranamnt)
    data[acctname]['trans'][trandate]['change'] = round(tranamnt + data[acctname]['trans'][trandate]['change'], 2)

# Iterate through all accounts and store high level data in dictionary
for account in acctjson:
    acctname = account['name']

    # All of the account keys should have been handled earlier, so this should never run
    if acctname not in data:
        print("[WARN] Account '%s' should have already been defined!" % acctname)
        data[acctname] = {}

    # Store account level information not found in transactions JSON data above
    data[acctname]['id']   = account['id']
    data[acctname]['type'] = ' '.join([w.capitalize() for w in re.findall('[a-zA-Z][^A-Z]*', account['type'])])
    data[acctname]['wbal'] = account['balance']
    data[acctname]['cbal'] = account['cleared_balance']
    data[acctname]['ubal'] = account['uncleared_balance']
    data[acctname]['open'] = not account['closed']
    data[acctname]['on']   = account['on_budget']

# Iterate through all stored data to create plots
plots = {}
for idx, acctname in enumerate(sorted(data)):
    if acctname not in plots: plots[acctname] = {}

    # Print information about account
    sys.stdout.write("%2d  %-25s %-15s %+11.2f %+11.2f %+10.2f" % (idx, acctname, data[acctname]['type'], data[acctname]['wbal'], data[acctname]['cbal'], data[acctname]['ubal']))

    # Notate if account has been closed
    if data[acctname]['open']: sys.stdout.write("   ")
    else:                      sys.stdout.write("  C")

    # Notate if account is not included in budget
    if data[acctname]['on']:   sys.stdout.write("  *")
    else:                      sys.stdout.write("   ")

    # Sum all accounts that are included in budget unless explicitly omitted by user by omitidx
    # Additionally include accounts with a zero closing balance, but ignore untracked assets such as retirement accounts
    if idx not in omitidx and (data[acctname]['on'] or (not data[acctname]['on'] and data[acctname]['type'] != 'Other Asset') or data[acctname]['wbal'] == 0.):
        sys.stdout.write("  ~")
        plots[acctname]['enabled'] = True
    else:
        sys.stdout.write("   ")
        plots[acctname]['enabled'] = False

    print()

    # Begin with the working balance returned by the server and work in reverse chronological order
    rbal = data[acctname]['wbal']
    D = sorted(data[acctname]['trans'])
    B = []
    # Subtract off the daily change moving backwards in time to create a running balance
    for d in reversed(D):
        B.append(rbal)
        data[acctname]['trans'][d]['change']  = round(data[acctname]['trans'][d]['change'], 2)
        data[acctname]['trans'][d]['rbal'] = rbal
        rbal = round(rbal - data[acctname]['trans'][d]['change'], 2)
    B.reverse()

    # Add the current value once more for the current day so step plot is correct
    today = datetime.now().date()
    if today not in D:
        D.append(today)
        B.append(data[acctname]['wbal'])

    # Save the sorted unique data in the dictionary of plots
    plots[acctname]['date']    = D
    plots[acctname]['balance'] = B

# Create placeholder date/balance pairs for sums and iterate through all plots
DS = None; BS = None # Selective
DN = None; BN = None # Net worth
for name, plot in plots.items():
    D = plot['date']
    B = plot['balance']

    # If plot is enabled, include in selective sum
    if plot['enabled']:
        if DS is None and BS is None:
            DS, BS = D, B
        else:
            DS, BS = add_series(DS, BS, D, B)

    # Include all plots in net worth calculation
    if DN is None and BN is None:
        DN, BN = D, B
    else:
        DN, BN = add_series(DN, BN, D, B)

    # Create plot for each account
    #plt.figure(name)
    #plt.title("{:} ({:+,.2f})".format(name, B[-1]).replace("+", "+$").replace("-", "-$"))
    #plt.xlabel("Date")
    #plt.ylabel("Value ({:}$)".format(scale_yaxis(B)))
    #plt.step(D, B, where="post")

# Plot net worth
plt.figure("Net Worth")
plt.title("Net Worth ({:+,.2f})".format(BN[-1]).replace("+", "+$").replace("-", "-$"))
plt.xlabel("Date")
plt.ylabel("Value ({:}$)".format(scale_yaxis(BN)))
plt.step(DN, BN, where="post")

# Plot selective sum
plt.figure("Selective Sum")
plt.title("Selective Sum ({:+,.2f})".format(BS[-1]).replace("+", "+$").replace("-", "-$"))
plt.xlabel("Date")
plt.ylabel("Value ({:}$)".format(scale_yaxis(BS)))
plt.step(DS, BS, where="post")

# Show all plots
plt.show()
