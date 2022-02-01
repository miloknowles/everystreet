import requests
import logging
import polyline

from flask import Flask, render_template, jsonify, request

import util.database as db
import util.strava_api as strava
from util.timestamps import epoch_timestamp_now
import util.matching as matching
from util.file_util import *

app = Flask(__name__)
logger = app.logger
STRAVA_TOKEN = strava.get_token_always_valid()

#===============================================================================

@app.route('/')
@app.route('/map')
def render_mapbox():
  """
  Render the MapBox map visualization. This is the default page.
  """
  return render_template("mapbox.html")

#===============================================================================

@app.route('/activities')
def render_activities():
  """
  Show the activities page.
  """
  try:
    d = db.get_activities()

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

  return render_template("activities.html", items=d.values())

#===============================================================================

@app.route('/stats')
def render_stats():
  """
  Show the stats page.
  """
  return render_template('stats.html', **db.get_database_stats())

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
    scope_arg = request.args.get('scope', 'week_only', type=str)
    logger.info('scope is {}'.format(scope_arg))

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
      logger.debug('processing #{}/{} (id={})'.format(i+1, len(new_ids), id))

      # Get activity data from Strava.
      r = strava.get_activity_by_id(STRAVA_TOKEN, id)

      # Add it to our database.
      db.add_or_update_activity(id, r)

      # Also store the decoded coordinates from the activity for faster client-side lookup later.
      coords = [[c[1], c[0]] for c in polyline.decode(r['map']['polyline'])]
      db.add_or_update_activity_features(id, {'coordinates': coords, 'type': 'LineString'})

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
    r = db.update_stats()
    return jsonify(r), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

@app.route('/action/match-activities')
def match_activities():
  """
  Match GPS points from an activity with edges in the road network.
  """
  try:
    # If unspecified, just process new activities (fast option).
    scope_arg = request.args.get('scope', 'new_only', type=str)
    assert(scope_arg in ['all', 'new_only'])

    activity_ids = db.get_activities_id_set()
    matched_ids = db.get_matched_id_set()

    # Figure out which activities need to be processed.
    if scope_arg == 'new_only':
      unmatched_ids = activity_ids - matched_ids
    else:
      unmatched_ids = activity_ids

    logger.info('Matching {} new activity ids (scope is {})'.format(len(unmatched_ids), scope_arg))

    nodes_df, edges_df = matching.load_graph(graph_folder('drive_graph.gpkg'))
    logger.debug('Loaded graph')

    # Build a KDtree for fast queries.
    kdtree = matching.kdtree_from_gdf(nodes_df)
    logger.debug('Built kdtree')

    for activity_id in unmatched_ids:
      logger.debug('Processing {}'.format(activity_id))

      activity_data = db.get_activity_by_id(activity_id)
      decoded = polyline.decode(activity_data['map']['polyline'])
      query_points = matching.resample_points([[p[1], p[0]] for p in decoded], spacing=20.0)
      matched_edges = matching.match_points_to_edges(query_points, nodes_df, edges_df, kdtree, max_node_dist=40)

      logger.debug('Updating database')
      db.update_coverage('cambridge', matched_edges, activity_id)

    return jsonify({'unmatched_ids': len(unmatched_ids)}), 200

  except Exception as e:
    logger.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

@app.route('/action/activity/<id>')
def get_activity_json(id):
  """
  Get the JSON for an activity (debugging).
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
