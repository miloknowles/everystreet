import base64
import json
from math import radians
import os

import polyline

import firebase_admin as fa
import firebase_admin.db as db
from firebase_admin import credentials

from python.file_util import *
import python.matching as matching

from dotenv import load_dotenv

#===============================================================================

load_dotenv() # Take environment variables from .env.

serviceAccountKey = json.loads(base64.b64decode(os.getenv('FIREBASE_KEY_BASE64')).decode('utf-8'))
cred = credentials.Certificate(serviceAccountKey)
fa.initialize_app(cred, {'databaseURL': os.getenv('FIREBASE_DB_URL')})

#===============================================================================

def get_processed_activity_ids_for_map(user_id, map_id):
  """
  Get a set of all user's activity IDs that have been processed so far.
  """
  items = db.reference('user_data').child(user_id).child('processed').child(map_id).get()
  return set(items.keys()) if items is not None else set()

#===============================================================================

def get_activity_data(user_id):
  """
  Get metadata about user activities that have been processed so far.
  """
  return db.reference('user_data').child(user_id).child('activity_data').get()

#===============================================================================

def get_activity_ids(user_id):
  """
  Get metadata about user activities that have been processed so far.
  """
  items = db.reference('user_data').child(user_id).child('activity_data').get()
  return set(items.keys()) if items is not None else set()

#===============================================================================

def get_activity_by_id(user_id, activity_id):
  """
  Get metadata about user activities that have been processed so far.
  """
  return db.reference('user_data').child(user_id).child('activity_data').child(activity_id).get()

#===============================================================================

def get_user_stats(user_id):
  """
  Get user stats from the database.
  """
  stats = db.reference('user_data').child(user_id).child('stats').get()
  return {} if stats is None else stats

#===============================================================================

def add_or_update_activity(user_id, activity_id, activity_data):
  """
  Store metadata and raw route information from Strava as a geojson feature.
  """

  # Also store the decoded coordinates from the activity for faster client-side lookup later.
  points = [[c[1], c[0]] for c in polyline.decode(activity_data['map']['polyline'])]

  db.reference('user_data').child(user_id).child('activity_data').child(str(activity_id)).update(
    {
      'id': activity_id,
      'name': activity_data['name'],
      'distance': activity_data['distance'],
      'start_date': activity_data['start_date'],
      'moving_time': activity_data['moving_time'],
      'geometry': {'type': 'LineString', 'coordinates': points}
    }
  )

#===============================================================================

def update_coverage(user_id, map_id, activity_id, edge_ids, edge_geometries, edge_lengths):
  """
  Save completed edges to the database for visualization and coverage metrics.
  """
  p = {}

  for i, e in enumerate(edge_ids):
    p[str(e)] = {
      'completed_by': {str(activity_id): 1},
      'geometry': edge_geometries[i],
      'length': edge_lengths[i]
    }

  ref = db.reference('user_data').child(user_id).child('coverage').child(map_id)
  ref.update(p)

  # Now indicate that this activity was processed for this map.
  ref = db.reference('user_data').child(user_id).child('processed').child(map_id)
  ref.update({activity_id: 1})

#===============================================================================

def update_user_stats(user_id):
  """
  Re-compute total user stats over their activities.
  """
  stats_ref = db.reference('user_data').child(user_id).child('stats')
  activities_ref = db.reference('user_data').child(user_id).child('activity_data')

  activities = activities_ref.get()

  total_distance = 0
  total_time = 0
  for item in activities.values():
    total_distance += 0.621371 * item['distance'] / 1000
    total_time += item['moving_time'] / 3600.0

  map_id = 'CAMBRIDGE_MA_US'

  # Get completed edges from the databse.
  r = db.reference('user_data').child(user_id).child('coverage').child(map_id).get()

  # Get the entire edge set from disk.
  _, edges_df = matching.load_graph(graph_data_folder('{}.gpkg'.format(map_id)))

  completed_distance = 0
  for key in r:
    completed_distance += r[key]['length']

  meters_to_mi = 0.621371 / 1000
  total_map_dist = edges_df['length'].sum() * meters_to_mi
  compl_map_dist = completed_distance * meters_to_mi

  p = {
    'total_distance': total_distance,
    'total_activities': len(activities.values()),
    'total_time': total_time,
    'coverage': {
      map_id: {
        'total_distance': total_map_dist,
        'completed_distance': compl_map_dist,
        'total_edges': len(edges_df),
        'completed_edges': len(r) if r is not None else 0,
        'percent_coverage': 100.0 * compl_map_dist / total_map_dist
      }
    }
  }

  stats_ref.update(p)

  return p

#===============================================================================
#============================ DATABASE MAINTENANCE =============================
#===============================================================================


def clear_user_activities(user_id):
  ref = db.reference('user_data').child(user_id).child('activity_data')
  ref.delete()


def clear_user_coverage(user_id, map_id):
  ref = db.reference('user_data').child(user_id).child('coverage').child(map_id)
  ref.delete()
