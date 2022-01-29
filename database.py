import firebase_admin as fa
import firebase_admin.db as db
from firebase_admin import credentials

from utils import epoch_timestamp_now

cred = credentials.Certificate(".serviceAccountKey.json")
app = fa.initialize_app(cred, {'databaseURL': 'https://runningheatmap-a5864-default-rtdb.firebaseio.com/'})


def add_or_update_activity(id, paramdict):
  """
  Create/update an activity in the database.
  """
  # Indicate when this activity was added to the database.
  paramdict.update({'last_update_time': epoch_timestamp_now()})
  ref = db.reference('activities').child(str(id))
  ref.update(paramdict)


def get_activity_count():
  """
  Counts the number activities in the database. This might be slow as db scales.
  """
  ref = db.reference('activities')
  return len(ref.get())


def get_activities():
  return db.reference('activities').get()
