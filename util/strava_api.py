import os
import requests
import urllib3
import csv
from dotenv import load_dotenv
from pprint import pprint

load_dotenv() # Take environment variables from .env.

# Not sure if this is needed; copied from tutorial.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_token_always_valid():
  """
  Get a token that is up-to-date.
  """
  auth_url = "https://www.strava.com/oauth/token"

  payload = {
    'client_id': os.getenv('STRAVA_CLIENT_ID'),
    'client_secret': os.getenv('STRAVA_CLIENT_SECRET'),
    'refresh_token': os.getenv('STRAVA_REFRESH_TOKEN'),
    'grant_type': 'refresh_token',
    'f': 'json'
  }

  res = requests.post(auth_url, data=payload, verify=False)

  print(res)

  access_token = res.json()['access_token']

  return access_token


def get_activity_by_id(access_token, id):
  """
  Requests info about an activity based on its unique ID.

  https://developers.strava.com/docs/reference/#api-Activities-getActivityById
  """
  activites_url = "https://www.strava.com/api/v3/activities/{}".format(id)
  header = {'Authorization': 'Bearer ' + access_token}
  param = {'per_page': 200, 'page': 1}
  response = requests.get(activites_url, headers=header, params=param).json()

  return response


def get_athlete_activities(access_token, before_time=None, after_time=None, page=1, per_page=30):
  """
  Returns a paginated list of the authenticated athlete's activities.

  https://developers.strava.com/docs/reference/#api-Activities-getLoggedInAthleteActivities
  """
  activites_url = "https://www.strava.com/api/v3/athlete/activities/"
  header = {'Authorization': 'Bearer ' + access_token}
  param = {'before': before_time, 'after': after_time, 'per_page': per_page, 'page': page}
  response = requests.get(activites_url, headers=header, params=param).json()

  return response


def get_all_activity_ids(access_token, before_time=None, after_time=None, verbose=True):
  """
  Returns the IDs of all activities within the query times.
  """
  page_index = 1

  id_list = []
  current_page = []

  while (len(current_page) > 0 or page_index == 1):
    if verbose:
      print('Fetching page {} of activities'.format(page_index))
    current_page = get_athlete_activities(access_token,
                                          before_time=before_time,
                                          after_time=after_time,
                                          page=page_index,
                                          per_page=30)
    page_index += 1

    for activity in current_page:
      id_list.append(activity['id'])

  return id_list


def download_polylines_csv(access_token, before_time=None, after_time=None, verbose=True):
  """
  See: https://www.markhneedham.com/blog/2017/04/29/leaflet-strava-polylines-osm/
  """
  id_list = get_all_activity_ids(access_token, before_time=before_time, after_time=after_time)

  with open("output/polylines/data.csv", "w") as runs_file:
    writer = csv.writer(runs_file, delimiter=",")
    writer.writerow(["id", "polyline"])

    for i, id in enumerate(id_list):
      if verbose and i % 10 == 0:
        print('Processing activity {}/{}'.format(i + 1, len(id_list)))
      r = get_activity_by_id(access_token, id)
      polyline = r["map"]["polyline"]
      writer.writerow([id, polyline])

  print('Finished downloading activity polylines')