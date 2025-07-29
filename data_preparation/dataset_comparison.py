import pandas as pd
from datetime import datetime
import numpy as np





def create_dataframe(filepath):
    return pd.read_csv(filepath)


def convert_time_of_df(df, time_column, start_time=None):
    # If start_time is not provided, use the current time
    if start_time is None:
        start_time = datetime.now()
    # Convert the column of elapsed seconds to float
    df[time_column] = df[time_column].astype(float)        
    
    # Round both start_time and elapsed_time to the nearest second
    start_time = start_time.replace(microsecond=0)
    df[time_column] = df[time_column].apply(lambda x: int(x * 1e6))

    # Calculate the datetime by adding elapsed time to the start time
    df[time_column] = start_time + pd.to_timedelta(df[time_column], unit='microseconds')
    
    # Format the datetime as ISO 8601 
    df[time_column] = df[time_column].dt.strftime('%Y-%m-%d %H:%M:%S.%f')
    
    return df


def harmonize_time(df_original, df_faulty, df_original_name_of_time_column, df_faulty_name_of_time_column, sampling_interval):
    # Ensure timestamps are datetime objects --> requires ISO8601 Format of Time columns in Dataframes, thus conversion function needs to be called first
    df_original[df_original_name_of_time_column] = pd.to_datetime(df_original[df_original_name_of_time_column], format='%Y-%m-%d %H:%M:%S.%f')
    df_faulty[df_faulty_name_of_time_column] = pd.to_datetime(df_faulty[df_faulty_name_of_time_column], format='%Y-%m-%d %H:%M:%S.%f')
    
    # Drop the "index" column if it exists
    if 'index' in df_original.columns:
        df_original.drop(columns=['index'], inplace=True)
    if 'index' in df_faulty.columns:
        df_faulty.drop(columns=['index'], inplace=True) 
    
    # Set timestamps as the index for both dataframes
    df_original.set_index(df_original_name_of_time_column, inplace=True)
    df_faulty.set_index(df_faulty_name_of_time_column, inplace=True)

    # Aggregate duplicates using the mean function for both DataFrames
    df_original = df_original.resample(sampling_interval).mean().interpolate()
    df_faulty = df_faulty.resample(sampling_interval).mean().interpolate()
    
    # Ensure that the faulty DataFrame is adapted to the original DataFrame regarding the time
    #df_faulty = df_faulty.reindex(df_original.index).interpolate()
    
    return df_original, df_faulty


def compare_dataframes(df_original, df_faulty, threshold=0.05):
    residuals_df = pd.DataFrame(index=df_original.index, columns=df_original.columns)
    deviations_df = pd.DataFrame(index=df_original.index, columns=df_original.columns)
    column_r_squared = {}
    #check if df_original and df2 have the same columns
    if df_original.columns.equals(df_faulty.columns):
        # Columns are the same
        pass
    else:
        # check if df_faulty has columns that are not in df_original:
        columns_to_drop = list(set(df_faulty.columns) - set(df_original.columns))
        #print(f"Columns to drop from df_faulty: {columns_to_drop}")
        df_faulty.drop(columns=columns_to_drop, inplace=True)
        
        if df_original.columns.equals(df_faulty.columns):
            pass
        
        else:
            # check if df_original has columns that are not in df_faulty:
            columns_to_drop = list(set(df_original.columns) - set(df_faulty.columns))
            #print(f"Columns to drop from df_original: {columns_to_drop}")
            df_original.drop(columns=columns_to_drop, inplace=True)
            pass

    # check if df1 and df2 have the same row indices
    if df_original.index.equals(df_faulty.index):
        # Rows are the same
        pass
    else:
        # if Rows are different: delete rows that are not in both dataframes
        rows_to_drop = list(set(df_original.index) - set(df_faulty.index))
        #print(f"Rows to drop: {rows_to_drop}")
        #if index is in df_original, then drop the row in df_original
        if rows_to_drop in df_original.index:
            df_original.drop(index=rows_to_drop, inplace=True)
        else:
            #if index is in df_faulty, then drop the row in df_faulty
            df_faulty.drop(index=rows_to_drop, inplace=True)
  
    
    for column in df_original.columns:
        if column != 'time':
            df1_values = df_original[column] # Original
            df2_values = df_faulty[column] # Faulty
            
            # Calculate residuals based on percentage difference over the whole timespan
            # use normalized relative error
            residuals = np.where((df1_values == 0) & (df2_values == 0), 0, (df2_values - df1_values) / np.max(np.abs(df1_values)))
 
            residuals_df[column] = residuals
            
            # Calculate R-squared for the column
            #r_squared = r2_score(df1_values, df2_values)
            #column_r_squared[column] = r_squared

            # Fill deviations DataFrame with zeros and ones based on threshold
            deviations = (np.where(abs(residuals) > threshold, np.sign(df2_values - df1_values), 0))
            deviations_df[column] = deviations.astype(int)
    residuals_df = residuals_df.round(3)        
    # Calculate overall mean R-squared across all columns
    #overall_mean_r_squared = sum(column_r_squared.values()) / len(column_r_squared)
  
    return residuals_df, deviations_df#, overall_mean_r_squared
