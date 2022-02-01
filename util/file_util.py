import os


def top_folder(rel="") -> str:
  return os.path.join(os.path.abspath(os.path.join(os.path.realpath(__file__), "../../")), rel)


def static_folder(rel="") -> str:
  return os.path.join(top_folder("static"), rel)


def geojson_folder(rel="") -> str:
  return os.path.join(static_folder("geojson"), rel)


def graph_folder(rel="") -> str:
  return os.path.join(static_folder("graphs"), rel)
