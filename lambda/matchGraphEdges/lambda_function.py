import json
import logging

from geopandas import read_file, GeoDataFrame

# Try to reduce import memory usage.
from numpy import int64, linspace, ceil, array
from pandas import Series, concat

from scipy.spatial import cKDTree
from shapely.geometry import Point


#===============================================================================
logger = logging.getLogger()
logger.setLevel(logging.INFO)
#===============================================================================


def kdtree_from_points(points):
  return cKDTree(points)


def kdtree_from_gdf(df):
  return cKDTree(array(list(df.geometry.apply(lambda x: (x.x, x.y)))))


def load_graph(graph_file):
  """
  Load GeoPackage as node/edge GeoDataFrames indexed as described in OSMnx docs
  """
  nodes_gdf = read_file(graph_file, layer='nodes').set_index('osmid')
  edges_gdf = read_file(graph_file, layer='edges').set_index(['u', 'v', 'key'])
  assert nodes_gdf.index.is_unique and edges_gdf.index.is_unique
  return nodes_gdf, edges_gdf


def resample_points(points, spacing=20):
  """
  Resample GPS coordinates to make matches more likely.

  Args:
    points (list) : List of [lng, lat] coordinates.
    spacing (float) : Maximum distance between points in meters.
  """
  df = GeoDataFrame(geometry=[Point(p) for p in points], crs='EPSG:4326')
  df.to_crs(epsg=3310, inplace=True)
  dist_to_next = df.distance(df.shift(-1))
  dist_to_next[len(dist_to_next)-1] = 0

  resampled = []
  for i in range(len(points)-1):
    pt = points[i]
    next = points[i+1]

    resampled.append(pt)

    if dist_to_next[i] > spacing:
      n = int(ceil(dist_to_next[i] / spacing))
      lngs = linspace(pt[0], next[0], num=n)[1:-1]
      lats = linspace(pt[1], next[1], num=n)[1:-1]
      resampled.extend(zip(lngs, lats))

  return resampled


