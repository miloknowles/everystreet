import base64
import json
import os

import firebase_admin as fa
import firebase_admin.db as db
from firebase_admin import credentials

from util.timestamps import epoch_timestamp_now

from dotenv import load_dotenv
from pprint import pprint

#===============================================================================

load_dotenv() # Take environment variables from .env.

serviceAccountKey = json.loads(base64.b64decode(os.getenv('FIREBASE_KEY_BASE64')).decode('utf-8'))
cred = credentials.Certificate(serviceAccountKey)
app = fa.initialize_app(cred, {'databaseURL': 'https://runningheatmap-a5864-default-rtdb.firebaseio.com/'})

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

def update_stats():
  """
  Re-compute stats over the database.
  """
  items = get_activities()

  total_activities = len(items.values())

  total_distance = 0
  total_time = 0
  total_elevation_gain = 0
  for item in items.values():
    total_distance += 0.621371 * item['distance'] / 1000
    total_time += item['moving_time'] / 3600.0
    total_elevation_gain += item['total_elevation_gain']

  pdict = {
    'total_distance': total_distance,
    'total_activities': total_activities,
    'total_elevation_gain': total_elevation_gain,
    'avg_distance': total_distance / total_activities,
    'total_time': total_time
  }

  db.reference('stats').update(pdict)

  return pdict

#===============================================================================

def get_stats():
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
  items = db.reference('matched_activities').get()
  return set(items.keys()) if items is not None else set()

#===============================================================================

def add_or_update_match(id, chunk_id, json):
  """
  Store map matching results from the Mapbox API.
  """
  db.reference('matched_activities').child(str(id)).child(str(chunk_id)).update(json)
