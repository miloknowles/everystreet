import requests
import urllib3
from calendar import timegm
from datetime import date

# Not sure if this is needed; copied from tutorial.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def epoch_timestamp(year, month, day):
  """
  Strava expects "epoch" timestamps, which are seconds since Jan 1, 1970.
  """
  return timegm(date(year, month, day).timetuple())


def get_token_always_valid():
  """
  Get a token that is up-to-date.
  """
  auth_url = "https://www.strava.com/oauth/token"

  # Access token: 8cea078f35c16461758c1131830baa82106c53df
  # NOTE: The refresh_token must come from a special read all request.
    # 'refresh_token': '28abf4fb89dee2efc9cbd2441ab28471c576bb70',
  payload = {
    'client_id': '77280',
    'client_secret': '2c396c1e3d793afc2537bbb1cba8a4e1da1015ae',
    'refresh_token': 'a926138a52a0f9bea2156c46410204bef8ee4377',
    'grant_type': 'refresh_token',
    'f': 'json'
  }

  res = requests.post(auth_url, data=payload, verify=False)
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
