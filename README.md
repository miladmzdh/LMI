# Local Mobility Index (LMI) Calculation Tool

This Python tool calculates a "Local Mobility Index" (LMI) for given stop points, taking into account home and optional work locations. It is designed to assess the localness of mobility patterns by considering proximity to points of interest (POIs) and distances from specified locations.

## Features:
- **Dynamic POI Downloading**: Automatically downloads POIs needed for computation.
- **User-Defined Parameters**: Accepts user-specified home location (mandatory) and work location (optional), along with other customizable parameters.
- **Geospatial Analysis**: Utilizes geospatial libraries like OSMnx, Pandana, and GeoPandas for handling spatial data and network analysis.

## Functionality:
- `LMI(stop_points, home_location, poiCutoff, nonPoiMaxDistance, second_place = -1, networkBufferAreaSize = None)`
  - `stop_points`: A GeoDataFrame of stop points with known Coordinate Reference System (CRS).
  - `home_location`: A tuple (X, Y) of the user's home location in the same Coordinate Reference System as the stop_points.
  - `poiCutoff`: The maximum distance (in meters) to consider a POI relevant. Determines how close a POI must be to be considered in the localness calculation.
  - `nonPoiMaxDistance`: The maximum distance (in meters) for non-POI stops. This parameter sets the maximum influence of stops that are not points of interest in the localness score.
  - `second_place`: Optional. A tuple (X, Y) of the user's work location in the same Coordinate Reference System as the stop_points, or -1 if not applicable. This parameter allows for bi-centric analysis of mobility patterns.
  - `networkBufferAreaSize`: Optional. Buffer size (in meters) for the area of interest around stop points for network data download. Determines the spatial extent for downloading network and POI data.

## Usage:
1. **Input Preparation**: Prepare a GeoDataFrame of stop points.
2. **Function Call**: Use the LMI function with the required parameters.
3. **Output**: The function returns a localness value, representing the degree of locality in the user's mobility pattern.

## Dependencies:
- `networkx`
- `osmnx`
- `pandana`
- `pandas`
- `numpy`
- `geopandas`
- `shapely`
- `datetime`
- `geopy`
- `scipy`
- `pyproj`
