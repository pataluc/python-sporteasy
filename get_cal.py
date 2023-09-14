#!/usr/bin/python3
import os
import requests
import jq
from datetime import datetime, timedelta
from icalendar import Calendar, Event
from http.cookiejar import LWPCookieJar
from dotenv import load_dotenv

# Loading config from .env file
load_dotenv(override=True)
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TEAM_ID = os.getenv('TEAM_ID')
EVENT_PREFIX = os.getenv('EVENT_PREFIX')
PRACTICE_BEFORE_MARGIN = int(os.getenv('PRACTICE_BEFORE_MARGIN'))
MATCH_MARGIN = int(os.getenv('MATCH_MARGIN'))

BASE_PATH = os.path.dirname(__file__)

# Initialisation session
jar = LWPCookieJar(filename = os.path.join(BASE_PATH, 'cookies.txt'))
session = requests.Session()
session.cookies = jar

# Checking if cookie still works
try:
    jar.load()
    session.get('https://api.sporteasy.net/v2.1/me').raise_for_status()
except:
    print("Cookie jar empty or outdated, Authenticating...")

    # Authentication
    auth_request = session.post('https://api.sporteasy.net/v2.1/account/authenticate/', json={"username": USERNAME, "password": PASSWORD})

teams = session.get('https://api.sporteasy.net/v2.1/me/teams').json()

team = jq.compile(".results[] | select(.slug_name==\"%s\")" % TEAM_ID).input_value(teams).first()

cal = Calendar()
cal.add('prodid', "-// saison %s" % team['current_season']['name'])
cal.add('X-WR-CALNAME', team['full_name'])
cal.add('X-WR-CALDESC', team['full_name'])

headers = {
    'x-impersonated-id': str(team['me']['profile']['id']),
    'Accept-Language': 'fr'
}
events = session.get("%s?season_id=%s&web=1" % (team['url_events'], team['current_season']['id']), headers=headers).json()
reading_date = datetime.now().strftime("%Y/%d/%m, %H:%M:%S")

for event in events['results']:
    cal_event = Event()
    cal_event.add('summary', "%s - %s" % (EVENT_PREFIX or team['full_name'], event['name']))
    cal_event.add('description', "%s\nhttps://%s.sporteasy.net/event/%s\nDate de lecture de SportEasy : %s" % (
        event['category']['localized_name'], TEAM_ID, event['id'], reading_date))
    if event['category']['type'] == 'training':
        start_delta = timedelta(minutes=PRACTICE_BEFORE_MARGIN)
        end_delta = timedelta(minutes=0)
    elif event['category']['type'] == 'championship_match':
        start_delta = timedelta(minutes=MATCH_MARGIN)
        end_delta = timedelta(minutes=MATCH_MARGIN)
    else:
        start_delta = timedelta(minutes=0)
        end_delta = timedelta(minutes=0)

    cal_event.add('dtstart', datetime.strptime(event['start_at'], '%Y-%m-%dT%H:%M:%S%z') - start_delta)
    if event['end_at']:
        cal_event.add('dtend', datetime.strptime(event['end_at'], '%Y-%m-%dT%H:%M:%S%z') + end_delta)
    cal.add_component(cal_event)

f = open(os.path.join(BASE_PATH, "output/%s.ics" % TEAM_ID), 'wb')
f.write(cal.to_ical())
f.close()

jar.save()
