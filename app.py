import logging
import json
from pprint import pprint
from flask import Flask, render_template, jsonify

import util.database as db
import util.strava_api as strava

app = Flask(__name__)
DATA_PATH = './static/data.csv'

#===============================================================================

@app.route('/')
def render_map():
  items = []

  try:
    d = db.get_activities()
    polylines = [item['map']['polyline'] for item in d.values()]
    logging.debug('Got {} polylines'.format(len(polylines)))

  except Exception as e:
    logging.exception(e)
    return jsonify({'error': str(e)}), 300

  return render_template("map.html", polylines=json.dumps(polylines))

#===============================================================================

@app.route('/activities')
def render_activities():
  items = []

  try:
    d = db.get_activities()

  except Exception as e:
    logging.exception(e)
    return jsonify({'error': str(e)}), 300

  return render_template("activities.html", items=d.values())

#===============================================================================

@app.route('/stats')
def render_stats():
  return render_template('stats.html', **db.get_stats())

#===============================================================================

@app.route('/action/update-activities')
def update_activities():
  """
  Checks for new activities from Strava.
  """
  try:
    token = strava.get_token_always_valid()
    ids = strava.get_all_activity_ids(token)

    current_count = db.get_activity_count()
    updated_count = len(ids)

    for i, id in enumerate(ids):
      print('Processing {}/{}'.format(i + 1, len(ids)))

      # Get activity data from Strava.
      r = strava.get_activity_by_id(token, id)

      # Add it to our database.
      db.add_or_update_activity(id, r)

    return jsonify({'total_count': updated_count, 'new_count': updated_count - current_count}), 200

  except Exception as e:
    logging.exception(e)
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
    logging.exception(e)
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
    logging.exception(e)
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
    logging.exception(e)
    return jsonify({'error': str(e)}), 300

#===============================================================================

if __name__ == "__main__":
  app.run(port=5001, debug=True)
