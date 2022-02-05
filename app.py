import logging
from unittest.mock import DEFAULT
import polyline
import os

from flask import Flask, render_template, jsonify, request

import util.firebase_api as db
import util.strava_api as strava
from util.timestamps import epoch_timestamp_now
import util.matching as matching
from util.file_util import *

from dotenv import load_dotenv

#===============================================================================

load_dotenv() # Take environment variables from .env.

app = Flask(__name__)
logger = app.logger
STRAVA_TOKEN = strava.get_token_always_valid()
DEFAULT_USER_ID = str(os.getenv('DEFAULT_USER_ID'))

#===============================================================================
#============================= SERVER ROUTES ===================================
#===============================================================================

@app.route('/')
@app.route('/map')
def render_map():
  """
  Render the MapBox map visualization. This is the default page.
  """
  return render_template("map.html")

#===============================================================================

@app.route('/activities')
def render_activities():
  """
  Show the activities page.
  """
  try:
    d = db.get_activity_data(DEFAULT_USER_ID)

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

  return render_template("activities.html", activity_data=[] if d is None else d.values())

#===============================================================================

@app.route('/stats')
def render_stats():
  """
  Show the stats page.
  """
  stats = db.get_user_stats(DEFAULT_USER_ID)
  return render_template('stats.html', **stats)

#===============================================================================

@app.route('/admin')
def render_admin():
  """
  Show the activities page.
  """
  try:
    d = db.get_activity_data(DEFAULT_USER_ID)

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

  return render_template("admin.html", activity_data=[] if d is None else d.values())

#===============================================================================
#============================= SERVER ACTIONS ==================================
#===============================================================================

@app.route('/action/pull-activities')
def update_activities():
  """
  Checks for new activities from Strava.

  If 'scope' arg is set to 'all', the fetch is exhaustive. Otherwise, we just
  scan for activities that occurred in the last week.
  """
  try:
    # If unspecified, just do a fast pull.
    scope = request.args.get('scope', 'week_only', type=str)
    logger.info('scope is {}'.format(scope))

    # Optionally limit query to a certain timeframe.
    if scope == 'all':
      window_time = None
    elif scope == 'day_only':
      window_time = epoch_timestamp_now() - 86400 # Sec per day.
    elif scope == 'week_only':
      window_time = epoch_timestamp_now() - 604800 # Sec per week.
    elif scope == 'month_only':
      window_time = epoch_timestamp_now() - 2592000 # Sec per month.
    else:
      window_time = epoch_timestamp_now() - 604800 # Sec per week.

    existing_ids = db.get_activity_ids(DEFAULT_USER_ID)
    maybe_new_ids = strava.get_activities_id_set(STRAVA_TOKEN, after_time=window_time)

    if scope is None or scope == 'all':
      new_ids = maybe_new_ids
    else:
      new_ids = maybe_new_ids - existing_ids

    new_count = len(new_ids)

    for i, activity_id in enumerate(new_ids):
      logger.debug('processing #{}/{} (id={})'.format(i+1, len(new_ids), activity_id))

      # Get activity data from Strava and add (the relevant part) to our database.
      activity_data = strava.get_activity_by_id(STRAVA_TOKEN, activity_id)
      db.add_or_update_activity(DEFAULT_USER_ID, activity_id, activity_data)

    return jsonify({'total_count': len(maybe_new_ids), 'new_count': new_count}), 200

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
    r = db.update_user_stats(DEFAULT_USER_ID)
    return jsonify(r), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

@app.route('/action/match-activities/<map_id>')
def match_activities(map_id):
  """
  Match GPS points from activities with edges in the road network.
  """
  try:
    if map_id not in ['CAMBRIDGE_MA_US']:
      raise ValueError('Unknown map_id {}'.format(map_id))

    # If unspecified, just process new activities (fast option).
    scope = request.args.get('scope', 'new_only', type=str)
    assert(scope in ['all', 'new_only'])

    activity_ids = db.get_activity_ids(DEFAULT_USER_ID)
    matched_ids = db.get_processed_activity_ids_for_map(DEFAULT_USER_ID, map_id)

    # Figure out which activities need to be processed.
    if scope == 'new_only':
      unmatched_ids = activity_ids - matched_ids
    else:
      unmatched_ids = activity_ids

    logger.info('Matching {} new activity ids (scope is {})'.format(len(unmatched_ids), scope))

    nodes_df, edges_df = matching.load_graph(graph_data_folder('{}.gpkg'.format(map_id)))
    logger.debug('Loaded graph')

    # Build a KDtree for fast queries.
    kdtree = matching.kdtree_from_gdf(nodes_df)
    logger.debug('Built kdtree')

    for activity_id in unmatched_ids:
      logger.debug('Processing {}'.format(activity_id))

      activity_data = db.get_activity_by_id(DEFAULT_USER_ID, activity_id)
      query_points = matching.resample_points(activity_data['geometry']['coordinates'], spacing=15.0)
      matched_edges = matching.match_points_to_edges(query_points, nodes_df, edges_df, kdtree, max_node_dist=30)

      matched_ids = []
      edge_geometries = []
      edge_lengths = []
      for i in range(len(matched_edges)):
        from_id = str(matched_edges.iloc[i]['from'])
        to_id = str(matched_edges.iloc[i]['to'])
        matched_ids.append(from_id + '-' + to_id)
        coords = matched_edges.iloc[i]['geometry'].coords
        geom = {
          'type': 'LineString',
          'coordinates': [[p[0], p[1]] for p in coords] # TODO
        }
        edge_geometries.append(geom)
        edge_lengths.append(matched_edges.iloc[i]['length'])

      db.update_coverage(DEFAULT_USER_ID, map_id, activity_id, matched_ids, edge_geometries, edge_lengths)

    return jsonify({'unmatched_ids': len(unmatched_ids)}), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

@app.route('/action/activity/<activity_id>')
def get_activity_json(activity_id):
  """
  Get the JSON for an activity (debugging).
  """
  try:
    r = strava.get_activity_by_id(STRAVA_TOKEN, activity_id)
    return jsonify(r), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

@app.route('/action/clear-coverage/<map_id>')
def clear_coverage(map_id):
  try:
    # db.clear_coverage()
    db.clear_user_coverage(DEFAULT_USER_ID, map_id)
    return jsonify('ok'), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300


if __name__ == "__main__":
  app.logger.setLevel(logging.DEBUG)
  app.run(port=5001, debug=True)
