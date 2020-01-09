import smtplib, os, sys
from datetime import datetime, timedelta

# Read authentication information from auth.py:
# Variables EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_FROM, EMAIL_TO, EMAIL_SIGNAL, and EMAIL_AVSIG should be defined.
with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'auth.py')) as f: exec(f.read())

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import BasicFinance

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("type", help="can be either tsp or av")
parser.add_argument("-s", "--signal", help="send email only if signal", action="store_true")
args = parser.parse_args()

msg = MIMEMultipart()

if not (args.type == 'tsp' or args.type == 'av'):
	print("Must select one of the following: tsp, av.")
	sys.exit()

path = None
name = None
email = None

bf = BasicFinance.BasicFinance()

if args.type == 'tsp':
	path = 'tsp'
	name = 'TSP'
	email = '/tmp/TSPEmail.txt'
	send = len(bf.getFederalTradingDays(datetime.now(), datetime.now()).tolist()) > 0

if args.type == 'av':
	path = 'av'
	name = 'Alpha Vantage'
	email = '/tmp/AVEmail.txt'
	send = len(bf.getTradingDays(datetime.now(), datetime.now()).tolist()) > 0

if not send:
	print('Not a market day, not sending report!')
	sys.exit()

if args.signal:
	msg['Subject'] = name + ' Signal Detected on ' + datetime.now().strftime('%m/%d/%Y')
	if args.type == 'av':
		EMAIL_TO = EMAIL_AVSIG
	else:
		EMAIL_TO = EMAIL_SIGNAL
else:
	msg['Subject'] = name + ' Status for ' + datetime.now().strftime('%m/%d/%Y')

if not EMAIL_TO: sys.exit()

msg['From'] = EMAIL_FROM
msg['To'] = ', '.join(EMAIL_TO)

try:
	with open(email, 'r') as fh:
		text = MIMEText('<font face="Courier New, Courier, monospace">' + fh.read().replace(' ', '&nbsp;').replace('\n', '<br />') + '</font>', 'html')
except:
	text = MIMEText('<font face="Courier New, Courier, monospace">Attached are the most recent ' + name + ' charts with signals.</font>', 'html')

msg.attach(text)

imgpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images', path)

for imgfile in sorted(os.listdir(imgpath)):
	with open(os.path.join(imgpath, imgfile), 'rb') as fp:
		img = MIMEImage(fp.read())
	img.add_header('Content-Disposition', 'attachment', filename=imgfile)
	msg.attach(img)

s = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
s.starttls()
s.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
s.quit()
