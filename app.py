import chunk
from lib2to3.pgen2.token import STAR
import requests
import logging
import json
import polyline
from flask import Flask, render_template, jsonify, request

import util.database as db
import util.strava_api as strava
from util.timestamps import epoch_timestamp_now

app = Flask(__name__)
logger = app.logger
DATA_PATH = './static/data.csv'
STRAVA_TOKEN = strava.get_token_always_valid()

#===============================================================================

@app.route('/')
def render_map():
  try:
    d = db.get_activities()
    polylines = [item['map']['polyline'] for item in d.values()]
    logger.debug('Got {} polylines'.format(len(polylines)))

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

  return render_template("map.html", polylines=json.dumps(polylines))

#===============================================================================

@app.route('/map')
def render_mapbox():
  items = []

  try:
    d = db.get_activities()
    polylines = [item['map']['polyline'] for item in d.values()]
    logger.debug('Got {} polylines'.format(len(polylines)))

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

  return render_template("mapbox.html", polylines=json.dumps(polylines))

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
    scope_arg = request.args.get('scope', 'week_only', type=str)

    # token = strava.get_token_always_valid()
    logger.info('Sliding window: {}'.format(scope_arg))

    # Optionally limit query to a certain timeframe.
    if scope_arg == 'all':
      window_time = None
    elif scope_arg == 'day_only':
      window_time = epoch_timestamp_now() - 86400 # Sec per day.
    elif scope_arg == 'week_only':
      window_time = epoch_timestamp_now() - 604800 # Sec per week.
    elif scope_arg == 'month_only':
      window_time = epoch_timestamp_now() - 2592000 # Sec per month.
    else:
      window_time = epoch_timestamp_now() - 604800 # Sec per week.

    existing_ids = db.get_activities_id_set()
    maybe_new_ids = strava.get_activities_id_set(STRAVA_TOKEN, after_time=window_time)

    if scope_arg is None or scope_arg == 'all':
      new_ids = maybe_new_ids
    else:
      new_ids = maybe_new_ids - existing_ids

    new_count = len(new_ids)

    for i, id in enumerate(new_ids):
      logger.debug('Processing #{}/{} | '.format(i+1, len(new_ids), id))

      # Get activity data from Strava.
      r = strava.get_activity_by_id(STRAVA_TOKEN, id)

      # Add it to our database.
      db.add_or_update_activity(id, r)

      coords = [[c[1], c[0]] for c in polyline.decode(r['map']['polyline'])]
      db.add_or_update_activity_features(id, {'coordinates': coords, 'type': 'LineString'})

    return jsonify({'total_count': len(maybe_new_ids), 'new_count': new_count}), 200

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

@app.route('/action/match-activities')
def match_activities():
  """
  Use the MapBox API to match raw GPS data to streets.
  """
  try:
    # If unspecified, just process new activities (fast option).
    scope_arg = request.args.get('scope', 'new_only', type=str)
    assert(scope_arg in ['all', 'new_only'])

    activity_ids = db.get_activities_id_set()
    matched_ids = db.get_matched_id_set()

    radius_meters = str(25.0)   # Search radius around each GPS point.
    chunk_size = 80             # Max 100 points in query.

    # Figure out which activities need to be processed.
    if scope_arg == 'new_only':
      unmatched_ids = activity_ids - matched_ids
    else:
      unmatched_ids = activity_ids

    logger.info('Matching {} new activity ids (scope is {})'.format(len(unmatched_ids), scope_arg))
    logger.debug('radius_meters={}'.format(radius_meters))
    logger.debug('chunk_size={}'.format(chunk_size))

    for id in unmatched_ids:
      logger.debug('Matching id={}'.format(id))

      # Need to send coordinates in Mapbox's format: lng,lat;lng,lat.
      encoded = db.get_activity_by_id(id)['map']['polyline']
      coordinate_list = ['{},{}'.format(tup[1], tup[0]) for tup in polyline.decode(encoded)]

      for j in range(len(coordinate_list) // chunk_size):
        logger.debug('Processing API chunk: {}'.format(j))
        offset = j*chunk_size
        # Grab a chunk of items.
        chunk_coords = coordinate_list[offset : min(offset + chunk_size, len(coordinate_list))]
        coordinate_str = ';'.join(chunk_coords)

        access_token = 'pk.eyJ1IjoibWlsb2tub3dsZXM5NyIsImEiOiJja3oxcnlvYngxNjFrMnVtanB2N3dnZ212In0.4fQMtF4yhwXBhRVoh97x_w'
        mapbox_url = 'https://api.mapbox.com/matching/v5/mapbox/walking/{}'.format(coordinate_str)
        param = {
          'radiuses': ';'.join([radius_meters for _ in range(len(chunk_coords))]),
          'geometries': 'geojson',
          'access_token': access_token,
          'steps': 'false'
        }

        response = requests.get(mapbox_url, params=param).json()

        if response['code'] == 'Ok':
          geometry = response['matchings'][0]['geometry']
          db.add_or_update_matched_features(id, j, geometry)
        else:
          raise Exception('API error during map matching for {}'.format(id))

    return jsonify({'unmatched_ids': len(unmatched_ids)}), 200

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
    r = strava.get_activity_by_id(STRAVA_TOKEN, id)
    return jsonify(r), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

if __name__ == "__main__":
  app.logger.setLevel(logging.DEBUG)
  app.run(port=5001, debug=True)