def match_points_to_edges(points, nodes_df, edges_df, kdtree, max_node_dist=40):
  """
  Matches a sequence of GPS coordinates to edges the street graph. This allows
  us to figure out which edges have been completed.

  Args:
    points (ndarray) : 2D array of [lng, lat] coordinates.
    nodes_df (GeoDataFrame) : dataframe with network nodes.
    edges_df (GeoDataFrame) : dataframe with network edges.
    kdtree (ktree) : a KDtree for quick nearest neighbor lookups.
    max_node_dist (float) : maximum distance for matching a point to a node.

  Returns:
    (GeoDataFrame) with completed edges

  References:
   - https://gis.stackexchange.com/questions/222315/finding-nearest-point-in-other-geodataframe-using-geopandas
  """
  # Get points from matched activity.
  dists, idxs = kdtree.query(points, k=3)

  # Get distance between each point and neighbor in meters.
  # https://gis.stackexchange.com/questions/293310/how-to-use-geoseries-distance-to-get-the-right-answer/293319
  query_gdf = GeoDataFrame(geometry=[Point(p) for p in points], crs='EPSG:4326')
  query_gdf.to_crs(epsg=3310, inplace=True)

  nn0 = nodes_df.iloc[idxs[:,0]].to_crs(epsg=3310).reset_index(drop=True)
  nn1 = nodes_df.iloc[idxs[:,1]].to_crs(epsg=3310).reset_index(drop=True)
  nn2 = nodes_df.iloc[idxs[:,2]].to_crs(epsg=3310).reset_index(drop=True)

  # Put nearest neighbor nodes and distances in one df.
  nn_data = concat(
    [
      Series(nodes_df.iloc[idxs[:,0]].reset_index(drop=False)['osmid'], name='osmid0', dtype=int64),
      Series(nodes_df.iloc[idxs[:,1]].reset_index(drop=False)['osmid'], name='osmid1', dtype=int64),
      Series(nodes_df.iloc[idxs[:,2]].reset_index(drop=False)['osmid'], name='osmid2', dtype=int64),
      Series(query_gdf.distance(nn0), name='dist0'),
      Series(query_gdf.distance(nn1), name='dist1'),
      Series(query_gdf.distance(nn2), name='dist2')
    ],
    axis=1)

  completed_edges = []
  # Put nearest neighbor nodes and distances in one df.
  nn_data = concat(
    [
      Series(nodes_df.iloc[idxs[:,0]].reset_index(drop=False)['osmid'], name='osmid0', dtype=int64),
      Series(nodes_df.iloc[idxs[:,1]].reset_index(drop=False)['osmid'], name='osmid1', dtype=int64),
      Series(nodes_df.iloc[idxs[:,2]].reset_index(drop=False)['osmid'], name='osmid2', dtype=int64),
      Series(dists[:,0], name='dist0'),
      Series(dists[:,1], name='dist1'),
      Series(dists[:,2], name='dist2')
    ],
    axis=1)

  completed_edges = []

  for i in range(len(points) - 1):
    di_values = [nn_data.iloc[i]['dist{}'.format(_)] for _ in range(3)]
    di_valid = [di < max_node_dist for di in di_values]

    # Check if starting point i is near a node. If not, skip.
    # By definition, all other candidates will be farther.
    if not di_valid[0]:
      continue

    j = i + 1
    did_complete_edge = False     # Once we complete an edge that starts from this node, continue.
    tries_remaining = 10          # Far away node matches are unlikely to complete an edge.
    while j < (len(points) - 1) and not did_complete_edge and tries_remaining > 0:

      # Search for the next end point j that's near a node.
      while (j < (len(points) - 1) and nn_data.iloc[j]['dist0'] > max_node_dist):
        j += 1

      # Handle the case where we reach the last point.
      dj = nn_data.iloc[j]['dist0']
      if dj > max_node_dist:
        continue

      # Get the candidate node IDs of i and j.
      u_options = [int64(nn_data.iloc[i]['osmid{}'.format(_)]) for _ in range(3) if di_valid[_]]
      v_options = [int64(nn_data.iloc[j]['osmid{}'.format(_)]) for _ in range(3) if di_valid[_]]

      for u in u_options:
        for v in v_options:
          uv_exists = edges_df.index.isin([(u, v, 0)]).any()
          vu_exists = edges_df.index.isin([(v, u, 0)]).any()

          if uv_exists:
            e = edges_df.loc[(u, v, 0)]
            completed_edges.append(e)
            did_complete_edge = True
          elif vu_exists:
            e = edges_df.loc[(v, u, 0)]
            completed_edges.append(e)
            did_complete_edge = True

      j += 1
      tries_remaining -= 1

  return GeoDataFrame(data=completed_edges)


#===============================================================================
_CURRENT_MAP_ID = "CAMBRIDGE_MA_US"
_NODES_DF, _EDGES_DF = load_graph('{}.gpkg'.format(_CURRENT_MAP_ID))
_KDTREE = kdtree_from_gdf(_NODES_DF)
#===============================================================================

def lambda_handler(event, context):
  global _CURRENT_MAP_ID, _NODES_DF, _EDGES_DF, _KDTREE

  raw_points = event['points']
  map_id = event['map_id']

  # Might need to load a new graph.
  if map_id != _CURRENT_MAP_ID:
    logger.info('Switching to a new map {}'.format(_CURRENT_MAP_ID))
    _CURRENT_MAP_ID = map_id
    _NODES_DF, _EDGES_DF = load_graph('{}.gpkg'.format(_CURRENT_MAP_ID))
    _KDTREE = kdtree_from_gdf(_NODES_DF)

  query_points = resample_points(raw_points, spacing=15.0)
  matched_edges = match_points_to_edges(query_points, _NODES_DF, _EDGES_DF, _KDTREE, max_node_dist=30)

  output = {
    'matched_edge_ids': [],
    'matched_edge_geometries': [],
    'matched_edge_lengths': []
  }

  for i in range(len(matched_edges)):
    from_id = str(matched_edges.iloc[i]['from'])
    to_id = str(matched_edges.iloc[i]['to'])
    output['matched_edge_ids'].append(from_id + '-' + to_id)
    coords = matched_edges.iloc[i]['geometry'].coords
    geom = {
      'type': 'LineString',
      'coordinates': [[p[0], p[1]] for p in coords] # TODO
    }
    output['matched_edge_geometries'].append(geom)
    output['matched_edge_lengths'].append(matched_edges.iloc[i]['length'])

  return {
    'statusCode': 200,
    'body': json.dumps(output)
  }
