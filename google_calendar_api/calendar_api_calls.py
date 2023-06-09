from __future__ import print_function

import datetime
import os.path
import json
import pickle
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CACHE_DURATION = 360


class Event:
    def __init__(self, summary, location, description, start, end, attendees=None, timeZone=None):
        self.summary = summary
        self.location = location
        self.description = description
        self.start = start
        self.end = end
        self.attendees = attendees if attendees is not None else []
        self.timeZone = timeZone

    def to_dict(self):
        event_dict = {
            'summary': self.summary,
            'location': self.location,
            'description': self.description,
            'start': {
                'dateTime': self.start,
                'timeZone': self.timeZone,
            },
            'end': {
                'dateTime': self.end,
                'timeZone': self.timeZone,
            },
            'attendees': [{'email': attendee} for attendee in self.attendees],
        }
        return event_dict

def get_credentials():
    """Gets valid user credentials from storage.
    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.
    Returns:
        Credentials, the obtained credential.
    """

    scopes = ['https://www.googleapis.com/auth/calendar.readonly']
    creds = None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('../token.json'):
        creds = Credentials.from_authorized_user_file('../token.json', scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '../credentials.json', scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('../token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def get_today_events():
    """
    Gets all of today's events from the user's primary calendar.

    :return: A list of tuples containing the start time, end time, and summary of each event (the event's name)
    """

    creds = get_credentials()
    event_list = []

    cache_file = "events_cache.pkl"
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            cache_data = pickle.load(f)
            if time.time() - cache_data["timestamp"] < CACHE_DURATION:
                print("Using cached data.")
                return json.dumps(cache_data["event_list"])

    try:
        service = build('calendar', 'v3', credentials=creds)

        calendar = service.calendars().get(calendarId='primary').execute()
        time_zone = calendar.get('timeZone')

        # Use the time zone to get today's events
        today = datetime.datetime.now(datetime.timezone.utc).astimezone()
        start = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        tomorrow = today + datetime.timedelta(days=1)
        end = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        print('Getting today\'s events')
        events_results = service.events().list(calendarId='primary', timeMin=start, timeMax=end, singleEvents=True, orderBy='startTime', timeZone=time_zone).execute()

        events = events_results.get('items', [])

        if not events:
            print('No upcoming events found.')
            return

        # Prints the start and name of the next 10 events

        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            start_time_obj = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S%z')
            local_time = start_time_obj.astimezone()
            start_time = local_time.strftime('%I:%M %p')

            end = event['end'].get('dateTime', event['end'].get('date'))
            end_time_obj = datetime.datetime.strptime(end, '%Y-%m-%dT%H:%M:%S%z')
            local_time = end_time_obj.astimezone()
            end_time = local_time.strftime('%I:%M %p')

            event_list.append((start_time, end_time, event['summary']))

        print(event_list)

        cache_data = {
            "timestamp": time.time(),
            "event_list": event_list
        }

        with open(cache_file, "wb") as f:
            pickle.dump(cache_data, f)

    except HttpError as error:
        print('An error occurred: %s' % error)

    return json.dumps(event_list)


def add_event(new_event):
    """
    Adds an event to the user's primary calendar.

    :param new_event: An instance of the Event class
    """

    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds)
    event = new_event.to_dict()
    event = service.events().insert(calendarId='primary', body=event).execute()
    print('Event created: %s' % (event.get('htmlLink')))


if __name__ == '__main__':
    get_today_events()
    sample_event = Event(
        summary='Google I/O 2015',
        location='800 Howard St., San Francisco, CA 94103',
        description="A chance to hear more about Google's developer products.",
        start='2023-05-28T09:00:00-07:00',
        end='2023-05-28T17:00:00-07:00',
        attendees=['lpage@example.com', 'sbrin@example.com'],
        timeZone='America/Los_Angeles',
    )
    add_event(sample_event)