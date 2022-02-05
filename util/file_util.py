import os


def top_folder(rel="") -> str:
  return os.path.join(os.path.abspath(os.path.join(os.path.realpath(__file__), "../../")), rel)


def static_folder(rel="") -> str:
  return os.path.join(top_folder("static"), rel)


def map_boundaries_folder(rel="") -> str:
  return os.path.join(static_folder("map_boundaries"), rel)


def graph_data_folder(rel="") -> str:
  return os.path.join(static_folder("graph_data"), rel)


def graph_geojson_folder(rel="") -> str:
  return os.path.join(static_folder("graph_geojson"), rel)
