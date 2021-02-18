import requests, json, sys, re, os
import numpy as np
from datetime import date, datetime, timedelta
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

# Turn on debug messages?
debug = True

# Define a pay date for biweekly plots
paydate = date(2020, 12, 24)

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
        sys.stdout.flush()
        with open(filename, "r") as fh:
            jsoninfo = json.load(fh)
            print("done!")
    else:
        sys.stdout.write("Saved JSON info for %s stale, requesting from server ... " % endpoint[-1])
        sys.stdout.flush()
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

def decrement_nmonth(dt, months):
    years, months = np.divmod(months, 12)
    year  = dt.year  - years
    month = dt.month - months
    if month <= 0:
        year  -= 1
        month += 12
    return date(year, month, dt.day)

def increment_nmonth(dt, months):
    years, months = np.divmod(months, 12)
    year  = dt.year  + years
    month = dt.month + months
    if month > 12:
        year  += 1
        month -= 12
    return date(year, month, dt.day)

def increment_biweekly(y, m, d):
    dt = date(y, m, d) + timedelta(days=14)
    return dt.year, dt.month, dt.day

# Counts backwards from current date by nmonths if alignday is None
# Otherwise starts at the next day of the month matching alignday
def compute_nmonth_deltas(Dnp, Bnp, months=1, alignday=None):
    DB = []; BB = []
    if alignday is None:
        curdate = date.today()
    else:
        curdate = date.today().replace(day=alignday)
        if curdate < date.today():
            curdate = increment_nmonth(curdate, 1)
    enddate = Dnp[ 0]
    while enddate <= curdate:
        if curdate > date.today():
            DB.append(date.today())
        else:
            DB.append(curdate)
        prvdate = decrement_nmonth(curdate, months)
        idx = np.where((Dnp > prvdate) & (Dnp <= curdate))
        if len(idx[0]) > 0:
            BB.append(Bnp[idx[0][-1]])
        elif len(BB) > 0:
            BB.append(BB[-1])
            if debug: print("[WARN] {:}monthly: Using previous value for {:} to {:}".format(months, curdate, prvdate))
        else:
            BB.append(0.)
            if debug: print("[WARN] {:}monthly: Using null value for {:} to {:}".format(months, curdate, prvdate))
        curdate = prvdate
    DB.append(Dnp[0])
    BB.append(Bnp[0])
    DBnp = np.flip(DB)
    BBnp = np.flip(BB)
    BBnp = BBnp[1:] - BBnp[:-1]
    BBnp = np.append(BBnp, BBnp[-1])
    return DBnp, BBnp

# Aligned to biweekly pay days
def compute_biweekly_deltas(Dnp, Bnp):
    DB = []; BB = []
    curdate = Dnp[0]
    # If not currently pay day of week, back up to previous pay day of week
    if curdate.weekday() != paydate.weekday():
        curdate -= timedelta(8 - (paydate.weekday()-today.weekday()) % 7)
    # If that day is not in a pay week, back up another week
    if ((curdate - paydate).days % 14) != 0:
        curdate -= timedelta(days=7)
    enddate = Dnp[-1]
    while curdate <= enddate:
        DB.append(curdate)
        nxtdate = date(*increment_biweekly(curdate.year, curdate.month, curdate.day))
        idx = np.where((Dnp >= curdate) & (Dnp < nxtdate))
        if len(idx[0]) > 0:
            BB.append(Bnp[idx[0][0]])
        elif len(BB) > 0:
            BB.append(BB[-1])
            if debug: print("[WARN] biweekly: Using previous value for {:} to {:}".format(curdate, nxtdate))
        else:
            BB.append(0.)
            if debug: print("[WARN] biweekly: Using null value for {:} to {:}".format(curdate, nxtdate))
        curdate = nxtdate
    DB.append(date.today())
    BB.append(Bnp[-1])
    DBnp = np.array(DB)
    BBnp = np.array(BB)
    BBnp = BBnp[1:] - BBnp[:-1]
    BBnp = np.append(BBnp, BBnp[-1])
    return DBnp, BBnp

def select_positive(BBnp):
    BBPnp = np.copy(BBnp)
    BBPnp[np.where(BBnp< 0)] = 0
    return BBPnp

def select_negative(BBnp):
    BBNnp = np.copy(BBnp)
    BBNnp[np.where(BBnp>=0)] = 0
    return BBNnp

# Iterate through all data sets
for title, D, B in [("Net Worth", DN, BN), ("Selective Sum", DS, BS)]:
    # Create numpy arrays
    Dnp = np.array(D)
    Bnp = np.array(B)

    # Plot daily values
    plt.figure("{:} Daily Values".format(title))
    plt.title("{:} Daily Values ({:+,.2f})".format(title, Bnp[-1]).replace("+", "+$").replace("-", "-$"))
    plt.xlabel("Date")
    plt.ylabel("Value ({:}$)".format(scale_yaxis(Bnp)))
    plt.fill_between(Dnp, select_negative(Bnp), 0, step="pre", color="tab:red",   alpha=0.4)
    plt.fill_between(Dnp, select_positive(Bnp), 0, step="pre", color="tab:green", alpha=0.4)
    #plt.xlim(Dnp[0], Dnp[-1])

    # Plot biweekly delta bars
    DBnp, BBnp = compute_biweekly_deltas(Dnp, Bnp)
    plt.figure("{:} Biweekly Deltas".format(title))
    plt.title("{:} Biweekly Deltas ({:+,.2f})".format(title, BBnp[-1]).replace("+", "+$").replace("-", "-$"))
    plt.xlabel("Date")
    plt.ylabel("Change in Value ({:}$)".format(scale_yaxis(BBnp)))
    plt.fill_between(DBnp, select_negative(BBnp), 0, step="post", color="tab:red",   alpha=0.4)
    plt.fill_between(DBnp, select_positive(BBnp), 0, step="post", color="tab:green", alpha=0.4)
    #plt.xlim(DBnp[0], DBnp[-1])

    # Plot nmonth delta bars
    for months, subtitle, alignday in [(1, "Monthly", 1), (3, "Quarterly", None), (12, "Yearly", None)]:
        DBnp, BBnp = compute_nmonth_deltas(Dnp, Bnp, months, alignday)
        plt.figure("{:} {:} Deltas".format(title, subtitle))
        plt.title("{:} {:} Deltas ({:+,.2f})".format(title, subtitle, BBnp[-1]).replace("+", "+$").replace("-", "-$"))
        plt.xlabel("Date")
        plt.ylabel("Change in Value ({:}$)".format(scale_yaxis(BBnp)))
        plt.fill_between(DBnp, select_negative(BBnp), 0, step="post", color="tab:red",   alpha=0.4)
        plt.fill_between(DBnp, select_positive(BBnp), 0, step="post", color="tab:green", alpha=0.4)
        #plt.xlim(DBnp[0], DBnp[-1])

# Show all plots
plt.show()
