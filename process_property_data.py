import csv
import json
import os
import pandas as pd
import requests
from pyproj import Transformer
from constants import ONEMAP_SEARCH_BASE_URL
from utils import calculate_distance, assign_planning_area_and_subzone

def process_hdb_property_prices():
    """
    Filters unique addresses and calculates the median and mean price per square meter.

    Args:
        input_csv (str): Path to the input CSV file containing resale data.
        output_csv (str): Path to save the cleaned data.

    Returns:
        DataFrame: Processed DataFrame with unique addresses and calculated statistics.
    """
    # Load the data
    data = pd.read_csv("./raw/hdb_property_prices.csv")
    
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
    
    data_with_planning_areas_and_subzones = assign_planning_area_and_subzone(unique_data)
    
    # Save the processed data to a new CSV
    data_with_planning_areas_and_subzones.to_csv("./processed/hdb_property_prices.csv", index=False)

def process_private_property_prices():
    """
    Calculate the mean and median price per square meter for each project,
    append street name for "LANDED HOUSING DEVELOPMENT" projects,
    fetch full addresses using the OneMap API (pick the closest entry if multiple found),
    and save the results to a CSV file.
    """
    directory = './raw'  # Hardcoded directory path
    output_file = "./processed/private_property_prices.csv"  # Output file name

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
                    lon, lat = transformer.transform(x, y)
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

    data_with_planning_areas_and_subzones = assign_planning_area_and_subzone(df)
    
    # Save the processed data to a new CSV
    data_with_planning_areas_and_subzones.to_csv(output_file, index=False)

    print(f"The analysis has been saved to '{output_file}'.")

def process_private_property_temporal_transactions():
    """
    Process and save all transactions from private property JSON files,
    formatting the contractDate as timeData (e.g., 0124 -> 01-24),
    and include address and latitude/longitude logic for each transaction.
    """
    directory = './raw'  # Hardcoded directory path
    output_file = "./processed/private_property_temporal_transactions.csv"  # Output file name

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

                # Original coordinates
                x = property_data.get('x')
                y = property_data.get('y')
                lat, lon = None, None
                if x and y:
                    lon, lat = transformer.transform(x, y)

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

                                                    # Ensure x and y are properly used
                                if x is not None and y is not None:
                                    distance = calculate_distance(float(x), float(y), result_x, result_y)
                                    if distance < min_distance:
                                        min_distance = distance
                                        closest_result = result

                            if closest_result:
                                address = closest_result.get("ADDRESS")

                # Process each transaction
                transactions = property_data.get('transaction', [])
                for transaction in transactions:
                    area = transaction.get('area', None)
                    price = transaction.get('price', None)
                    contract_date = transaction.get('contractDate', None)
                    if contract_date:
                        time_data = f"{contract_date[:2]}-{contract_date[2:]}"  # Convert to "MM-YY" format
                    else:
                        time_data = None

                    results.append({
                        'project_name': project_name,
                        'street': street,
                        'full_address': address,
                        'latitude': lat,
                        'longitude': lon,
                        'area': area,
                        'price': price,
                        'time_data': time_data,
                        'housing_type': 'private',
                        'property_type': transaction.get('propertyType'),
                        'tenure': transaction.get('tenure'),
                        'district': transaction.get('district'),
                        'type_of_sale': transaction.get('typeOfSale'),
                    })

    # Convert results to a DataFrame
    df = pd.DataFrame(results)

    data_with_planning_areas_and_subzones = assign_planning_area_and_subzone(df)
    
    # Save the processed data to a new CSV
    data_with_planning_areas_and_subzones.to_csv(output_file, index=False)

    print(f"The transaction data has been saved to '{output_file}'.")


def combine_property_prices_dataset():
    # Load data
    hdb_file = "./processed/hdb_property_prices.csv"
    private_file = "./processed/private_property_prices.csv"
    output_file = "./processed/combined_property_prices.csv"

    # Load your datasets
    hdb_prices = pd.read_csv(hdb_file)
    private_prices = pd.read_csv(private_file)

    # Find shared columns
    shared_columns = hdb_prices.columns.intersection(private_prices.columns)

    # Keep only shared columns in both DataFrames
    hdb_prices_shared = hdb_prices[shared_columns]
    private_prices_shared = private_prices[shared_columns]

    # Concatenate the DataFrames
    combined_data = pd.concat([hdb_prices_shared, private_prices_shared], ignore_index=True)

    # Save results
    combined_data.to_csv(output_file, index=False)


