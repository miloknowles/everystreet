from datetime import date
from pprint import pprint

from strava_api import *


# Re-run whenever new runs need to be added to database.
if __name__ == '__main__':
  token = get_token_always_valid()
  download_polylines(token)
