import sys

import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd

from scipy.spatial import cKDTree
from shapely.geometry import Point
from shapely.geometry import Polygon

import polyline

sys.path.append('..')
from util.database import get_activity_by_id, get_matched_feature_by_id

graph_file_fmt = '../static/geojson/{}_graph.gpkg'


def save_networks():
  boundary = gpd.read_file('../static/geojson/cambridge.geojson')['geometry'][0] # shapely Polygon.

  print('Loading graph ...')
  for network_type in ('walk', 'drive'):
    print('Loading network of type {}'.format(network_type))
    G = ox.graph_from_polygon(boundary, network_type=network_type)
    ox.plot_graph(G)
    ox.io.save_graph_geopackage(G, filepath=graph_file_fmt.format(network_type), directed=False, encoding='utf-8')
    print('Saved!')

  print('Done')


def save_geojson(graph_type):
  gpkg_file = graph_file_fmt.format(graph_type)
  nodes_gdf = gpd.read_file(gpkg_file, layer='nodes').set_index('osmid')
  edges_gdf = gpd.read_file(gpkg_file, layer='edges').set_index(['u', 'v', 'key'])
  assert nodes_gdf.index.is_unique and edges_gdf.index.is_unique

  edges_gdf.to_file('../static/geojson/{}_edges.geojson'.format(graph_type), driver='GeoJSON')


# print(nodes_gdf.head())
# print(edges_gdf.head())

# convert the node/edge GeoDataFrames to a MultiDiGraph
# graph_attrs = {'crs': 'epsg:4326', 'simplified': True}
# G2 = ox.graph_from_gdfs(nodes_gdf, edges_gdf, graph_attrs)

# print(type(G2))
# print(G2.head())

# ox.plot_graph(G2)
# edges_gdf.to_file('../static/geojson/walk_edges.geojson', driver='GeoJSON')


def total_length(edges_gdf):
  total_length = edges_gdf['length'].sum()
  print('Total length: {}mi'.format(total_length * 0.000621371))
  return total_length


def resample_points(points, max_dist_btw=10):
  df = gpd.GeoDataFrame(geometry=[Point(p) for p in query_points], crs='EPSG:4326')
  df.to_crs(epsg=3310, inplace=True)
  dist_to_next = df.distance(df.shift(-1))
  dist_to_next[len(dist_to_next)-1] = 0

  resampled = []
  for i in range(len(points)-1):
    pt = points[i]
    next = points[i+1]

    resampled.append(pt)

    if dist_to_next[i] > max_dist_btw:
      n = int(np.ceil(dist_to_next[i] / max_dist_btw))
      lngs = np.linspace(pt[0], next[0], num=n)[1:-1]
      lats = np.linspace(pt[1], next[1], num=n)[1:-1]
      resampled.extend(zip(lngs, lats))

  return resampled


# load GeoPackage as node/edge GeoDataFrames indexed as described in OSMnx docs
gpkg_file = graph_file_fmt.format('drive')
nodes_gdf = gpd.read_file(gpkg_file, layer='nodes').set_index('osmid')
edges_gdf = gpd.read_file(gpkg_file, layer='edges').set_index(['u', 'v', 'key'])
assert nodes_gdf.index.is_unique and edges_gdf.index.is_unique

# Build a KDtree for fast queries.
node_points = np.array(list(nodes_gdf.geometry.apply(lambda x: (x.x, x.y))))
kdtree = cKDTree(node_points)
print('Built KDtree')

activity_id = '6591898176'
# matched_feature = get_matched_feature_by_id(activity_id)
decoded = polyline.decode(get_activity_by_id(activity_id)['map']['polyline'])
query_points = [[tup[1], tup[0]] for tup in decoded]

query_points = resample_points(query_points, max_dist_btw=20.0)

# query_points = matched_feature['geometry']['coordinates']
print('Got {} query points for activity {}'.format(len(query_points), activity_id))
# print(query_points)

fig, ax = plt.subplots()
nodes_gdf.plot(ax=ax, marker='x', color='blue', markersize=3)
edges_gdf.plot(ax=ax, color='black', linewidth=1)
# plt.show()

