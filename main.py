from estimate_income import *
from interpolate_property_data import *
from process_property_data import *
from process_income_data import *

if __name__ == "__main__":
    process_hdb_property_prices()
    process_private_property_prices()
    # optional: combine_property_prices_dataset()
    process_income_to_cumulative()
    interpolate_property_prices_to_population_density_grid()
    # estimated_income.csv dataset
    estimate_income()