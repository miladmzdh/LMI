# Imports necessary for the example
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Example usage of the Mobility Localness Index (MLI) Calculation Tool
# This script demonstrates how to use the LMI function with a set of user-defined stop points, home location, and work location.

# Define home and work locations
home_location = (-81.29, 43.52)
work_location = (-81.275888, 43.009603)

# Define stop points with time spent at each location (in seconds)
stop_points_df = pd.DataFrame({
    'x': [-81.36, -81.52, -81.03],
    'y': [43.87, 42.96, 43.52],
    't': [45*60, 500*60, 20*60]
})

# Additional parameters
buffer_size = 0.1  # degrees (approximate, check for accurate unit)
max_dist_nonPOIstops = 50000  # meters
threshold_poi = 0.0025  # degrees (approximate, check for accurate unit)

# Create a new column in the DataFrame for the geometry
stop_points_df['geometry'] = stop_points_df.apply(lambda row: Point(row['x'], row['y']), axis=1)

# Create a GeoDataFrame with the specified coordinate reference system (CRS)
stop_points = gpd.GeoDataFrame(stop_points_df, geometry='geometry', crs='EPSG:4326')

# Call the LMI function with the defined parameters
localness_value = LMI(stop_points, home_location, threshold_poi, max_dist_nonPOIstops, work_location, buffer_size=buffer_size)

# Output the result
print(f"Calculated Mobility Localness Index: {localness_value}")
