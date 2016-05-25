import re
from time import sleep

import requests
from requests.auth import HTTPBasicAuth

from flask import Flask
from flask import render_template
from flask import url_for
from flask import request

from twilio import twiml
from twilio.rest import TwilioRestClient

from firebase import firebase

firebase = firebase.FirebaseApplication('https://yourfirebaseurl.firebaseio.com/', None)

# Declare and configure application
app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('local_settings.py')

# Render Template
@app.route('/')
def index():
    return render_template('index.html')

# Incoming Agent Conference TwiML
@app.route('/voice', methods=['GET', 'POST'])
def voice():
    firebase.put("/", request.form['CallSid'], data={'To': request.form['To'], 'From': request.form['From'], 'StatusCallbackEvent': 'call-created'})
    response = twiml.Response()
    dial = response.dial()
    dial.conference("SignalWarmTransfer",
            statusCallbackEvent="start end join leave mute hold", statusCallback="/callback",)
    return str(response)

# Update Agent with Conference Events Callback
@app.route('/callback', methods=['GET', 'POST'])
def callback():
    agent = str(request.form['CallSid'])
    event = request.form['StatusCallbackEvent']
    firebase.patch("/"+str(agent), data={'ConferenceSid': request.form['ConferenceSid'], 'StatusCallbackEvent': request.form['StatusCallbackEvent']})
    return '200'

# Delete Agent on Status Callback
@app.route('/callend', methods=['GET', 'POST'])
def callend():
    sleep(1.5)
    firebase.delete("/", request.form['CallSid'])
    return '200'

# Hold/Unhold Call SID
@app.route('/hold', methods=['GET', 'POST'])
def hold():
    account_sid = app.config["TWILIO_ACCOUNT_SID"]
    auth_token = app.config["TWILIO_AUTH_TOKEN"]
    call_sid = str(request.form['call_sid'])
    agent = firebase.get("/"+str(call_sid), None)
    url = 'https://api.twilio.com/2010-04-01/Accounts/{}/Conferences/{}/Participants/{}.json'.format(account_sid, agent['ConferenceSid'], call_sid)
    if agent['StatusCallbackEvent'] == "participant-hold":
        params = {'Hold':'false'}
    else:
        params = {'Hold':'true', 'HoldUrl':'https://signal-events-16.herokuapp.com/holdurl'}
    hold_request = requests.post(url, data = params , auth=HTTPBasicAuth(account_sid, auth_token))
    print str(hold_request.status_code) + hold_request.text
    return str(hold_request.status_code)

# WaitUrl Call SID
@app.route('/holdurl', methods=['GET', 'POST'])
def holdurl():
    response = twiml.Response()
    response.play("https://s3.amazonaws.com/twiliotest1/Calypso.mp3", loop="3")
    return str(response)

if __name__ == '__main__':
    app.run(port=8080, debug=True, processes=4)