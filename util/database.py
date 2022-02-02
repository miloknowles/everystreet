import base64
import json
import os
from sqlite3 import complete_statement

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

def get_activities():
  """
  Get all activities from the database.
  """
  return db.reference('activities').get()

#===============================================================================

def get_activity_by_id(id):
  """
  Get database activity by its ID.
  """
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

def get_matched_id_set():
  """
  Get a set of activity IDs for which matching has been done already. This helps
  us avoid duplicating calls to the Mapbox API.
  """
  items = db.reference('coverage').child('matched_activities').get()
  return set(items.keys()) if items is not None else set()

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

def update_coverage(map_name, edges, activity_id):
  """
  Save completed edges to the database for visualization and coverage metrics.
  """
  p = {}

  # Indicate that we processed this activity.
  db.reference('coverage').child('matched_activities').child(str(activity_id)).update({'num_edges': len(edges)})

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
      'osmid': str(edges.iloc[i]['osmid']),
      'length': edges.iloc[i]['length'],
      'from': str(from_id),
      'to': str(to_id),
      'name': edge_name,
      'complete': True,
      'completed_by': str(activity_id)
    }

  db.reference('coverage').child(map_name).update(p)

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

  edges_df['complete'] = np.zeros(len(edges_df))

  dist = 0
  for key in r:
    dist += r[key]['length']

  total_map_distance = edges_df['length'].sum() * 0.621371 / 1000
  complete_map_distance = dist * 0.621371 / 1000

  pdict = {
    'total_distance': total_distance,
    'total_activities': total_activities,
    'total_elevation_gain': total_elevation_gain,
    'avg_distance': total_distance / total_activities,
    'total_time': total_time,
    'total_map_distance': total_map_distance,
    'complete_map_distance': complete_map_distance,
    'total_map_edges': len(edges_df),
    'complete_map_edges':  len(r),
    'percent_coverage': complete_map_distance / total_map_distance * 100
  }

  db.reference('stats').update(pdict)

  return pdict

#===============================================================================
#============================ DATABASE MAINTENANCE =============================
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

def clear_coverage():
  """
  DANGER: Clears all children under 'coverage' in the database.
  """
  db.reference('coverage').delete()
