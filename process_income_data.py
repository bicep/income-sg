import pandas as pd

def process_income_to_cumulative():
    """
    Process the income data by summing 'No_Working_Person' into '0_1000',
    dropping 'No_Working_Person', and calculating cumulative probabilities
    for each income range within each planning area.

    Returns:
    - pd.DataFrame: The processed DataFrame with cumulative probabilities.
    """
    # Load the dataset
    income_data = pd.read_csv("./raw/income.csv")
    
    # Convert all columns except 'planning_Area' to numeric, forcing errors to NaN
    for column in income_data.columns:
        if column != 'planning_Area':
            income_data[column] = pd.to_numeric(income_data[column], errors='coerce')

    # Fill NaN values with 0 for calculations (if applicable)
    income_data.fillna(0, inplace=True)

    # Sum the 'No_Working_Person' column into the '0_1000' column and drop 'No_Working_Person'
    if 'No_Working_Person' in income_data.columns:
        income_data['0_1000'] += income_data['No_Working_Person']
        income_data.drop(columns=['No_Working_Person'], inplace=True)

    # Identify the income columns (excluding 'planning_Area' and 'Total')
    income_columns = [col for col in income_data.columns if col not in ['planning_Area', 'Total']]
    
    # Calculate probabilities by dividing each income bracket by the total
    income_data[income_columns] = income_data[income_columns].div(income_data['Total'], axis=0)
    
    # Drop the 'Total' column as it's no longer needed
    income_data.drop(columns=['Total'], inplace=True)

    # Calculate the cumulative probabilities across the income columns for each row
    income_data[income_columns] = income_data[income_columns].cumsum(axis=1)

    # Ensure that the cumulative probabilities for "20k and over" round off to 1
    for i, _ in income_data.iterrows():
        last_col = income_columns[-1]  # Assume the last column is "20k and over"
        income_data.loc[i, last_col] = 1.0  # Explicitly set the final value to 1


    # Save the modified dataset to a new file
    income_data.to_csv("processed/cumulative_income.csv", index=False)

    return income_data
