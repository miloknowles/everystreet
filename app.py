import logging
from flask import Flask
from flask import render_template
import csv
import json


app = Flask(__name__)
DATA_PATH = './static/data.csv'


@app.route('/')
def render_map():
  runs = []

  try:
    with open(DATA_PATH, "r") as runs_file:
      reader = csv.DictReader(runs_file)

      for row in reader:
        runs.append(row["polyline"])

      print('Found polylines for {} runs'.format(len(runs)))

  except Exception as e:
    logging.exception(e)

  return render_template("map.html", runs=json.dumps(runs))


@app.route('/activities')
def render_activities():
  activity_ids = []

  try:
    with open(DATA_PATH, "r") as runs_file:
      reader = csv.DictReader(runs_file)

      for row in reader:
        activity_ids.append(row["id"])

  except Exception as e:
    logging.exception(e)

  return render_template(
    "activities.html",
    activity_ids=activity_ids,
    num_activity_ids=len(activity_ids))


@app.route('/stats')
def render_stats():
  return render_template('stats.html')


if __name__ == "__main__":
  app.run(port=5001, debug=True)
