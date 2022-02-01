from dis import dis
from nis import match
import os, sys

import osmnx as ox
import geopandas as gpd
import geopy
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd

from scipy.spatial import cKDTree
from shapely.geometry import Point
from shapely.geometry import Polygon

sys.path.append('..')
from util.database import get_matched_feature_by_id

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
matched_feature = get_matched_feature_by_id(activity_id)
query_points = matched_feature['geometry']['coordinates']
print('Got {} query points for activity {}'.format(len(query_points), activity_id))
# print(query_points)

fig, ax = plt.subplots()
nodes_gdf.plot(ax=ax, marker='x', color='blue', markersize=1)
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
  dists, idxs = kdtree.query(query_points, k=1)

  # Get distance between each point and neighbor in meters.
  # https://gis.stackexchange.com/questions/293310/how-to-use-geoseries-distance-to-get-the-right-answer/293319
  query_gdf = gpd.GeoDataFrame(geometry=[Point(p) for p in query_points], crs='EPSG:4326')
  query_gdf.plot(ax=ax, color='yellow')
  query_gdf.to_crs(epsg=3310, inplace=True)
  nn_gdf = nodes_gdf.iloc[idxs].to_crs(epsg=3310).reset_index(drop=True)
  distance_m = query_gdf.distance(nn_gdf)

  # Put nearest neighbor nodes and distances in one df.
  nn_data = pd.concat(
    [
      nodes_gdf.iloc[idxs].reset_index(drop=False),
      pd.Series(distance_m, name='distance_m')
    ],
    axis=1)

  # print(nn_data.head())
  max_dist_btw_point_and_node = 30 # m

  print(edges_gdf.index)
  # assert(False)

  completed_edges = []

  for i in range(len(query_points) - 1):
    di = nn_data.iloc[i]['distance_m']

    # Check if starting point i is near a node. If not, skip.
    if di > max_dist_btw_point_and_node:
      continue

    print('Starting from point {} (distance is {} m)'.format(i, di))

    # Search for an end point j that's near a node.
    j = i+1
    while (j < (len(query_points) - 1) and nn_data.iloc[j]['distance_m'] > max_dist_btw_point_and_node):
      j += 1

    # Handle the case where we reach the last point.
    dj = nn_data.iloc[j]['distance_m']
    if dj > max_dist_btw_point_and_node:
      continue

    print('Ending at point {} (distance is {} m)'.format(j, dj))

    # Get the node IDs of i and j.
    u = nn_data.iloc[i]['osmid']
    v = nn_data.iloc[j]['osmid']

    # print(u, v)

    tmp_gdf = gpd.GeoDataFrame(geometry=[nn_data.iloc[i].geometry, nn_data.iloc[j].geometry])
    tmp_gdf.plot(ax=ax, marker='o', color='red', markersize=2)
    # plt.show()

    # The edges dataframe has a MultiIndex with (u, v, ?).
    uv_exists = edges_gdf.index.isin([(u, v, 0)]).any()
    vu_exists = edges_gdf.index.isin([(v, u, 0)]).any()

    if uv_exists:
      e = edges_gdf.loc[(u, v, 0)]
      completed_edges.append(e)
    elif vu_exists:
      e = edges_gdf.loc[(v, u, 0)]
      completed_edges.append(e)

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
