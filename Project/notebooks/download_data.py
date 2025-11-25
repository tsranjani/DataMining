import requests
import zipfile
import io
import os
from typing import List
import pandas as pd

data_dir = 'data/'
world_bank_data_dicts = [
    {
        'name': 'GDP per capita',
        'output_dir': 'gdp_per_capita',
        'url': 'https://api.worldbank.org/v2/en/indicator/NY.GDP.PCAP.CD?downloadformat=csv'
    },
    {
        'name': 'Health expenditure per capita',
        'output_dir': 'health_per_capita',
        'url': 'https://api.worldbank.org/v2/en/indicator/SH.XPD.CHEX.PC.CD?downloadformat=csv'
    }
]
who_data_dicts = [
    {
        'name': 'NCD_PAC WHO indicator',
        'file_name': 'NCD_PAC',
        'output_dir': 'physical_activity',
        'indicator_name': 'NCD_PAC',
    },
    {
        'name': 'NCD_PAA WHO indicator',
        'file_name': 'NCD_PAA',
        'output_dir': 'physical_activity',
        'indicator_name': 'NCD_PAA',
    },
    {
        'name': 'SA_0000001400 WHO indicator',
        'file_name': 'SA_0000001400',
        'output_dir': 'alcohol_consumption',
        'indicator_name': 'SA_0000001400',
    },
    {
        'name': 'SDGTOBACCO WHO indicator',
        'file_name': 'SDGTOBACCO',
        'output_dir': 'tobacco_consumption',
        'indicator_name': 'SDGTOBACCO',
    },
    {
        'name': 'M_Est_tob_daily_crude WHO indicator',
        'file_name': 'M_Est_tob_daily_crude',
        'output_dir': 'tobacco_consumption',
        'indicator_name': 'M_Est_tob_daily_crude',
    },
    {
        'name': 'UHC_NCD_NONELEVBP WHO indicator',
        'file_name': 'UHC_NCD_NONELEVBP',
        'output_dir': 'blood_pressure',
        'indicator_name': 'UHC_NCD_NONELEVBP',
    },    
    {
        'name': 'EQ_OVERWEIGHTADULT WHO indicator',
        'file_name': 'EQ_OVERWEIGHTADULT',
        'output_dir': 'obesity',
        'indicator_name': 'EQ_OVERWEIGHTADULT',
    },
    {
        'name': 'NCD_UNDER70 WHO indicator',
        'file_name': 'NCD_UNDER70',
        'output_dir': 'mortality',
        'indicator_name': 'NCD_UNDER70',
    },
    {
        'name': 'WHS2_131 WHO indicator',
        'file_name': 'WHS2_131',
        'output_dir': 'mortality',
        'indicator_name': 'WHS2_131',
    }
]

def download_worldbank_data(output_dir: str, download_url: str):
    """Function to download worldbank data

    Args:
        output_dir (str): path to output directory
        download_url (str): download URL that points to download link
    """
    try:
        # request zip
        response = requests.get(download_url)
        response.raise_for_status() # raise an exception for bad status codes (4xx or 5xx)

        # unzip
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            # create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # extract all
            zf.extractall(output_dir)
            
    except requests.exceptions.RequestException as e:
        print(f'An error occurred during download: {e}')
    except zipfile.BadZipFile:
        print('The downloaded file is not a valid ZIP file.')
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
       

