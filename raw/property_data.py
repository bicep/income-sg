import json
import os
import pandas as pd
import requests
from pyproj import Transformer
from raw.constants import ONEMAP_SEARCH_BASE_URL
from raw.utils import calculate_distance

def calculate_hdb_resale_prices(input_csv):
    """
    Filters unique addresses and calculates the median and mean price per square meter.

    Args:
        input_csv (str): Path to the input CSV file containing resale data.
        output_csv (str): Path to save the cleaned data.

    Returns:
        DataFrame: Processed DataFrame with unique addresses and calculated statistics.
    """
    # Load the data
    data = pd.read_csv(input_csv)
    
    # Create full address column
    data["full_address"] = data["block"] + " " + data["street_name"]
    
    # Calculate price per square meter
    data["price_per_sqm"] = data["resale_price"] / data["floor_area_sqm"]
    
    # Filter unique addresses and calculate median and mean price per square meter
    unique_data = data.groupby("full_address").agg(
        median_price_per_sqm=("price_per_sqm", "median"),
        mean_price_per_sqm=("price_per_sqm", "mean")
    ).reset_index()
    
    # Add the housing_type column
    unique_data["housing_type"] = "public"

        # Initialize latitude and longitude columns
    unique_data["latitude"] = None
    unique_data["longitude"] = None
    
    for index, row in unique_data.iterrows():
        params = {
            "searchVal": row["full_address"],
            "returnGeom": "Y",
            "getAddrDetails": "Y",
        }
        response = requests.get(ONEMAP_SEARCH_BASE_URL, params=params)
        
        # Check response status
        if response.status_code != 200:
            print(f"Failed to fetch data for address: {row['full_address']}")
            print(f"Status Code: {response.status_code}, Response: {response.text}")
            continue
        
        data = response.json()

        result = None
        
        # Check the number of results found
        if data["found"] == 0:
            print(f"No data found for address: {row['full_address']}")
            continue
        elif data["found"] == 1:
            result = data["results"][0]
        else:
            print(f"Multiple entries found for address: {row['full_address']}. Using the second result (tends to be residential).")
            result = data["results"][1]
        
        # Populate latitude and longitude
        unique_data.at[index, "latitude"] = result["LATITUDE"]
        unique_data.at[index, "longitude"] = result["LONGITUDE"]
    
    # Save the processed data to a new CSV
    unique_data.to_csv("./raw/hdb_property_prices.csv", index=False)

def calculate_and_save_private_property_prices():
    """
    Calculate the mean and median price per square meter for each project,
    append street name for "LANDED HOUSING DEVELOPMENT" projects,
    fetch full addresses using the OneMap API (pick the closest entry if multiple found),
    and save the results to a CSV file.
    """
    directory = './raw'  # Hardcoded directory path
    output_file = "./raw/private_property_prices.csv"  # Output file name

    results = []

    # Specific filenames to process
    filenames = [f"private_property_prices_raw_{i}.json" for i in range(1, 5)]

    # Initialize a transformer for coordinate conversion
    transformer = Transformer.from_crs("EPSG:3414", "EPSG:4326", always_xy=True)  # Assuming Singapore CRS (EPSG:3414) to WGS84

    # Iterate through the specified files in the directory
    for filename in filenames:
        filepath = os.path.join(directory, filename)
        if os.path.exists(filepath):
            try:
                # Attempt to read the file with UTF-8 encoding
                with open(filepath, 'r', encoding='utf-8') as file:
                    data = json.load(file)
            except UnicodeDecodeError:
                # Retry with 'latin-1' encoding if UTF-8 fails
                with open(filepath, 'r', encoding='latin-1') as file:
                    data = json.load(file)

            # Process the data for each file
            for property_data in data['Result']:
                project_name = property_data.get('project', 'Unknown')
                street = property_data.get('street', 'Unknown')

                # Modify project name for "LANDED HOUSING DEVELOPMENT"
                if "LANDED HOUSING DEVELOPMENT" in project_name.upper():
                    project_name = f"{project_name} in {street}"

                transactions = property_data.get('transaction', [])
                prices_per_sqm = [
                    float(t['price']) / float(t['area'])
                    for t in transactions
                    if t.get('price') and t.get('area')
                ]

                # Original coordinates
                x = property_data.get('x')
                y = property_data.get('y')
                lat, lon = None, None
                if x and y:
                    lat, lon = transformer.transform(x, y)
                else:
                    # Skip if no coordinates
                    continue

                # Fetch the full address from OneMap API
                address = project_name  # Default to project name
                params = {
                    "searchVal": project_name,
                    "returnGeom": "Y",
                    "getAddrDetails": "Y",
                }
                response = requests.get(ONEMAP_SEARCH_BASE_URL, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if data["found"] > 0:
                        if data["found"] == 1:
                            # Only one result, use its address
                            address = data["results"][0].get("ADDRESS")
                        else:
                            # Multiple results, pick the closest based on x/y
                            closest_result = None
                            min_distance = float("inf")
                            for result in data["results"]:
                                result_x = float(result.get("X", 0))
                                result_y = float(result.get("Y", 0))
                                distance = calculate_distance(float(x), float(y), result_x, result_y)
                                if distance < min_distance:
                                    min_distance = distance
                                    closest_result = result

                            if closest_result:
                                address = closest_result.get("ADDRESS")

                if prices_per_sqm:
                    results.append({
                        'project_name': project_name,
                        'full_address': address,
                        'median_price_per_sqm': pd.Series(prices_per_sqm).median(),
                        'mean_price_per_sqm': sum(prices_per_sqm) / len(prices_per_sqm),
                        'housing_type': 'private',
                        'latitude': lat,
                        'longitude': lon,
                    })

    # Convert results to a DataFrame
    df = pd.DataFrame(results)

    # Save the results to a CSV file
    df.to_csv(output_file, index=False)

    print(f"The analysis has been saved to '{output_file}'.")

