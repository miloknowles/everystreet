from calendar import timegm
from datetime import date, datetime


def epoch_timestamp(year, month, day):
  """
  Strava expects epoch timestamps, which are seconds since Jan 1, 1970.
  """
  return timegm(date(year, month, day).timetuple())


def epoch_timestamp_now():
  """
  Gets server time in seconds since epoch.
  """
  return timegm(datetime.utcnow().timetuple())
