from math import sqrt
import os
import pandas as pd
import geopandas as gpd
import numpy as np
from scipy.spatial import cKDTree

def calculate_distance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two points."""
    return sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

def assign_planning_area_and_subzone(df, 
                                     planning_area_geojson='./raw/planning_area.geojson', 
                                     subzone_geojson='./raw/subzone.geojson'):
    """
    Assigns planning area and subzone information to a property dataset based on latitude and longitude.
    Replaces the original CSV file with the enriched version.

    Parameters:
        df (pd.Dataframe): Dataframe
        planning_area_geojson (str): Path to the GeoJSON file containing planning area geometries. Default is './raw/planning_area.geojson'.
        subzone_geojson (str): Path to the GeoJSON file containing subzone geometries. Default is './raw/subzone.geojson'.

    Returns:
        pd.DataFrame: A DataFrame enriched with planning area and subzone information.
    """

    # Load GeoJSON files as GeoDataFrames
    planning_areas_gdf = gpd.read_file(planning_area_geojson).rename(columns={'name': 'planning_area'})
    subzones_gdf = gpd.read_file(subzone_geojson).rename(columns={'name': 'subzone'})

    # Create point geometries for properties
    properties_gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df['longitude'], df['latitude']),
        crs='EPSG:4326'
    )

    # Spatial join to find planning areas
    properties_gdf = gpd.sjoin(properties_gdf, planning_areas_gdf[['planning_area', 'geometry']], 
                               how='left', predicate='intersects').drop(columns=['index_right'])

    # Spatial join to find subzones
    properties_gdf = gpd.sjoin(properties_gdf, subzones_gdf[['subzone', 'geometry']], 
                               how='left', predicate='intersects').drop(columns=['index_right'])

    # Drop unnecessary columns
    enriched_df = properties_gdf.dropna(subset=['planning_area', 'subzone']).drop(columns=['geometry'])

    return enriched_df

def prepare_coordinates(data, lat_col, lon_col, value_col):
    return data[[lat_col, lon_col, value_col]].dropna().rename(columns={
        lat_col: 'lat',
        lon_col: 'lon',
        value_col: 'value'
    })

# Interpolation function using Inverse Distance Weighting (IDW)
def idw_interpolation(source_data, target_coords, power=2):
    """
    Perform IDW interpolation.
    :param source_data: DataFrame with 'lat', 'lon', 'value'
    :param target_coords: Array of target coordinates [[lat, lon], ...]
    :param power: Power parameter for IDW
    :return: Interpolated values for target_coords
    """
    source_coords = source_data[['lat', 'lon']].values
    source_values = source_data['value'].values

    # Create KDTree for efficient nearest-neighbor lookup
    tree = cKDTree(source_coords)

    # Query distances and indices of nearest neighbors
    distances, indices = tree.query(target_coords, k=30)

    # Apply IDW formula
    weights = 1 / (distances**power + 1e-10)  # Avoid division by zero
    interpolated_values = np.sum(weights * source_values[indices], axis=1) / np.sum(weights, axis=1)

    return interpolated_values

# Standardize planning area names
def standardize_names(df, column_name):
    df[column_name] = df[column_name].str.strip().str.lower()
    return df