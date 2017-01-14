import smtplib, os
from datetime import datetime

# Read authentication information from auth.py:
# Variables EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_FROM, EMAIL_TO should be defined.
with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'auth.py')) as f: exec(f.read())

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

msg = MIMEMultipart()
msg['Subject'] = 'TSP Charts ' + datetime.now().strftime('%m/%d/%Y')
msg['From'] = EMAIL_FROM
msg['To'] = EMAIL_TO

try:
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'TSPEmail.txt'), 'r') as fh:
        text = MIMEH('<font face="Courier New, Courier, monospace">' + fh.read() + '</font>', 'html')
except:
    text = MIMEText('<font face="Courier New, Courier, monospace">Attached are the most recent TSP charts with signals.</font>', 'html')

msg.attach(text)

imgpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')

for imgfile in sorted(os.listdir(imgpath)):
    with open(os.path.join(imgpath, imgfile), 'rb') as fp:
        img = MIMEImage(fp.read())
    img.add_header('Content-Disposition', 'attachment', filename=imgfile)
    msg.attach(img)

s = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
s.starttls()
s.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
s.sendmail(msg['From'], msg['To'], msg.as_string())
s.quit()
