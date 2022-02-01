import base64
import json
import os

import numpy as np
import pandas as pd

import firebase_admin as fa
import firebase_admin.db as db
from firebase_admin import credentials

from util.timestamps import epoch_timestamp_now
from util.file_util import *
import util.matching as matching

from dotenv import load_dotenv
from pprint import pprint


#===============================================================================

load_dotenv() # Take environment variables from .env.

serviceAccountKey = json.loads(base64.b64decode(os.getenv('FIREBASE_KEY_BASE64')).decode('utf-8'))
cred = credentials.Certificate(serviceAccountKey)
fa.initialize_app(cred, {'databaseURL': 'https://runningheatmap-a5864-default-rtdb.firebaseio.com/'})

#===============================================================================

def add_or_update_activity(id, paramdict):
  """
  Create/update an activity in the database.
  """
  # Indicate when this activity was added to the database.
  paramdict.update({'last_update_time': epoch_timestamp_now()})
  ref = db.reference('activities').child(str(id))
  ref.update(paramdict)

#===============================================================================

def get_activity_count():
  """
  Counts the number activities in the database. This might be slow as db scales.
  """
  ref = db.reference('activities')
  return len(ref.get())

#===============================================================================

def get_activities():
  """
  Get all activities from the database.
  """
  return db.reference('activities').get()

#===============================================================================

def get_activity_by_id(id):
  return db.reference('activities').child(str(id)).get()

#===============================================================================

def get_activities_id_set():
  """
  Get a set of all IDs in the database.
  """
  items = db.reference('activities').get()
  return set(items.keys()) if items is not None else set()

#===============================================================================

def get_database_stats():
  """
  Get current stats from the database. These might be out of date.
  """
  return db.reference('stats').get()

#===============================================================================

def get_matched_features_id_set():
  """
  Get a set of activity IDs for which matching has been done already. This helps
  us avoid duplicating calls to the Mapbox API.
  """
  items = db.reference('matched_features').get()
  return set(items.keys()) if items is not None else set()

#===============================================================================

def add_or_update_match(activity_id, chunk_id, json):
  """
  Store map matching results from the Mapbox API.
  """
  db.reference('matched_activities').child(str(id)).child(str(chunk_id)).update(json)

#===============================================================================

def add_or_update_matched_features(activity_id, geometry):
  """
  Store a map-matched segment from the Mapbox API as a geojson feature.
  """
  # uid = str(activity_id) + '-' + str(chunk_id)
  db.reference('matched_features').child(activity_id).update(
    { 'type': 'Feature', 'geometry': geometry }
  )

#===============================================================================

def add_or_update_activity_features(activity_id, geometry):
  """
  Store a raw segment from Strava as a geojson feature.
  """
  uid = str(activity_id)
  db.reference('activity_features').child(uid).update(
    {
      'type': 'Feature',
      'geometry': geometry
    }
  )

#===============================================================================

def clear_matched_activities_and_features():
  """
  DANGER: Clears all matching-related database entries!
    'matched_activities'
    'matched_features'
  """
  db.reference('matched_activities').delete()
  db.reference('matched_features').delete()

#===============================================================================

def get_matched_feature_by_id(activity_id):
  return db.reference('matched_features').child(activity_id).get()

#===============================================================================

def update_coverage(map_name, edges, activity_id):
  """
  Save completed edges to the database for visualization and coverage metrics.
  """
  p = {}

  for i in range(len(edges)):
    from_id = edges.iloc[i]['from']
    to_id = edges.iloc[i]['to']
    edge_name = edges.iloc[i]['name']

    coords = edges.iloc[i]['geometry'].coords
    geom = {
      'type': 'LineString',
      'coordinates': [[p[0], p[1]] for p in coords]
    }

    uid = uid = str(from_id) + '-' + str(to_id)
    p[uid] = {
      'feature': {
        'geometry': geom,
        'type': 'Feature'
      },
      'from': str(from_id),
      'to': str(to_id),
      'name': edge_name,
      'complete': True,
      'completed_by': str(activity_id)
    }

  db.reference('coverage').child(map_name).update(p)

#===============================================================================

def reset_coverage():
  db.reference('coverage').delete()

#===============================================================================

def get_coverage(map_name):
  return db.reference('coverage').child(map_name).get()


#===============================================================================

def update_stats():
  """
  Re-compute stats over the database.
  """
  items = db.reference('activities').get()

  total_activities = len(items.values())
  total_distance = 0
  total_time = 0
  total_elevation_gain = 0

  for item in items.values():
    total_distance += 0.621371 * item['distance'] / 1000
    total_time += item['moving_time'] / 3600.0
    total_elevation_gain += item['total_elevation_gain']

  # Estimate coverage.
  r = db.reference('coverage').child('cambridge').get() # TODO

  _, edges_df = matching.load_graph(graph_folder('drive_graph.gpkg'))

  edges_df['complete'] = pd.Series(np.ones(len(edges_df)))

  for key in r:
    v = np.int64(r[key]['to'])
    u = np.int64(r[key]['from'])

    if edges_df.index.isin([(u, v, 0)]).any():
      edges_df.at[(u, v, 0), 'complete'] = 1

  complete_map_edges = edges_df['complete'].sum()
  total_map_distance = edges_df['length'].sum() * 0.621371 / 1000
  complete_map_distance = edges_df[edges_df['complete'] > 0]['length'].sum() * 0.621371 / 1000

  pdict = {
    'total_distance': total_distance,
    'total_activities': total_activities,
    'total_elevation_gain': total_elevation_gain,
    'avg_distance': total_distance / total_activities,
    'total_time': total_time,
    'total_map_distance': total_map_distance,
    'complete_map_distance': complete_map_distance,
    'total_map_edges': len(edges_df),
    'complete_map_edges':  complete_map_edges,
    'percent_coverage': complete_map_distance / total_map_distance * 100
  }

  db.reference('stats').update(pdict)

  return pdict
