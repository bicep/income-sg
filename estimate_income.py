import pandas as pd
import numpy as np

from utils import standardize_names

def estimate_income():
    # Hardcoded file paths
    interpolated_combined_path = "./processed/interpolated_combined.csv"
    cumulative_income_path = "./processed/cumulative_income.csv"
    output_path = "./processed/estimated_income.csv"

    # Load the datasets
    interpolated_combined = pd.read_csv(interpolated_combined_path)
    cumulative_income = pd.read_csv(cumulative_income_path)

    interpolated_combined = standardize_names(interpolated_combined, "planning_area")
    cumulative_income = standardize_names(cumulative_income, "planning_area")

    # Calculate exponential price bins for stratification
    max_price = interpolated_combined['combined_price'].max()
    min_price = interpolated_combined['combined_price'].min()
    num_bins = 10
    bins = np.geomspace(min_price, max_price, num_bins + 1)  # Exponential progression for bins

    interpolated_combined['price_decile'] = np.digitize(
        interpolated_combined['combined_price'], bins, right=False
    ) - 1  # Adjust for 0-based indexing

    # Initialize an empty list to store results
    results = []

    # Get income brackets programmatically
    income_brackets = [col for col in cumulative_income.columns if col not in ['planning_area']]

    # Process each planning area separately
    for planning_area in interpolated_combined['planning_area'].unique():
        # Filter data for the current planning area
        area_data = interpolated_combined[interpolated_combined['planning_area'] == planning_area]
        income_data = cumulative_income[cumulative_income['planning_area'] == planning_area]

        # Handle missing income data
        if income_data.empty:
            print(f"Warning: No income data for planning area '{planning_area}', using 'other' planning area information.")
            
            # Check population density
            if area_data['popDensity'].sum() == 0:
                print(f"Skipping '{planning_area}' due to zero population density.")
                continue

            # Use \"others\" planning area as fallback
            other_income_data = cumulative_income[cumulative_income['planning_area'] == 'others']
            if not other_income_data.empty:
                cumulative_probs = other_income_data[income_brackets].iloc[0].values
            else:
                print(f"No 'other' column found. Skipping '{planning_area}'.")
                continue
        else:
            # Extract cumulative probabilities from income data
            cumulative_probs = income_data[income_brackets].iloc[0].values

        # Assign income levels to each property in the planning area
        for _, row in area_data.iterrows():
            # Skip rows with zero population density
            if row['popDensity'] < 1 or row['subzone'] in [
                'AIRPORT ROAD', 'BENOI SECTOR', 'CENTRAL WATER CATCHMENT', 
                'CHANGI AIRPORT', 'CITY TERMINALS', 'CLEMENTI FOREST', 
                'CONEY ISLAND', 'DEFU INDUSTRIAL PARK', 'JURONG ISLAND', 
                'JURONG ISLAND AND BUKOM', 'JURONG PORT', 'MANDAI WEST', 
                'MARINA CENTRE', 'MARINA EAST', 'MARINA SOUTH', 
                'NORTH-EASTERN ISLANDS', 'PASIR RIS WAFER FAB PARK', 
                'PIONEER SECTOR', 'PORT', 'RESERVOIR VIEW', 
                'SELETAR AEROSPACE PARK', 'SEMBAWANG WHARVES', 
                'SOUTHERN ISLANDS', 'THE WHARVES', 'WESTERN WATER CATCHMENT'
            ]:
                continue

            decile = row['price_decile']

            # Map decile to cumulative probability and find matching income bracket
            decile_prob = (decile + 1) / 10.0
            matching_index = np.searchsorted(cumulative_probs, decile_prob)
            matching_index = min(matching_index, len(income_brackets) - 1)  # Handle edge cases
            income_bracket = income_brackets[matching_index]

            # Parse the lower and upper bounds of the bracket
            if 'and_over' in income_bracket.lower():
                # Adjust lower and upper bounds for deciles >= 7
                if decile == 7:
                    lower_bound, upper_bound = 30000, 80000
                elif decile == 8:
                    lower_bound, upper_bound = 40000, 100000
                elif decile == 9:
                    lower_bound, upper_bound = 50000, 120000
                elif decile == 10:
                    lower_bound, upper_bound = 70000, 150000
                else:
                    lower_bound = int(income_bracket.split('_')[0])
                    upper_bound = lower_bound * 3  # Exaggerated approximation for "and Over"
            elif '_' in income_bracket:
                lower_bound, upper_bound = map(int, income_bracket.split('_'))
            else:
                raise ValueError(f"Unexpected income bracket format: {income_bracket}")

            # Generate a random income within the bracket bounds
            average_income = np.random.uniform(lower_bound, upper_bound)

            # Append the result
            results.append({
                'planning_area': planning_area,
                'subzone': row['subzone'],
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'property_price': row['combined_price'],
                'price_decile': decile,
                'income_bracket': income_bracket,
                'popDensity': row['popDensity'],
                'average_income': average_income
            })

    # Convert results to a DataFrame
    result_df = pd.DataFrame(results)

    # Save to a CSV file
    result_df.to_csv(output_path, index=False)
