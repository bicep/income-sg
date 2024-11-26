import pandas as pd
from utils import idw_interpolation, prepare_coordinates

def interpolate_property_prices_to_population_density_grid():
    # Load data
    pop_density_file = "./processed/population_density.csv"
    hdb_file = "./processed/hdb_property_prices.csv"
    private_file = "./processed/private_property_prices.csv"
    output_file = "./processed/interpolated_combined.csv"

    population_density = pd.read_csv(pop_density_file)
    hdb_prices = pd.read_csv(hdb_file)
    private_prices = pd.read_csv(private_file)

    hdb_data = prepare_coordinates(hdb_prices, 'latitude', 'longitude', 'mean_price_per_sqm')
    private_data = prepare_coordinates(private_prices, 'latitude', 'longitude', 'mean_price_per_sqm')

    # Combine datasets
    combined_data = pd.concat([hdb_data, private_data], ignore_index=True)

    # Population density grid coordinates
    pop_coords = population_density[['latitude', 'longitude']].values

    # Interpolate combined prices
    population_density['combined_price'] = idw_interpolation(combined_data, pop_coords)

    # Save results
    population_density.to_csv(output_file, index=False)

    print(f"Interpolation completed. Results saved to '{output_file}'.")