def register_feature(query_points, nodes_gdf, edges_gdf, kdtree):
  """
  For each coordinate in query_points, find its k nearest neighbors in target_points.
  https://gis.stackexchange.com/questions/222315/finding-nearest-point-in-other-geodataframe-using-geopandas

  Args:
    query_points (np.ndarray) : 2D array of [lng, lat] coordinates.
    kdtree (cKDTree) : a KDtree for quick nearest neighbor lookups.
  """
  # Get points from matched activity.
  dists, idxs = kdtree.query(query_points, k=3)

  # Get distance between each point and neighbor in meters.
  # https://gis.stackexchange.com/questions/293310/how-to-use-geoseries-distance-to-get-the-right-answer/293319
  query_gdf = gpd.GeoDataFrame(geometry=[Point(p) for p in query_points], crs='EPSG:4326')
  query_gdf.plot(ax=ax, color='yellow')

  query_gdf.to_crs(epsg=3310, inplace=True)

  nn0 = nodes_gdf.iloc[idxs[:,0]].to_crs(epsg=3310).reset_index(drop=True)
  nn1 = nodes_gdf.iloc[idxs[:,1]].to_crs(epsg=3310).reset_index(drop=True)
  nn2 = nodes_gdf.iloc[idxs[:,2]].to_crs(epsg=3310).reset_index(drop=True)

  # Put nearest neighbor nodes and distances in one df.
  nn_data = pd.concat(
    [
      pd.Series(nodes_gdf.iloc[idxs[:,0]].reset_index(drop=False)['osmid'], name='osmid0', dtype=np.int64),
      pd.Series(nodes_gdf.iloc[idxs[:,1]].reset_index(drop=False)['osmid'], name='osmid1', dtype=np.int64),
      pd.Series(nodes_gdf.iloc[idxs[:,2]].reset_index(drop=False)['osmid'], name='osmid2', dtype=np.int64),
      pd.Series(query_gdf.distance(nn0), name='dist0'),
      pd.Series(query_gdf.distance(nn1), name='dist1'),
      pd.Series(query_gdf.distance(nn2), name='dist2')
    ],
    axis=1)

  max_dist_btw_point_and_node = 40 # m

  completed_edges = []

  for i in range(len(query_points) - 1):
    di_values = [nn_data.iloc[i]['dist{}'.format(_)] for _ in range(3)]
    di_valid = [di < max_dist_btw_point_and_node for di in di_values]

    # Check if starting point i is near a node. If not, skip.
    # By definition, all other candidates will be farther.
    if not di_valid[0]:
      continue

    print('Starting from point {} (distance is {} m)'.format(i, di_values[0]))

    j = i + 1
    did_complete_edge = False     # Once we complete an edge that starts from this node, continue.
    tries_remaining = 10          # Far away node matches are unlikely to complete an edge.
    while j < (len(query_points) - 1) and not did_complete_edge and tries_remaining > 0:

      # Search for the next end point j that's near a node.
      while (j < (len(query_points) - 1) and nn_data.iloc[j]['dist0'] > max_dist_btw_point_and_node):
        j += 1

      # Handle the case where we reach the last point.
      dj = nn_data.iloc[j]['dist0']
      if dj > max_dist_btw_point_and_node:
        continue

      print('Trying endpoint {} (distance is {} m)'.format(j, dj))

      # Get the candidate node IDs of i and j.
      u_options = [np.int64(nn_data.iloc[i]['osmid{}'.format(_)]) for _ in range(3) if di_valid[_]]
      v_options = [np.int64(nn_data.iloc[j]['osmid{}'.format(_)]) for _ in range(3) if di_valid[_]]

      for u in u_options:
        for v in v_options:
          uv_exists = edges_gdf.index.isin([(u, v, 0)]).any()
          vu_exists = edges_gdf.index.isin([(v, u, 0)]).any()

          if uv_exists:
            e = edges_gdf.loc[(u, v, 0)]
            completed_edges.append(e)
            did_complete_edge = True
          elif vu_exists:
            e = edges_gdf.loc[(v, u, 0)]
            completed_edges.append(e)
            did_complete_edge = True

      j += 1
      tries_remaining -= 1

  print('Completed {} edges'.format(len(completed_edges)))
  completed_gdf = gpd.GeoDataFrame(data=completed_edges)
  completed_gdf.plot(ax=ax, color='green')


register_feature(query_points, nodes_gdf, edges_gdf, kdtree)
plt.show()

# ckdnearest(gpd1, gpd2)

# print(nodes_gdf.head())
# print(edges_gdf.head())

# convert the node/edge GeoDataFrames to a MultiDiGraph
# graph_attrs = {'crs': 'epsg:4326', 'simplified': True}
# G2 = ox.graph_from_gdfs(nodes_gdf, edges_gdf, graph_attrs)

# print(type(G2))
# print(G2.head())

# ox.plot_graph(G2)
# edges_gdf.to_file('../static/geojson/walk_edges.geojson', driver='GeoJSON')
