import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon

file_fmt = '../static/geojson/{}_graph.gpkg'

def save_networks():
  # This will be a shapely Polygon.
  boundary = gpd.read_file('../static/geojson/cambridge.geojson')['geometry'][0]

  print('Loading graph ...')
  for network_type in ('walk', 'drive'):
    print('Loading network of type {}'.format(network_type))
    G = ox.graph_from_polygon(boundary, network_type=network_type)
    ox.plot_graph(G)
    ox.io.save_graph_geopackage(G, filepath=file_fmt.format(network_type), directed=False, encoding='utf-8')
    print('Saved!')

  print('Done')

# load GeoPackage as node/edge GeoDataFrames indexed as described in OSMnx docs
gpkg_file = file_fmt.format('walk')
gdf_nodes = gpd.read_file(gpkg_file, layer='nodes').set_index('osmid')
gdf_edges = gpd.read_file(gpkg_file, layer='edges').set_index(['u', 'v', 'key'])
assert gdf_nodes.index.is_unique and gdf_edges.index.is_unique

# print(gdf_nodes.head())
print(gdf_edges.head())

total_length = gdf_edges['length'].sum()
print('Total length: {}mi'.format(total_length * 0.000621371))

# convert the node/edge GeoDataFrames to a MultiDiGraph
graph_attrs = {'crs': 'epsg:4326', 'simplified': True}
G2 = ox.graph_from_gdfs(gdf_nodes, gdf_edges, graph_attrs)

# print(type(G2))
# print(G2.head())

# ox.plot_graph(G2)

# gdf_edges.to_file('../static/geojson/walk_edges.geojson', driver='GeoJSON')
