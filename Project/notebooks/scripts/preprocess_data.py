import os
import pandas as pd
from typing import Dict

DATA_DIR = os.path.join("..", "data")
WB_PATHS = [
    "gdp_per_capita/gdp_per_capita_data.csv",
    "health_per_capita/health_per_capita_data.csv"
]
WHO_PATHS = [
    "physical_activity/NCD_PAC.csv",
    "physical_activity/NCD_PAA.csv",
    "alcohol_consumption/alcohol.csv",
    "mortality/NCD_UNDER70.csv",
    "mortality/WHS2_131.csv"
]

def process_WB_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Processes World Bank data into a unified format"""
    
    columns_to_drop = ['Country Name', 'Indicator Name', 'Unnamed: 69']
    updated_df = df.drop(columns_to_drop, axis=1)
    
    # to align with WHO data column names
    new_column_names = {
        'Indicator Code': 'IndicatorCode', 
        'Country Code': 'SpatialDim'
    }
    updated_df.rename(new_column_names, axis=1, inplace=True)
    
    # change dataframe structure so it is the same as WHO data
    updated_df = updated_df.melt(
        id_vars=['IndicatorCode', 'SpatialDim'],      # fixed columns
        var_name='TimeDim',                           # new column containing the old column names (the years)
        value_name='NumericValue'                     # new column containing the values
    )

    # convert from string
    updated_df['TimeDim'] = updated_df['TimeDim'].astype(int)
    
    return updated_df

def drop_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drops a lot of columns, only used for WHO data"""
    
    columns_to_delete = ['Unnamed: 0', 'Id', 'SpatialDimType', 
       'ParentLocationCode', 'TimeDimType', 'ParentLocation', 'Dim1Type',
       'Dim1', 'Dim2Type', 'Dim2', 'Dim3Type', 'Dim3',
       'DataSourceDimType', 'DataSourceDim', 'Value', 'Low', 'High',
       'Comments', 'Date', 'TimeDimensionValue', 'TimeDimensionBegin',
       'TimeDimensionEnd']
    updated_df = df.drop(columns_to_delete, axis=1)
    
    return updated_df

def merge_dataframes(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Merges dataframes listed in a dataframe dictionary"""
    dataframes = list(dfs.values())
    merged_df = pd.concat(
        dataframes,
        ignore_index=True
    )

    print("Merged dataframe:")
    print('  # of rows:   ', merged_df.shape[0])
    print('  # of columns:', merged_df.shape[1])
    return merged_df

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and returns a new dataframe"""
    df_copy = df.copy()
    original_row_num = df_copy.shape[0]

    df_copy = df_copy.drop_duplicates()
    duplicates_dropped = original_row_num - df_copy.shape[0]

    df_copy = df_copy.dropna()
    na_values_dropped = original_row_num - duplicates_dropped - df_copy.shape[0]

    print("Cleaning info:")
    print('  Original # of rows:     ', original_row_num)
    print('  Duplicate rows dropped: ', duplicates_dropped)
    print('  Na values dropped:      ', na_values_dropped)
    print('  New # of rows:          ', df_copy.shape[0])
    return df_copy

def process_data(WB_paths: list[str] = WB_PATHS, WHO_paths: list[str] = WHO_PATHS) -> pd.DataFrame:
    dfs = {}
    
    ## 1. Process data
    # process World Bank data
    print("Loading World Bank data...")
    for path in WB_PATHS:
        path = os.path.join(DATA_DIR, path)
        df = pd.read_csv(path, skiprows=4)
        
        df_key_name = path.split("/")[-1].split(".")[0]
        dfs[df_key_name] = process_WB_dataframe(df)
        print(f"  > {df_key_name} - Done")
    
    
    # process WHO data
    print("Loading WHO data...")
    for path in WHO_PATHS:
        path = os.path.join(DATA_DIR, path)
        df = pd.read_csv(path)
        
        df_key_name = path.split("/")[-1].split(".")[0]
        dfs[df_key_name] = drop_columns(df)
        print(f"  > {df_key_name} - Done")
        
    print("Dataframes processed:", list(dfs.keys()))
    
    ## 2. Merge dataframes
    merged_df = merge_dataframes(dfs)
    
    # rename some of the columns for readability
    merged_df.rename(
        {
            'IndicatorCode': 'Indicator',
            'SpatialDim': 'Country',
            'TimeDim': 'Year',
            'NumericValue': 'Value'
        },
        axis=1,
        inplace=True
    )
    
    ## 3. Clean data
    merged_df = clean_dataframe(merged_df)
    
    ## 4. Group by indicators and countries
    grouped_df = merged_df.groupby(['Indicator', 'Country', 'Year'])
    # list of all unique indicators and countries
    unique_indicators = merged_df['Indicator'].unique()
    unique_countries = merged_df['Country'].unique()

    print("Unique Indicators:")
    print(unique_indicators)
    print("\nUnique Countries:")
    print(unique_countries)
    
    ## 5. Outlier detection
    # Based on "data_preprocess.ipynb" there isn't really any outlier, therefore I didn't include the code for now
    
    ## 6. Aggregated multiple datapoints
    # It seems there are mutliple datapoints in a year for a group of (Indicator, Country)
    print("Indicators and the minimum number of datapoints for a country and year pair.")
    number_of_datapoints = grouped_df.count()\
        .groupby(['Indicator', 'Country']).min()\
        .groupby('Indicator').min()
    print(number_of_datapoints.to_string())
    print("A higher than 1 value could suggest that the indicator is an estimate!")
    
    # Take the mean of the datapoints
    merged_df['Value'] = grouped_df['Value'].transform('mean')

    return merged_df
