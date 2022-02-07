import logging
import math
import json

from python.timestamps import epoch_timestamp_now
import python.firebase_api as db
import python.strava_api as strava


logger = logging.getLogger()
logger.setLevel(logging.INFO)

STRAVA_TOKEN = strava.get_token_always_valid()

# Define a list of Python lambda functions that are called by this AWS Lambda function.
ACTIONS = {
  'square': lambda x: x * x,
  'square root': lambda x: math.sqrt(x),
  'increment': lambda x: x + 1,
  'decrement': lambda x: x - 1,
}


def lambda_handler(event, context):
  """
  Checks for new activities from Strava.

  If 'timeframe' arg is set to 'all', the fetch is exhaustive. Otherwise, we just
  scan for activities that occurred in the last week.
  """
  try:
    # If unspecified, just do a fast pull.
    timeframe = event['timeframe']
    user_id = event['user_id']

    logger.info('timeframe = {}'.format(timeframe))

    # Optionally limit query to a certain timeframe.
    if timeframe == 'all':
      after_time_epoch = None
    elif timeframe == 'day_only':
      after_time_epoch = epoch_timestamp_now() - 86400 # Sec per day.
    elif timeframe == 'week_only':
      after_time_epoch = epoch_timestamp_now() - 604800 # Sec per week.
    elif timeframe == 'month_only':
      after_time_epoch = epoch_timestamp_now() - 2592000 # Sec per month.
    else:
      after_time_epoch = epoch_timestamp_now() - 604800 # Sec per week.

    existing_ids = db.get_activity_ids(user_id)

    # TODO: store key in database.
    maybe_new_ids = strava.get_activities_id_set(STRAVA_TOKEN, after_time=after_time_epoch)

    if timeframe is None or timeframe == 'all':
      new_ids = maybe_new_ids
    else:
      new_ids = maybe_new_ids - existing_ids

    new_count = len(new_ids)

    for i, activity_id in enumerate(new_ids):
      logger.debug('processing #{}/{} (id={})'.format(i+1, len(new_ids), activity_id))

      # Get activity data from Strava and add (the relevant part) to our database.
      activity_data = strava.get_activity_by_id(STRAVA_TOKEN, activity_id)
      db.add_or_update_activity(user_id, activity_id, activity_data)

    response = {
      'statusCode': 200,
      'headers': {
        'Content-Type': 'application/json',
      },
      'body': json.stringify({'total_count': len(maybe_new_ids), 'new_count': new_count})
    }

    return response

  except Exception as e:
    logger.exception(e)

    response = {
      'statusCode': 300,
      'headers': {
        'Content-Type': 'application/json',
      },
      'body': json.stringify({'error': str(e)})
    }

    return response
