import requests
from datetime import date
from pprint import pprint

from strava_api import *


if __name__ == '__main__':
  token = get_token_always_valid()

  # Try getting a single activity by ID.
  # r = get_activity_by_id(token, '6596522872')
  # pprint(r)

  # Try getting a list of activities from an athlete.
  after_time = epoch_timestamp(2022, 1, 24)
  before_time = epoch_timestamp(2022, 1, 26)
  r = get_athlete_activities(token, before_time=before_time, after_time=after_time, page=1, per_page=30)
  pprint(r)