def search_for_indicators(search_terms: List[str], negative_search_terms: List[str] = None) -> pd.DataFrame:
    """Function to search for specific indicators

    Args:
        search_terms (List[str]): A list of search terms that are used to filter for indicators
                                  (IndicatorName must contain ALL of these terms).
        negative_search_terms (List[str], optional): A list of terms that, if found in the 
                                                     IndicatorName, will exclude the indicator.
                                                     Defaults to None (no exclusions).

    Returns:
        pd.DataFrame: DataFrame with all the indicators that fit the filters 
    """
    INDICATORS_URL = "https://ghoapi.azureedge.net/api/Indicator"
    
    filtered_df = pd.DataFrame() 

    try:
        # request indicators
        response = requests.get(INDICATORS_URL)
        response.raise_for_status()

        # convert response to dataframe
        indicators_list = response.json().get('value', [])
        df_indicators = pd.DataFrame(indicators_list)

        # filter for POSITIVE search terms (must contain ALL)
        combined_positive_filter = pd.Series([True] * len(df_indicators)) # start with all True
        for term in search_terms:
            # filter for search term (case-insensitive)
            term_filter = df_indicators['IndicatorName'].str.contains(term, case=False, na=False)
            # combine filters (must contain ALL terms)
            combined_positive_filter = combined_positive_filter & term_filter

        # filter for NEGATIVE search terms (must NOT contain ANY)
        combined_negative_filter = pd.Series([False] * len(df_indicators)) # start with all False (i.e., NO terms found)
        if negative_search_terms:
            for term in negative_search_terms:
                # filter for negative term (case-insensitive)
                term_filter = df_indicators['IndicatorName'].str.contains(term, case=False, na=False)
                # combine filters (will be True if ANY negative term is found)
                combined_negative_filter = combined_negative_filter | term_filter 
            
            # final NEGATIVE filter should be the inverse: True where NO negative terms were found
            final_negative_filter = ~combined_negative_filter 
        else:
            # if no negative terms, this filter is all True (i.e., keep all rows)
            final_negative_filter = pd.Series([True] * len(df_indicators))

        # combine both filters (must pass positive AND negative checks)
        final_combined_filter = combined_positive_filter & final_negative_filter
        
        # filter for non-archived indicators
        final_combined_filter = final_combined_filter & ~df_indicators['IndicatorCode'].str.contains('ARCHIVED', case=False, na=False)

        # apply filter
        filtered_df = df_indicators[final_combined_filter]

        # Print message reflecting both types of terms
        positive_terms_str = f"ALL terms [{', '.join(search_terms)}]"
        negative_terms_str = f"AND NOT ANY of [{', '.join(negative_search_terms)}]" if negative_search_terms else ""
        print(f"Indicators containing {positive_terms_str} {negative_terms_str}:")
        print(f"Found {len(filtered_df)} indicators.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return filtered_df
  
def download_who_indicator_data(file_name: str, output_dir: str, download_url: str):
    """Function to download an indicator's data from WHO

    Args:
        file_name (str): filename to use for saving
        output_dir (str): output directory for saved file
        download_url (str): download URL for indicator
    """
    try:
        # request indicator
        response_odata = requests.get(download_url)
        response_odata.raise_for_status()
        
        # convert response to dataframe
        data_json = response_odata.json()
        df_odata = pd.json_normalize(data_json['value'])
        
        if df_odata.empty:
            print(f"\n Warning: Indicator {file_name} returned no data from the API.")
            return 1
        
        # save 
        os.makedirs(output_dir, exist_ok=True)
        df_odata.to_csv(os.path.join(output_dir, file_name+'.csv')) 
    except requests.exceptions.RequestException as e:
        print(f"An OData API error occurred: {e}")
    return 0
   
        
if __name__ == '__main__':  
    # download World Bank data  
    for data_dict in world_bank_data_dicts:
        data_name = data_dict['name']
        data_url = data_dict['url']
        output_dir = os.path.join(data_dir, data_dict['output_dir'])
        
        if os.path.exists(output_dir):
            continue # skip already downloaded
    
        print(f'Downloading {data_name} to {output_dir}... ', end='')
        download_worldbank_data(output_dir, data_url)
        
        # rename
        all_files = os.listdir(output_dir) # needed to get old file name
        old_file_name = [item for item in all_files if item.startswith('API')][0]
        new_file_name = data_dict['output_dir'] + '_data.csv'
        os.rename(os.path.join(output_dir, old_file_name), os.path.join(output_dir, new_file_name))
        
        print('Done')
    
    # download WHO data
    for data_dict in who_data_dicts:
        data_name = data_dict['name']
        indicator = data_dict['indicator_name']
        
        output_dir = os.path.join(data_dir, data_dict['output_dir'])
        file_name = data_dict['file_name']
        
        data_url = f"https://ghoapi.azureedge.net/api/{indicator}"
        
        if os.path.exists(os.path.join(output_dir, file_name+'.csv')):
            continue # skip already downloaded
        
        print(f'Downloading {data_name} to {output_dir}... ', end='')
        failed = download_who_indicator_data(file_name, output_dir, data_url)
        if not failed: print(' Done')
    
    print('All downloads are finished!')