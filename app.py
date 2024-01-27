import pandas as pd
import streamlit as st
from datetime import datetime
from rich.console import Console
from rich.traceback import install
from io import BytesIO

# Install rich traceback
console = Console()
install()

default_date = datetime(2024, 1, 18)
min_date = datetime(2020, 1, 1)
max_date = datetime(2025, 12, 31)

st.title('秒杀价格处理')

input_data = st.file_uploader("Choose a file", type=['csv', 'xlsx'])

selected_date = st.date_input("Select a date", default_date, min_value=min_date, max_value=max_date)

DATE = selected_date.strftime('%Y-%m-%d')

submit_button = st.button("Process File")

if input_data and submit_button:
    
    try: 
    
        input_data = pd.read_excel(input_data, header=[0, 1])
        
        # Get the first two column names
        first_col_name = input_data.columns[0][1] if len(input_data.columns) > 0 else None
        second_col_name = input_data.columns[1][1] if len(input_data.columns) > 1 else None
        
        if first_col_name == 'SKU ' and second_col_name == 'SKU ':
    
            # Drop the first column from '输入1.xlsx'
            input_data = input_data.iloc[:, 1:]

            # Process and adjust the columns of '输入1.xlsx'
            new_columns = []
                    
            for i, col in enumerate(input_data.columns):
                if i < 4:  # The first four columns belong to the 'Main' category
                    new_columns.append(('Main', col[1]))
                else:
                    # Extracting the column name and removing any non-date related text
                    col_name = col[0]
                    if isinstance(col_name, str):
                        # Remove any text like 'Stock' and try converting to datetime
                        col_name = col_name.split()[0]  # Keeping only the date part
                    try:
                        # Convert to datetime and format as 'YYYY-MM-DD'
                        new_date = pd.to_datetime(col_name, dayfirst=True).strftime('%Y-%m-%d')
                        new_columns.append((new_date, col[1]))
                    except:
                        # In case of failure, log the issue for further inspection
                        print(f"Failed to convert column: {col}")

            # Assign the new columns to the DataFrame
            input_data.columns = pd.MultiIndex.from_tuples(new_columns)
            
            # Specifying the date and creating the pivot table
            date_columns = [col for col in input_data.columns if col[0] == DATE]
            main_columns = [col for col in input_data.columns if col[0] == 'Main']
            selected_columns = main_columns + date_columns
            pivot_table = input_data[selected_columns]
            pivot_table = pivot_table[pivot_table[date_columns].any(axis=1)].fillna(0)

            # Creating the output DataFrame based on the pivot table
            mapping = {'SE': 0, 'BMH': 1, 'XF': 2, 'NTH': 3}
            sorted_sub_columns = sorted(['SE', 'NTH', 'BMH', 'XF'], key=lambda x: mapping[x])
            output_data = pd.DataFrame(columns=['*专题ID', '*商品编码', '*活动价', '活动库存', '限购数量', '排序', '*调价原因'])

            # Initialize an empty list to hold DataFrame objects
            dataframe_list = []

            # Loop through each row in the pivot table
            for _, row in pivot_table.iterrows():
                sku = row[('Main', 'SKU ')]
                activity_price = row[('Main', '秒杀')]

                # Create DataFrames for each sub-column and add them to the list
                for sub_col in sorted_sub_columns:
                    # Using .get to handle missing values, defaulting to 0
                    activity_stock = row.get((DATE, sub_col), 0)
                    
                    output_row_df = pd.DataFrame([{
                        '*专题ID': 111,
                        '*商品编码': sku,
                        '*活动价': activity_price,
                        '活动库存': activity_stock,
                        '限购数量': 1,
                        '排序': 999,
                        '*调价原因': '自营活动'
                    }])
                    dataframe_list.append(output_row_df)

            # Concatenate all the DataFrame objects in the list into one DataFrame
            output_data_1 = pd.concat(dataframe_list, ignore_index=True)

            st.write(output_data_1)
            
            output_buffer = BytesIO()
            with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                output_data_1.to_excel(writer, index=False) 
            output_xlsx = output_buffer.getvalue()

            # Provide a download button for the Excel file
            st.download_button(
                label="Download data as Excel",
                data=output_xlsx,
                file_name='输出.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        elif first_col_name == 'SKU ':

            new_columns = []
            for i, col in enumerate(input_data.columns):
                if i < 4:  # The first four columns belong to the 'Main' category
                    new_columns.append(('Main', col[1]))
                else:
                    col_name = col[0]
                    if isinstance(col_name, str):
                        # Keeping only the date part and removing other texts like 'Stock'
                        col_name = col_name.split(' ')[0]
                    try:
                        # Convert to datetime and format as 'YYYY-MM-DD'
                        new_date = pd.to_datetime(col_name).strftime('%Y-%m-%d')
                        new_columns.append((new_date, col[1]))
                    except ValueError as e:
                        print(f"Failed to convert column: {col}, error: {e}")

            # Assign the new column structure to the dataframe
            input_data.columns = pd.MultiIndex.from_tuples(new_columns)

            # Now you can proceed with using the transformed dataframe
            input_data.head()
            # Assign the new columns to the DataFrame
            input_data.columns = pd.MultiIndex.from_tuples(new_columns)

            date_columns = [col for col in input_data.columns if col[0] == DATE]
            main_columns = [col for col in input_data.columns if col[0] == 'Main']
            selected_columns = main_columns + date_columns
            pivot_table = input_data[selected_columns]
            pivot_table = pivot_table[pivot_table[date_columns].any(axis=1)].fillna(0)

            def process_miaosha(value):
                # Define default prices for locations
                default_prices = {'SE': None, 'NTH': None, 'BMH': None, 'XF': None}

                # Location mapping
                location_mapping = {'伦敦': 'SE', 'XF': 'XF', 'SE': 'SE', 'NTH': 'NTH', 'BMH': 'BMH'}

                # Initialize unspecified price
                unspecified_price = None

                try:
                    if isinstance(value, str) and '；' in value:
                        # Split by '；' and process each part
                        parts = value.split('；')
                        for part in parts:
                            part = part.strip()
                            if ' ' in part:
                                loc_name, price = part.split(maxsplit=1)
                                loc_code = location_mapping.get(loc_name, None)
                                if loc_code:
                                    default_prices[loc_code] = float(price)
                                else:
                                    unspecified_price = float(price)
                            else:
                                unspecified_price = float(part)
                        # Apply unspecified price to locations that are None
                        for loc in default_prices:
                            if default_prices[loc] is None and unspecified_price is not None:
                                default_prices[loc] = unspecified_price
                    elif isinstance(value, str):
                        # Handle improperly formatted numbers
                        numeric_part = ''.join(filter(lambda x: x.isdigit() or x == '.', value))
                        # Replace multiple dots with a single one
                        numeric_part = numeric_part.replace("..", ".")
                        price = float(numeric_part)
                        for loc in default_prices:
                            default_prices[loc] = price
                    else:
                        # If value is not a string (e.g., a float or int), use it directly
                        price = float(value) if value is not None else None
                        for loc in default_prices:
                            default_prices[loc] = price

                except ValueError as e:
                    print(f"Error converting price: {e}")

                return default_prices


            # Creating the output DataFrame based on the pivot table
            mapping = {'SE': 0, 'BMH': 1, 'XF': 2, 'NTH': 3}
            sorted_sub_columns = sorted(['SE', 'NTH', 'BMH', 'XF'], key=lambda x: mapping[x])
            output_data = pd.DataFrame(columns=['*专题ID', '*商品编码', '*活动价', '活动库存', '限购数量', '排序', '*调价原因'])

            # Create an empty list to store DataFrames for each row
            dataframe_list = []

            # Function to extract numeric value from the '限购' string
            def extract_numeric_limit(value):
                if isinstance(value, str):
                    # Extract numeric part from the string
                    numeric_part = ''.join(filter(lambda x: x.isdigit(), value))
                    return int(numeric_part) if numeric_part else 1  # Default to 1 if no numeric part found
                return value  # Return as is if it's already a number

            # Loop through each row in the pivot table
            for _, row in pivot_table.iterrows():
                sku = row[('Main', 'SKU ')]
                miaosha_values = process_miaosha(row[('Main', '秒杀')])
                purchase_limit_raw = row[('Main', '限购')]  # Read purchase limit from the pivot table
                purchase_limit = extract_numeric_limit(purchase_limit_raw)  # Extract numeric value

                # Create DataFrames for each sub-column and add them to the list
                for sub_col in sorted_sub_columns:
                    activity_stock_raw = row.get((DATE, sub_col), 0)
                    
                    # Handle special cases for activity stock
                    if activity_stock_raw == '不限量':
                        activity_stock = ''  # Empty string for '不限量'
                    elif activity_stock_raw == '/':
                        activity_stock = 0   # Zero for '/'
                    else:
                        activity_stock = activity_stock_raw

                    activity_price = miaosha_values.get(sub_col, 0)

                    output_row_df = pd.DataFrame([{
                        '*专题ID': 111,
                        '*商品编码': sku,
                        '*活动价': activity_price,
                        '活动库存': activity_stock,
                        '限购数量': purchase_limit,  # Use the extracted numeric purchase limit
                        '排序': 999,
                        '*调价原因': '自营活动'
                    }])
                    dataframe_list.append(output_row_df)

            # Concatenate all row DataFrames to create the final output DataFrame
            output_data_2 = pd.concat(dataframe_list, ignore_index=True)
            
            output_csv = output_data_2.to_csv(index=False).encode('utf-8')
            
            st.write(output_data_2)

            output_buffer = BytesIO()
            with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                output_data_2.to_excel(writer, index=False) 
            output_xlsx = output_buffer.getvalue()

            # Provide a download button for the Excel file
            st.download_button(
                label="Download data as Excel",
                data=output_xlsx,
                file_name='输出.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        else:
            # This is neither Input 1 nor Input 2
            st.write("The file does not match Input 1 or Input 2 format.")
            
    except Exception as e:
        exception_details = f"An error occurred: {e}"
        console.log(exception_details)
        console.print_exception()
        st.error(exception_details)
