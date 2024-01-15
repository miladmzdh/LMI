# Local Mobility Index (LMI) Calculation Tool

This Python tool calculates a "Local Mobility Index" (LMI) for given stop points, taking into account home and optional work locations. It is designed to assess the localness of mobility patterns by considering proximity to points of interest (POIs) and distances from specified locations.

## Features:
- **Dynamic POI Downloading**: Automatically downloads POIs needed for computation.
- **User-Defined Parameters**: Accepts user-specified home location (mandatory) and work location (optional), along with other customizable parameters.
- **Geospatial Analysis**: Utilizes geospatial libraries like OSMnx, Pandana, and GeoPandas for handling spatial data and network analysis.

## Functionality:
- `LMI(stop_points, home_location, threshold_poi, max_dist_nonPOIstops, second_place = -1, filter_dist_from_home = None, buffer_size = None)`
  - `stop_points`: A GeoDataFrame of stop points with known Coordinate Reference System (CRS).
  - `home_location`: A tuple (longitude, latitude) of the user's home location.
  - `threshold_poi`: The maximum distance (in meters) to consider a POI relevant.
  - `max_dist_nonPOIstops`: The maximum distance (in meters) for non-POI stops.
  - `second_place`: A tuple (longitude, latitude) of the user's work location, or -1 if not applicable.
  - `filter_dist_from_home`: Optional filter distance (in meters) from the home location.
  - `buffer_size`: Optional buffer size (in meters) for area of interest around stop points.

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

## Installation:
Ensure all dependencies are installed. You can use pip to install them:
```bash
pip install networkx osmnx pandana pandas numpy geopandas shapely datetime geopy scipy
