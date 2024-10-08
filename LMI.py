def LMI(stop_points, home_location, poiCutoff, nonPoiMaxDistance, second_place = -1, networkBufferAreaSize = None, POITypeList = None, pois = None):
    
    # importing packages
    
    import networkx as nx
    import osmnx as ox
    import pandana as pdna
    import pandas as pd
    import numpy as np
    import geopandas as gpd
    from shapely.geometry import Point, LineString, Polygon
    from datetime import datetime, timedelta, time
    from geopy.distance import geodesic
    from geopy.distance import distance
    from scipy.spatial.distance import cdist
    import numbers
    from pyproj import Transformer, CRS
    
    # Check if stop__points is a GeoDataFrame with known CRS
    if not isinstance(stop_points, gpd.GeoDataFrame) or stop_points.crs is None:
        raise ValueError("Stop Points must be a GeoDataFrame with a known CRS.")
        
    if stop_points.empty:
        raise ValueError("Stop Points must not be empty")

    # Function to check if an object is a tuple of two numbers
    def is_numeric_tuple(obj):
        return isinstance(obj, tuple) and len(obj) == 2 and all(isinstance(n, numbers.Number) for n in obj)

    # Check if home_location and second_place are tuples of two numbers
    if not is_numeric_tuple(home_location):
        raise ValueError("Home Location must be a tuple of two numerical values.")
    if second_place != -1 and not is_numeric_tuple(second_place):
        raise ValueError("Second Place must be a tuple of two numerical values or -1.")

    # Function to check if a value is numerical or None
    def is_numeric_or_none(value):
        return value is None or isinstance(value, numbers.Number)

    # Check if the other parameters are numerical or their default values
    if not all(is_numeric_or_none(value) for value in [poiCutoff, nonPoiMaxDistance, networkBufferAreaSize]):
        raise ValueError("poiCutoff, nonPoiMaxDistance, and networkBufferAreaSize must be numerical or None/default.")

    # Check if POITypeList is a list containing only string values
    if POITypeList is not None:
        if not isinstance(POITypeList, list) or not all(isinstance(item, str) for item in POITypeList):
            raise ValueError("POITypeList must be a list of strings")

    # Check if pois is a GeoDataFrame and contains the required columns
    if pois is not None:
        if not isinstance(pois, gpd.GeoDataFrame):
            raise TypeError("pois must be a GeoDataFrame")
        if 'geometry' not in pois.columns or 'amenity' not in pois.columns:
            raise ValueError("pois must contain 'geometry' and 'amenity' columns")

    # The analogy and some pre defined variables, tranforming the crs
    
    work_location = second_place

    main_crs_temp = stop_points.crs

    # Function to get the UTM zone for a given latitude and longitude
    def get_utm_zone(lon, lat):
        utm_band = str(int((lon + 180) / 6) % 60 + 1)
        if len(utm_band) == 1:
            utm_band = '0' + utm_band
        if lat >= 0:
            return '326' + utm_band
        else:
            return '327' + utm_band

    # Transform the GeoDataFrame to WGS 84
    gdf_wgs84 = stop_points.to_crs(epsg=4326)

    # Determine UTM zone for transformation
    centroid = gdf_wgs84.geometry.unary_union.centroid
    utm_crs = CRS.from_epsg(get_utm_zone(centroid.x, centroid.y))

    # Transform to UTM CRS
    stop_points = gdf_wgs84.to_crs(utm_crs)

    #transform home and work location to utm
    
    lat, lon = home_location[1], home_location[0]
    
    point = Point(lat, lon)

    # Create a GeoDataFrame with the point
    home_location_gdf = gpd.GeoDataFrame(geometry=[point])

    home_location_gdf.set_crs(main_crs_temp, inplace=True)

    home_location_gdf = home_location_gdf.to_crs(utm_crs)

    if work_location != -1: 
    
        lat, lon = work_location[1], work_location[0]
    
        point = Point(lat, lon)
    
        # Create a GeoDataFrame with the point
        work_location_gdf = gpd.GeoDataFrame(geometry=[point])
    
        work_location_gdf.set_crs(main_crs_temp, inplace=True)

        work_location_gdf = work_location_gdf.to_crs(utm_crs)

    home_location = (home_location_gdf.geometry.iloc[0].x, home_location_gdf.geometry.iloc[0].y)
    work_location = (work_location_gdf.geometry.iloc[0].x, work_location_gdf.geometry.iloc[0].y)

    main_crs = stop_points.crs
    
    user_id= 0
    
    # donwloading the network

    gdf = stop_points.copy()


    # Compute the convex hull
    convex_hull = gdf.unary_union.convex_hull

    if networkBufferAreaSize != None:
        # Add a 5km buffer
        buffer_polygon = convex_hull.buffer(networkBufferAreaSize)

        # Change the CRS of buffer back to EPSG:4326 for osmnx and make a geodataframe
        buffer = gpd.GeoDataFrame(geometry=[buffer_polygon], crs=main_crs).to_crs(epsg=4326)

    else:
        buffer = convex_hull

    # Download the network
    G = ox.graph_from_polygon(buffer.geometry[0], network_type="all")

    # Convert the network to GeoDataFrames
    nodes, edges = ox.graph_to_gdfs(G, nodes=True, edges=True)

    # Reset index of edges DataFrame
    edges = edges.reset_index()
    
    
    if pois is None:
        # Specify the desired tags for amenities
        tags = {'amenity': True}
    
        # Download amenities within the polygon using OSMnx
        geometries = ox.geometries.geometries_from_polygon(buffer.geometry[0], tags=tags)
    
        # Convert the geometries to a GeoDataFrame
        pois = gpd.GeoDataFrame(geometries)
    
        # Filter the DataFrame to keep only the nodes
        pois = pois[pois.index.get_level_values('element_type') == 'node']
        
        # Filter based on the user's list
        if POITypeList is not None:
            pois = pois[pois['amenity'].isin(POITypeList)]

    # Reset the index of the filtered DataFrame
    destination_gdf = pois.reset_index()


    #copmuting the distance between all pois and all stop points
    threshold = poiCutoff  # Define the threshold distance


    dist_dfs = []
    points_for_users = []
    all_nonPOI_points = []

    distance_crs = main_crs
    destination_gdf_projected = destination_gdf.to_crs(distance_crs)

    origin_gdf = stop_points.copy()

    # Create network with pandana
    net = pdna.Network(nodes['x'], nodes['y'], edges['u'], edges['v'], edges[['length']])

    # Reproject the GeoDataFrames
    origin_gdf_projected = origin_gdf.to_crs(distance_crs)

    # Reshape the coordinate arrays
    coords_origin = np.column_stack((origin_gdf.geometry.x, origin_gdf.geometry.y))
    coords_destination = np.column_stack((destination_gdf_projected.geometry.x, destination_gdf_projected.geometry.y))

    # Calculate distances using cdist()
    distances = cdist(coords_origin, coords_destination)

    # Find indices of distances below the threshold
    list_poi_each_stop = []
    for i in distances:

        indices = np.where(i < threshold)[0]

        if len(indices)>0:
            min_index = indices[np.argmin(i[indices])]
            list_poi_each_stop.append(min_index)
        else:
            list_poi_each_stop.append([])

    origin_gdf.to_crs("EPSG:4326", inplace=True)

    origin_nodes = net.get_node_ids(origin_gdf['geometry'].x, origin_gdf['geometry'].y).values

    results = []
    count_o = 0
    for i, origin in origin_gdf.iterrows():
        flag = True #to check if at least it has one poi nearby
        #for each node
        if list_poi_each_stop[count_o]: #check if it's empty
            destination_node = net.get_node_ids([destination_gdf['geometry'].loc[list_poi_each_stop[count_o]].x], [destination_gdf['geometry'].loc[list_poi_each_stop[count_o]].y]).values
            origin_node = origin_nodes[count_o]

            # Calculate the shortest path length using Pandana
            path_length = net.shortest_path_length(origin_node, destination_node[0])

            if path_length <= threshold:
                flag = False #Yes it has at least one poi nearby
                # Append the result as a dictionary to the list
                results.append({'origin': i, 'destination': list_poi_each_stop[count_o], 'length': path_length})       


        if flag:
            all_nonPOI_points.append(origin)

        count_o+=1

    # Create the DataFrame from the list of dictionaries
    results_df = pd.DataFrame(results)
    dist_dfs.append(results_df)

    if len(results_df)>0:
        #getting all the necessary points to avoid more calculation for home locations
        points_for_users.append([user_id,list(set(results_df.destination))])
    else:
        points_for_users.append([])

    if len(all_nonPOI_points)>0:
        all_nonPOI_points = pd.concat(all_nonPOI_points, axis=1).T

        all_nonPOI_points = gpd.GeoDataFrame(all_nonPOI_points, geometry='geometry')
        all_nonPOI_points.set_crs("EPSG:4326", inplace=True)


    #computing the pois distance to home locations

    dist_home_dfs = []

    lat, lon = home_location[1], home_location[0]

    point = Point(lat, lon)

    # Create a GeoDataFrame with the point
    origin_gdf = gpd.GeoDataFrame(geometry=[point])

    origin_gdf.set_crs(main_crs, inplace=True)

    # Reshape the coordinate arrays
    coords_origin = np.column_stack((origin_gdf.geometry.x, origin_gdf.geometry.y))
    coords_destination = np.column_stack((destination_gdf_projected.geometry.x, destination_gdf_projected.geometry.y))

    # Calculate distances using cdist()
    distances = cdist(coords_origin, coords_destination)

    # add the distances to the dataframe
    destination_gdf['distance'] = distances[0]

    # Group the DataFrame by amenity and find the index of the row with the minimum distance
    closest_rows = destination_gdf.groupby('amenity')['distance'].idxmin()

    # Get the closest rows
    points_for_users_adjusted_temp = destination_gdf.loc[closest_rows]

    points_for_users_adjusted = list(points_for_users_adjusted_temp.index)

    origin_gdf.to_crs("EPSG:4326", inplace=True)

    # Create a DataFrame with scalar values
    df_temp = pd.DataFrame({'lat': [origin_gdf.geometry.y], 'lon': [origin_gdf.geometry.x]})

    results = []

    if len(points_for_users_adjusted) != 0:

        # Get the node IDs using the DataFrame
        origin_nodes = net.get_node_ids(df_temp['lat'], df_temp['lon']).values

        # points that are closest
        dests_nodes = net.get_node_ids(destination_gdf['geometry'].loc[points_for_users_adjusted].x, destination_gdf['geometry'].loc[points_for_users_adjusted].y).values

        points_for_user = points_for_users[0]

        if len(points_for_user)>0:
            dests_nodes1 = net.get_node_ids(destination_gdf['geometry'].loc[points_for_user[1]].x, destination_gdf['geometry'].loc[points_for_user[1]].y).values
            dests_nodes = np.concatenate((dests_nodes, dests_nodes1))
            points_for_users_adjusted = points_for_users_adjusted + points_for_user[1]


        for count, j in enumerate(dests_nodes):
            # Get the nearest nodes in the graph for the origin and destination points
            origin_node = origin_nodes[0]
            destination_node = j

            # Calculate the shortest path length using Pandana
            path_length = net.shortest_path_length(origin_node, destination_node)

            # Append the result as a dictionary to the list
            results.append({'origin': user_id, 'destination': points_for_users_adjusted[count], 'length': path_length})

    # Create the DataFrame from the list of dictionaries
    dist_home_df = pd.DataFrame(results)

    if work_location != -1: 
        #computing the pois distance to work locations
    
        dist_home_dfs = []
    
        lat, lon = work_location[1], work_location[0]
    
        point = Point(lat, lon)
    
        # Create a GeoDataFrame with the point
        origin_gdf = gpd.GeoDataFrame(geometry=[point])
    
        origin_gdf.set_crs(main_crs, inplace=True)
    
        # Reshape the coordinate arrays
        coords_origin = np.column_stack((origin_gdf.geometry.x, origin_gdf.geometry.y))
        coords_destination = np.column_stack((destination_gdf_projected.geometry.x, destination_gdf_projected.geometry.y))
    
        # Calculate distances using cdist()
        distances = cdist(coords_origin, coords_destination)
    
        # add the distances to the dataframe
        destination_gdf['distance'] = distances[0]
    
        # Group the DataFrame by amenity and find the index of the row with the minimum distance
        closest_rows = destination_gdf.groupby('amenity')['distance'].idxmin()
    
        # Get the closest rows
        points_for_users_adjusted_temp = destination_gdf.loc[closest_rows]
    
        points_for_users_adjusted = list(points_for_users_adjusted_temp.index)
    
        origin_gdf.to_crs("EPSG:4326", inplace=True)
    
        # Create a DataFrame with scalar values
        df_temp = pd.DataFrame({'lat': [origin_gdf.geometry.y], 'lon': [origin_gdf.geometry.x]})
    
        results = []
    
        if len(points_for_users_adjusted) != 0:
    
            # Get the node IDs using the DataFrame
            origin_nodes = net.get_node_ids(df_temp['lat'], df_temp['lon']).values
    
            # points that are closest
            dests_nodes = net.get_node_ids(destination_gdf['geometry'].loc[points_for_users_adjusted].x, destination_gdf['geometry'].loc[points_for_users_adjusted].y).values
    
            points_for_user = points_for_users[0]
    
            if len(points_for_user)>0:
                dests_nodes1 = net.get_node_ids(destination_gdf['geometry'].loc[points_for_user[1]].x, destination_gdf['geometry'].loc[points_for_user[1]].y).values
                dests_nodes = np.concatenate((dests_nodes, dests_nodes1))
                points_for_users_adjusted = points_for_users_adjusted + points_for_user[1]
    
    
            for count, j in enumerate(dests_nodes):
                # Get the nearest nodes in the graph for the origin and destination points
                origin_node = origin_nodes[0]
                destination_node = j
    
                # Calculate the shortest path length using Pandana
                path_length = net.shortest_path_length(origin_node, destination_node)
    
                # Append the result as a dictionary to the list
                results.append({'origin': user_id, 'destination': points_for_users_adjusted[count], 'length': path_length})
    
        # Create the DataFrame from the list of dictionaries
        dist_work_df = pd.DataFrame(results)


    #computing the non-pois stop points distance to home locations
    all_nonPOI_points['distance_to_home'] = [np.nan]*len(all_nonPOI_points)


    lat, lon = home_location[1], home_location[0]

    point = Point(lat, lon)

    # Create a DataFrame with scalar values and provide an index
    df_temp = pd.DataFrame({'lat': [lat], 'lon': [lon]})

    # Get the node IDs using the DataFrame
    origin_nodes = net.get_node_ids(df_temp['lat'], df_temp['lon']).values

    temp_dest_gdf = all_nonPOI_points

    results = []
    if len(temp_dest_gdf) != 0:

        dests_nodes = net.get_node_ids(temp_dest_gdf['geometry'].x, temp_dest_gdf['geometry'].y).values

        for count, j in enumerate(dests_nodes):
            # Get the nearest nodes in the graph for the origin and destination points
            origin_node = origin_nodes[0]
            destination_node = j

            # Calculate the shortest path length using Pandana
            path_length = net.shortest_path_length(origin_node, destination_node)

            # Append the result as a dictionary to the list
            results.append(path_length)

        all_nonPOI_points.distance_to_home[list(temp_dest_gdf.index)] = results

    if work_location != -1: 
        #computing the non-pois stop points distance to work locations
        all_nonPOI_points['distance_to_work'] = [np.nan]*len(all_nonPOI_points)

        lat, lon = work_location[1], work_location[0]
    
        point = Point(lat, lon)
    
        # Create a DataFrame with scalar values and provide an index
        df_temp = pd.DataFrame({'lat': [lat], 'lon': [lon]})
    
        # Get the node IDs using the DataFrame
        origin_nodes = net.get_node_ids(df_temp['lat'], df_temp['lon']).values
    
        temp_dest_gdf = all_nonPOI_points
    
        results = []
        if len(temp_dest_gdf) != 0:
    
            dests_nodes = net.get_node_ids(temp_dest_gdf['geometry'].x, temp_dest_gdf['geometry'].y).values
    
            for count, j in enumerate(dests_nodes):
                # Get the nearest nodes in the graph for the origin and destination points
                origin_node = origin_nodes[0]
                destination_node = j
    
                # Calculate the shortest path length using Pandana
                path_length = net.shortest_path_length(origin_node, destination_node)
    
                # Append the result as a dictionary to the list
                results.append(path_length)
    
            all_nonPOI_points.distance_to_work[list(temp_dest_gdf.index)] = results

    
    
    if work_location == -1:
        #main section to compute the mobility localness

        #just to have the same analogy for the rest of the code we still call it rank_

        all_nonPOI_points['rank_'] = 1-(all_nonPOI_points['distance_to_home']/nonPoiMaxDistance)
        all_nonPOI_points['rank_'] = all_nonPOI_points['rank_'].apply(lambda x: x if x > 0 else 0)

        # Create a dict for amenities and home for using as denominator
        dicts_keys = set(destination_gdf.amenity)

        amenity_dict = {value: destination_gdf[destination_gdf.amenity==value].index for value in dicts_keys}

        users_localness = []

        results_df = dist_dfs[user_id]
        results_df_home = dist_home_df

        try:

            origin_gdf = stop_points

            results_df = results_df.reset_index()

            if len(origin_gdf)==1:
                users_localness.append(1)
            else:
                # Create a dictionary with values as keys and initialize them with zeros
                home_dict = {value: np.nan for value in dicts_keys}

                for i in home_dict:
                    dict_temp = results_df_home[results_df_home.destination.isin(amenity_dict[i])]
                    if len(dict_temp)>0:
                        home_dict[i] = dict_temp.length.sort_values().iloc[0]

                # for each stop points
                stop_point_dist_mean = []
                list_points_included = []
                length_pois_ = []

                if len(results_df)>0:
    
                    for i, origin in origin_gdf.iterrows():
    
                        length_pois = results_df[results_df.origin==i].length
    
                        if len(length_pois)>0:
    
                            index_poi = results_df.loc[length_pois.idxmin()].destination
                            type_pois = destination_gdf.loc[index_poi].amenity
    
                            length_pois_ = results_df_home[results_df_home.destination==index_poi]
    
                            if len(length_pois_)>0:
    
                                # actual localness for each stop point
                                stop_point_dist_temp = 0
    
                                try:
                                    dist_to_home = length_pois_.length.values[0]
                                    if dist_to_home == 0:
                                        stop_point_dist_temp = 1
                                    else:
                                        stop_point_dist_temp = home_dict[type_pois]/dist_to_home
    
                                    list_points_included.append(i)
    
                                except:
                                    pass
                                #the mean values of localness for all pois around the stop point (we change it but still we kept the name)
                                stop_point_dist_mean.append(stop_point_dist_temp)
    
                    #adding dwell time to the stops
                    poi_points_dwell_time = origin_gdf['t'][list_points_included]/origin_gdf['t'].sum()
    
                    temp_point_for_user = all_nonPOI_points
                    temp_point_for_user['n_dwell_time'] = temp_point_for_user['t']/origin_gdf['t'].sum()
    
    
                    if len(list_points_included)>0:
                        users_localness.append((stop_point_dist_mean*poi_points_dwell_time).sum() + (temp_point_for_user.rank_*temp_point_for_user['n_dwell_time']).sum())
                    else:
                        users_localness.append(1)
                else:
                    temp_point_for_user = all_nonPOI_points
                    temp_point_for_user['n_dwell_time'] = temp_point_for_user['t']/origin_gdf['t'].sum()  
        
                    users_localness.append((temp_point_for_user.rank_*temp_point_for_user['n_dwell_time']).sum())
    
    
        except:
            print('There is an unexpected error')
            users_localness.append((user_id,np.nan))
        
            
        
        return users_localness[0]
    
    else:
        

        #main section to compute the mobility localness

        users_localness = []
        
        all_nonPOI_points['dist_to_both_min'] = np.minimum(all_nonPOI_points['distance_to_home'], all_nonPOI_points['distance_to_work'])


        #just to have the same analogy for the rest of the code we still call it rank_
        all_nonPOI_points['rank_'] = 1-all_nonPOI_points['dist_to_both_min']/nonPoiMaxDistance
        all_nonPOI_points['rank_'] = all_nonPOI_points['rank_'] = all_nonPOI_points['rank_'].apply(lambda x: x if x > 0 else 0)


        # Create a dict for amenities and home for using as denominator
        dicts_keys = set(destination_gdf.amenity)

        amenity_dict = {value: destination_gdf[destination_gdf.amenity==value].index for value in dicts_keys}

        results_df_work = dist_work_df
        results_df = dist_dfs[user_id]
        
        results_df_home = dist_home_df
        try:
            origin_gdf = stop_points
            
            if len(origin_gdf)==1:
                users_localness.append(1)
            else:

                # Create a dictionary with values as keys and initialize them with zeros
                home_dict = {value: np.nan for value in dicts_keys}

                for i in home_dict:
                    dict_temp = results_df_home[results_df_home.destination.isin(amenity_dict[i])]
                    if len(dict_temp)>0:
                        home_dict[i] = dict_temp.length.sort_values().iloc[0]

                # Create a dictionary with values as keys and initialize them with zeros
                work_dict = {value: np.nan for value in dicts_keys}

                if len(results_df_work)>0:
                    for i in work_dict:
                        dict_temp = results_df_work[results_df_work.destination.isin(amenity_dict[i])]
                        if len(dict_temp)>0:
                            work_dict[i] = dict_temp.length.sort_values().iloc[0]
                # for each stop points
                stop_point_dist_mean = []
                list_points_included = []
                length_pois_w = []
                length_pois_h = []

                if len(results_df)>0:
                    
                    for i, origin in origin_gdf.iterrows():
                        
                        length_pois = results_df[results_df.origin==i].length
    
                        if len(length_pois)>0:
                            index_poi = results_df.loc[length_pois.idxmin()].destination
                            type_pois = destination_gdf.loc[index_poi].amenity
    
                            length_pois_h = results_df_home[results_df_home.destination==index_poi]
                            if len(results_df_work)>0:
                                length_pois_w = results_df_work[results_df_work.destination==index_poi]
    
                            # actual localness for each stop point
                            stop_point_dist_temp = 0
                            try:
                                flag_w = 0
                                if len(length_pois_h)>0:
                                    dist_to_home_work = length_pois_h.length.values[0] #we assessing home first
    
                                    if len(results_df_work)>0 and len(length_pois_w)>0:
                                        dist_to_work = length_pois_w.length.values[0]
                                    else:
                                        dist_to_work = dist_to_home_work+1 #just to be bigger than that for the next condition
    
                                    if dist_to_work < dist_to_home_work:#we compare and if work was less then work distance will be done we consider
                                        dist_to_home_work = dist_to_work
                                        flag_w = 1
                                else:
                                    if len(results_df_work)>0 and len(length_pois_w)>0:
                                        dist_to_home_work = length_pois_w.length.values[0]
                                        flag_w = 1
                                    else:
                                        pass
    
                                if dist_to_home_work == 0:
                                    stop_point_dist_temp = 1
                                else:
                                    if flag_w == 0:
                                        stop_point_dist_temp = (home_dict[type_pois]/dist_to_home_work)
                                    else:
                                        stop_point_dist_temp = (work_dict[type_pois]/dist_to_home_work)
    
                                list_points_included.append(i)
    
                            except:
                                pass

                            stop_point_dist_mean.append(stop_point_dist_temp)
    
                    poi_points_dwell_time = origin_gdf['t'][list_points_included]/origin_gdf['t'].sum()
    
                    temp_point_for_user = all_nonPOI_points
                    temp_point_for_user['n_dwell_time'] = temp_point_for_user['t']/origin_gdf['t'].sum()  
    
    
                    if len(list_points_included)>0:
                        users_localness.append((stop_point_dist_mean*poi_points_dwell_time).sum() + (temp_point_for_user.rank_*temp_point_for_user['n_dwell_time']).sum())
                    else:
                        users_localness.append(1)
                else:
                    temp_point_for_user = all_nonPOI_points
                    temp_point_for_user['n_dwell_time'] = temp_point_for_user['t']/origin_gdf['t'].sum()  
    
                    users_localness.append((temp_point_for_user.rank_*temp_point_for_user['n_dwell_time']).sum())
    
        except:
            print('There is an unexpected error')
            users_localness.append(np.nan)
        
        return users_localness[0]
