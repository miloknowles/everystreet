from curses import window
import logging
import json
from pprint import pprint
from flask import Flask, render_template, jsonify, request
from numpy import full

import util.database as db
import util.strava_api as strava
from util.timestamps import epoch_timestamp_now

app = Flask(__name__)
logger = app.logger
DATA_PATH = './static/data.csv'

#===============================================================================

@app.route('/')
def render_map():
  items = []

  try:
    d = db.get_activities()
    polylines = [item['map']['polyline'] for item in d.values()]
    logger.debug('Got {} polylines'.format(len(polylines)))

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

  return render_template("map.html", polylines=json.dumps(polylines))

#===============================================================================

@app.route('/activities')
def render_activities():
  items = []

  try:
    d = db.get_activities()

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

  return render_template("activities.html", items=d.values())

#===============================================================================

@app.route('/stats')
def render_stats():
  return render_template('stats.html', **db.get_stats())

#===============================================================================

@app.route('/action/pull-activities')
def update_activities():
  """
  Checks for new activities from Strava.

  NOTE: If full_history flag is set, the fetch is exhaustive. Otherwise, we just
  scan for activities that occurred in the last week.
  """
  try:
    # If unspecified, just do a fast pull.
    sliding_window = request.args.get('sliding_window', None, type=str)

    token = strava.get_token_always_valid()
    logger.info('Sliding window: {}'.format(sliding_window))

    # Optionally limit query to a certain timeframe.
    if sliding_window is None:
      window_time = None
    elif sliding_window == 'day':
      window_time = epoch_timestamp_now() - 86400 # Sec per day.
    elif sliding_window == 'week':
      window_time = epoch_timestamp_now() - 604800 # Sec per week.
    elif sliding_window == 'month':
      window_time = epoch_timestamp_now() - 2592000 # Sec per month.
    else:
      window_time = epoch_timestamp_now() - 604800 # Sec per week.

    existing_ids = db.get_activities_id_set()
    maybe_new_ids = strava.get_activities_id_set(token, after_time=window_time)
    new_ids = maybe_new_ids - existing_ids

    current_count = len(existing_ids)
    new_count = len(new_ids)

    for i, id in enumerate(new_ids):
      logger.debug('Processing #{}/{} | '.format(i+1, len(new_ids), id))

      # Get activity data from Strava.
      r = strava.get_activity_by_id(token, id)

      # Add it to our database.
      db.add_or_update_activity(id, r)

    return jsonify({'total_count': current_count + new_count, 'new_count': new_count}), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

@app.route('/action/get-activities')
def get_activities():
  """
  Gets activities from the database.
  """
  try:
    r = db.get_activities()
    return jsonify(r), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

@app.route('/action/compute-stats')
def compute_stats():
  """
  Recompute stats over the database.
  """
  try:
    r = db.update_stats()
    return jsonify(r), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

@app.route('/action/activity/<id>')
def activity_json(id):
  """
  Get the json for an activity (debugging).
  """
  try:
    token = strava.get_token_always_valid()
    r = strava.get_activity_by_id(token, id)
    return jsonify(r), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

if __name__ == "__main__":
  app.logger.setLevel(logging.DEBUG)
  app.run(port=5001, debug=True)