def process_raw_private_property_prices_to_csv():
    directory = './raw'  # Hardcoded directory path
    output_file = "./processed/private_property_prices_raw.csv"  # Output file name
    results = []

    # Specific filenames to process
    filenames = [f"private_property_prices_raw_{i}.json" for i in range(1, 5)]

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
            for property_data in data.get('Result', []):
                street = property_data.get('street', 'Unknown')
                project_name = property_data.get('project', 'Unknown')

                for transaction in property_data.get('transaction', []):
                    results.append({
                        'street': street,
                        'project_name': project_name,
                        'area': transaction.get('area', 'Unknown'),
                        'floorRange': transaction.get('floorRange', 'Unknown'),
                        'noOfUnits': transaction.get('noOfUnits', 'Unknown'),
                        'contractDate': transaction.get('contractDate', 'Unknown'),
                        'typeOfSale': transaction.get('typeOfSale', 'Unknown'),
                        'price': transaction.get('price', 'Unknown'),
                        'propertyType': transaction.get('propertyType', 'Unknown'),
                        'district': transaction.get('district', 'Unknown'),
                        'typeOfArea': transaction.get('typeOfArea', 'Unknown'),
                        'tenure': transaction.get('tenure', 'Unknown'),
                    })

    # Write results to the output CSV
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'street', 'project_name', 'area', 'floorRange', 'noOfUnits',
            'contractDate', 'typeOfSale', 'price', 'propertyType', 'district',
            'typeOfArea', 'tenure'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return results

def process_property_transactions_with_ids(current_year=2024):
    """
    Processes property transaction data to filter, transform, and save into a new format.

    Args:
        input_file (str): Path to the input CSV file.
        output_file (str): Path to save the processed CSV file.
        current_year (int): The current year for calculating property age.

    Returns:
        pd.DataFrame: The processed DataFrame.
    """
    input_file = "./processed/private_property_temporal_transactions.csv"
    output_file = "./processed/private_property_prices_id.csv"

    # Load the data into a pandas DataFrame
    df = pd.read_csv(input_file)

    # Filter out rows with 'Freehold' tenure (these will have 'unknown' building age)
    df = df[df['tenure'].str.contains("lease commencing from")]

    # Calculate property age for leasehold properties
    df['property_age'] = df['tenure'].str.extract(r'(\d{4})').astype(float).apply(lambda x: current_year - x)

    # Add a property_id column for unique properties (group by project_name, street, full_address, latitude, and longitude)
    df['property_id'] = (df['project_name'] + "_" + df['street'] + "_" + df['full_address'] + 
                         "_" + df['latitude'].astype(str) + "_" + df['longitude'].astype(str)).factorize()[0] + 1

    # Add a transaction_id column (unique for each transaction)
    df['transaction_id'] = range(1, len(df) + 1)

    # Rename columns for the output
    df['property_address'] = df['full_address']
    df['transaction_amount'] = df['price']
    df['property_area'] = df['area']

    # Select only the required columns for the new CSV
    output_df = df[['transaction_id', 'property_id', 'property_address', 'latitude', 'longitude', 
                    'property_age', 'property_area', 'transaction_amount']]

    # Save to a new CSV file
    output_df.to_csv(output_file, index=False)

    return output_df


def process_hdb_property_prices_with_id():
    """
    Processes HDB property data to match the private property format, including property_id and transaction_id.

    Returns:
        DataFrame: Processed DataFrame with standardized columns.
    """
    # Load the raw and processed data
    raw_file = "./raw/hdb_property_prices.csv"
    processed_file = "./processed/hdb_property_prices.csv"
    output_file = "./processed/hdb_property_prices_id.csv"
    
    raw_data = pd.read_csv(raw_file)
    processed_data = pd.read_csv(processed_file)

    # Create full address column in raw data
    raw_data["property_address"] = raw_data["block"] + " " + raw_data["street_name"]

    # Merge latitude and longitude by matching full_address with property_address
    merged_data = raw_data.merge(
        processed_data[["full_address", "latitude", "longitude"]],
        how="left",
        left_on="property_address",
        right_on="full_address"
    )

    # Handle unmatched addresses
    unmatched_addresses = merged_data[merged_data["latitude"].isnull()]
    if not unmatched_addresses.empty:
        print("Unmatched addresses found:")
        print(unmatched_addresses["property_address"].unique())
        # Optionally save unmatched addresses for manual handling
        unmatched_addresses.to_csv("./processed/unmatched_addresses.csv", index=False)

    # Calculate property age
    merged_data["property_age"] = 2024 - merged_data["lease_commence_date"]

    # Assign unique property_id for each property (based on address and geolocation)
    merged_data["property_id"] = (
        merged_data["property_address"] + "_" +
        merged_data["latitude"].astype(str) + "_" +
        merged_data["longitude"].astype(str)
    ).factorize()[0] + 1

    # Rename floor_area_sqm to property_area
    merged_data.rename(columns={"floor_area_sqm": "property_area"}, inplace=True)

    # Sort by property_id
    merged_data = merged_data.sort_values(by=["property_id"]).reset_index(drop=True)

    # Add a unique, sequential transaction_id column
    merged_data["transaction_id"] = range(1, len(merged_data) + 1)

    # Select and rename columns for consistency with private property data
    output_df = merged_data[[
        "transaction_id", "property_id", "property_address", "latitude", "longitude", 
        "property_age", "property_area", "resale_price"
    ]].rename(columns={"resale_price": "transaction_amount"})

    # Save the processed data
    output_df.to_csv(output_file, index=False)

    return output_df
