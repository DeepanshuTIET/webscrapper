import requests
import bs4
import pandas as pd
import numpy as np
import sqlite3
import duckdb
import os
import warnings
import re
from datetime import datetime
from dateutil import parser as date_parser

# I hate those annoying pandas warnings, so let's just ignore them
warnings.filterwarnings("ignore")

class WebScraperToStorage:
    def __init__(self, url, company_name="TCS"):
        self.url = url
        self.company_name = company_name
        self.html_content = None
        self.tables = []
        
        # Setting up the folder structure - basically organizing everything neatly
        os.makedirs("data", exist_ok=True)
        os.makedirs("data/csv", exist_ok=True)
        os.makedirs("data/databases", exist_ok=True)
    
    def detect_data_type(self, series):
        """
        Intelligent data type detection for a pandas Series
        Returns the best detected type and conversion function
        """
        # Remove empty strings and NaN values for analysis
        clean_series = series.dropna()
        clean_series = clean_series[clean_series.astype(str).str.strip() != '']
        
        if len(clean_series) == 0:
            return 'object', None
        
        # Convert to string for pattern matching
        str_series = clean_series.astype(str).str.strip()
        
        # Check for boolean values first (highest priority for obvious cases)
        if self._is_boolean_series(str_series):
            return 'bool', self._convert_to_boolean
        
        # Check for percentage values
        if self._is_percentage_series(str_series):
            return 'float64', self._convert_percentage_to_float
        
        # Check for currency values  
        if self._is_currency_series(str_series):
            return 'float64', self._convert_currency_to_float
        
        # Check for numeric values (integers and floats)
        numeric_type = self._detect_numeric_type(str_series)
        if numeric_type:
            return numeric_type, self._convert_to_numeric
        
        # Check for date/datetime values
        if self._is_date_series(str_series):
            return 'datetime64[ns]', self._convert_to_datetime
        
        # Default to object (string) type
        return 'object', None
    
    def _is_boolean_series(self, str_series):
        """Check if series contains boolean values"""
        boolean_patterns = {
            'true', 'false', 'yes', 'no', 'y', 'n', 
            '1', '0', 'on', 'off', 'enabled', 'disabled'
        }
        
        # Check if at least 80% of non-empty values match boolean patterns
        total_values = len(str_series)
        if total_values == 0:
            return False
            
        boolean_matches = str_series.str.lower().isin(boolean_patterns).sum()
        return (boolean_matches / total_values) >= 0.8
    
    def _is_percentage_series(self, str_series):
        """Check if series contains percentage values"""
        # Pattern for percentage: number followed by %
        percentage_pattern = r'^-?\d*\.?\d+\s*%$'
        
        total_values = len(str_series)
        if total_values == 0:
            return False
            
        percentage_matches = str_series.str.match(percentage_pattern, na=False).sum()
        return (percentage_matches / total_values) >= 0.7
    
    def _is_currency_series(self, str_series):
        """Check if series contains currency values"""
        # Patterns for various currency formats
        currency_patterns = [
            r'^[\$₹€£¥][\d,]+\.?\d*$',  # Symbol before number
            r'^[\d,]+\.?\d*[\$₹€£¥]$',  # Symbol after number
            r'^\$?-?[\d,]+\.?\d*$',      # Optional $ sign with negative support
            r'^INR\s*[\d,]+\.?\d*$',     # INR prefix
            r'^USD\s*[\d,]+\.?\d*$'      # USD prefix
        ]
        
        total_values = len(str_series)
        if total_values == 0:
            return False
        
        currency_matches = 0
        for pattern in currency_patterns:
            currency_matches += str_series.str.match(pattern, na=False).sum()
        
        return (currency_matches / total_values) >= 0.7
    
    def _detect_numeric_type(self, str_series):
        """Detect if series is numeric and return appropriate type"""
        # Remove common thousands separators and handle negative signs
        cleaned_series = str_series.str.replace(',', '').str.replace(' ', '')
        
        # Pattern for numeric values (int or float)
        numeric_pattern = r'^-?\d*\.?\d+$'
        
        total_values = len(cleaned_series)
        if total_values == 0:
            return None
            
        numeric_matches = cleaned_series.str.match(numeric_pattern, na=False).sum()
        
        if (numeric_matches / total_values) >= 0.8:
            # Check if all numeric values are integers
            try:
                # Try to convert to numeric
                numeric_values = pd.to_numeric(cleaned_series, errors='coerce')
                numeric_values = numeric_values.dropna()
                
                if len(numeric_values) > 0:
                    # Check if all values are integers
                    if all(val == int(val) for val in numeric_values):
                        return 'int64'
                    else:
                        return 'float64'
            except:
                pass
        
        return None
    
    def _is_date_series(self, str_series):
        """Check if series contains date/datetime values"""
        total_values = len(str_series)
        if total_values == 0:
            return False
        
        # Common date patterns
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',          # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',          # MM/DD/YYYY or DD/MM/YYYY
            r'\d{2}-\d{2}-\d{4}',          # MM-DD-YYYY or DD-MM-YYYY
            r'\w{3}\s+\d{4}',              # Jan 2024
            r'\w{3}\s+\d{2},?\s+\d{4}',    # Jan 15, 2024
            r'\d{2}\s+\w{3}\s+\d{4}'       # 15 Jan 2024
        ]
        
        pattern_matches = 0
        for pattern in date_patterns:
            pattern_matches += str_series.str.contains(pattern, na=False, regex=True).sum()
        
        # Also try to parse a sample using dateutil
        successful_parses = 0
        sample_size = min(10, total_values)
        sample_series = str_series.head(sample_size)
        
        for value in sample_series:
            try:
                date_parser.parse(value, fuzzy=False)
                successful_parses += 1
            except:
                continue
        
        # Consider it a date series if pattern matching or parsing shows high success rate
        pattern_success_rate = pattern_matches / total_values
        parse_success_rate = successful_parses / sample_size if sample_size > 0 else 0
        
        return pattern_success_rate >= 0.6 or parse_success_rate >= 0.7
    
    def _convert_to_boolean(self, series):
        """Convert series to boolean type"""
        def convert_value(val):
            if pd.isna(val) or val == '':
                return None
            
            val_str = str(val).lower().strip()
            true_values = {'true', 'yes', 'y', '1', 'on', 'enabled'}
            false_values = {'false', 'no', 'n', '0', 'off', 'disabled'}
            
            if val_str in true_values:
                return True
            elif val_str in false_values:
                return False
            else:
                return None
        
        return series.apply(convert_value)
    
    def _convert_percentage_to_float(self, series):
        """Convert percentage strings to float values"""
        def convert_value(val):
            if pd.isna(val) or val == '':
                return None
            
            try:
                # Remove % sign and convert to float, then divide by 100
                val_str = str(val).replace('%', '').strip()
                return float(val_str) / 100.0
            except:
                return None
        
        return series.apply(convert_value)
    
    def _convert_currency_to_float(self, series):
        """Convert currency strings to float values"""
        def convert_value(val):
            if pd.isna(val) or val == '':
                return None
            
            try:
                # Remove currency symbols and common formatting
                val_str = str(val)
                # Remove currency symbols
                val_str = re.sub(r'[₹$€£¥]', '', val_str)
                # Remove currency codes  
                val_str = re.sub(r'\b(INR|USD|EUR|GBP|JPY)\s*', '', val_str)
                # Remove commas and spaces
                val_str = val_str.replace(',', '').replace(' ', '').strip()
                
                return float(val_str)
            except:
                return None
        
        return series.apply(convert_value)
    
    def _convert_to_numeric(self, series):
        """Convert series to numeric type (int or float)"""
        def convert_value(val):
            if pd.isna(val) or val == '':
                return None
            
            try:
                # Remove common formatting
                val_str = str(val).replace(',', '').replace(' ', '').strip()
                
                # Try integer first
                if '.' not in val_str:
                    return int(val_str)
                else:
                    return float(val_str)
            except:
                return None
        
        return series.apply(convert_value)
    
    def _convert_to_datetime(self, series):
        """Convert series to datetime type"""
        def convert_value(val):
            if pd.isna(val) or val == '':
                return None
            
            try:
                return date_parser.parse(str(val))
            except:
                return None
        
        return series.apply(convert_value)
    
    def apply_data_type_conversion(self, df):
        """Apply intelligent data type conversion to entire DataFrame"""
        converted_df = df.copy()
        conversion_log = []
        
        for column in df.columns:
            try:
                original_type = str(df[column].dtype)
                detected_type, conversion_func = self.detect_data_type(df[column])
                
                if conversion_func is not None:
                    converted_series = conversion_func(df[column])
                    # Only apply conversion if it was mostly successful
                    non_null_original = df[column].dropna().astype(str).str.strip()
                    non_null_original = non_null_original[non_null_original != '']
                    non_null_converted = converted_series.dropna()
                    
                    if len(non_null_converted) >= len(non_null_original) * 0.7:  # 70% success rate
                        converted_df[column] = converted_series
                        if detected_type in ['int64', 'float64'] and converted_df[column].isna().all():
                            # If all values failed to convert, keep as object
                            converted_df[column] = df[column]
                            detected_type = 'object'
                        else:
                            converted_df[column] = converted_df[column].astype(detected_type, errors='ignore')
                        
                        conversion_log.append({
                            'column': column,
                            'original_type': original_type,
                            'detected_type': detected_type,
                            'conversion_success': True
                        })
                    else:
                        conversion_log.append({
                            'column': column,
                            'original_type': original_type,
                            'detected_type': detected_type,
                            'conversion_success': False
                        })
                else:
                    conversion_log.append({
                        'column': column,
                        'original_type': original_type,
                        'detected_type': detected_type,
                        'conversion_success': False
                    })
                    
            except Exception as e:
                print(f"  Warning: Error converting column '{column}': {e}")
                conversion_log.append({
                    'column': column,
                    'original_type': str(df[column].dtype),
                    'detected_type': 'object',
                    'conversion_success': False
                })
        
        # Print conversion summary
        successful_conversions = [log for log in conversion_log if log['conversion_success']]
        if successful_conversions:
            print(f"  ✓ Successfully converted {len(successful_conversions)} columns:")
            for log in successful_conversions:
                print(f"    - {log['column']}: {log['original_type']} → {log['detected_type']}")
        
        return converted_df
    
    def get_sql_data_type(self, pandas_dtype):
        """Convert pandas data type to appropriate SQL data type"""
        dtype_str = str(pandas_dtype)
        
        if 'int' in dtype_str:
            return 'INTEGER'
        elif 'float' in dtype_str:
            return 'REAL'
        elif 'bool' in dtype_str:
            return 'BOOLEAN'
        elif 'datetime' in dtype_str:
            return 'DATETIME'
        else:
            return 'TEXT'
    
    def create_table_with_proper_types(self, conn, table_name, df, db_type='sqlite'):
        """Create table with proper column types based on DataFrame dtypes"""
        # Build CREATE TABLE statement with proper types
        columns_def = []
        
        for column in df.columns:
            # Clean column name for SQL compatibility
            clean_col_name = re.sub(r'[^\w]', '_', str(column))
            sql_type = self.get_sql_data_type(df[column].dtype)
            columns_def.append(f'"{clean_col_name}" {sql_type}')
        
        columns_sql = ', '.join(columns_def)
        create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({columns_sql})'
        
        try:
            if db_type == 'sqlite':
                conn.execute(create_sql)
            else:  # duckdb
                conn.execute(create_sql)
            
            # Prepare DataFrame for insertion (handle column name mapping)
            df_for_insert = df.copy()
            df_for_insert.columns = [re.sub(r'[^\w]', '_', str(col)) for col in df_for_insert.columns]
            
            return df_for_insert
        except Exception as e:
            print(f"  Warning: Error creating table with proper types: {e}")
            return df  # Return original DataFrame as fallback
    
    def fetch_html(self):
        """Just grabbing the HTML from whatever website we're targeting"""
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            self.html_content = response.text
            
            # Saving the raw HTML too, just in case I need to debug something later
            with open(f"data/{self.company_name}.html", "w", encoding="utf-8") as f:
                f.write(self.html_content)
            
            print(f"✓ Successfully fetched HTML from {self.url}")
            return True
        except Exception as e:
            print(f"✗ Error fetching HTML: {e}")
            return False
    
    def extract_tables(self):
        """This is where the magic happens - finding all the tables in the HTML"""
        if not self.html_content:
            print("✗ No HTML content found. Please fetch HTML first.")
            return False
        
        try:
            soup = bs4.BeautifulSoup(self.html_content, 'html.parser')
            
            # Let's hunt for all the tables on this page
            html_tables = soup.find_all('table')
            
            if not html_tables:
                print("✗ No tables found in the HTML content")
                return False
            
            print(f"✓ Found {len(html_tables)} tables in the HTML")
            
            # Now converting each table into something useful (pandas DataFrames)
            self.tables = []
            for i, table in enumerate(html_tables):
                try:
                    # pandas has this neat function that does most of the heavy lifting
                    df_list = pd.read_html(str(table))
                    if df_list:
                        df = df_list[0]
                        # Need to clean up the mess that websites usually give us
                        df = self.clean_dataframe(df)
                        if not df.empty:
                            table_info = {
                                'index': i,
                                'dataframe': df,
                                'row_count': len(df),
                                'column_count': len(df.columns)
                            }
                            self.tables.append(table_info)
                            print(f"  Table {i}: {len(df)} rows, {len(df.columns)} columns")
                except Exception as e:
                    print(f"  ✗ Error processing table {i}: {e}")
                    # Some tables are just broken, so we'll skip them and move on
                    continue
            
            print(f"✓ Successfully extracted {len(self.tables)} valid tables")
            return True
            
        except Exception as e:
            print(f"✗ Error extracting tables: {e}")
            return False
    
    def clean_dataframe(self, df):
        """
        Cleaning up the messy data that websites usually throw at us
        Now with intelligent data type detection and conversion!
        """
        print(f"  🧹 Cleaning DataFrame with {len(df)} rows and {len(df.columns)} columns")
        
        # Getting rid of completely useless empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Column names from websites are usually a disaster, so let's fix them
        df.columns = [str(col).strip().replace('\n', ' ').replace('\r', '') for col in df.columns]
        
        # Replace NaN with empty strings for initial processing
        df = df.fillna('')
        
        # Apply intelligent data type conversion
        print(f"  🔍 Detecting and converting data types...")
        df = self.apply_data_type_conversion(df)
        
        print(f"  ✓ DataFrame cleaned and types converted")
        return df
    
    def save_to_csv(self):
        """Saving everything as CSV files - the universal format everyone loves"""
        if not self.tables:
            print("✗ No tables to save. Please extract tables first.")
            return False
        
        try:
            for table_info in self.tables:
                table_index = table_info['index']
                df = table_info['dataframe']
                
                filename = f"data/csv/{self.company_name}_table_{table_index}.csv"
                df.to_csv(filename, index=False, encoding='utf-8')
                print(f"✓ Saved table {table_index} to {filename}")
            
            # Creating a handy summary file so I don't have to remember what's what
            summary_data = []
            for table_info in self.tables:
                summary_data.append({
                    'table_index': table_info['index'],
                    'rows': table_info['row_count'],
                    'columns': table_info['column_count'],
                    'filename': f"{self.company_name}_table_{table_info['index']}.csv"
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv(f"data/csv/{self.company_name}_tables_summary.csv", index=False)
            print(f"✓ Created summary file: {self.company_name}_tables_summary.csv")
            
            return True
        except Exception as e:
            print(f"✗ Error saving to CSV: {e}")
            return False
    
    def save_to_sqlite(self):
        """SQLite time - perfect for when I need to run some SQL queries with proper data types"""
        if not self.tables:
            print("✗ No tables to save. Please extract tables first.")
            return False
        
        try:
            db_path = f"data/databases/{self.company_name}_tables.db"
            conn = sqlite3.connect(db_path)
            
            for table_info in self.tables:
                table_index = table_info['index']
                df = table_info['dataframe']
                
                table_name = f"{self.company_name}_table_{table_index}"
                
                # Create table with proper column types
                df_for_insert = self.create_table_with_proper_types(conn, table_name, df, 'sqlite')
                
                # Insert data with proper type handling
                try:
                    # Drop table first to recreate with proper schema
                    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                    
                    # Create and populate table with proper types
                    df_for_insert = self.create_table_with_proper_types(conn, table_name, df, 'sqlite')
                    df_for_insert.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
                    
                    print(f"✓ Saved table {table_index} to SQLite as '{table_name}' with proper data types")
                    
                    # Print column types for verification
                    cursor = conn.execute(f"PRAGMA table_info({table_name})")
                    columns_info = cursor.fetchall()
                    print(f"  📊 Column types: {[(col[1], col[2]) for col in columns_info]}")
                    
                except Exception as e:
                    # Fallback to old method if new method fails
                    print(f"  ⚠️  Falling back to default types for table {table_index}: {e}")
                    df.to_sql(table_name, conn, if_exists='replace', index=False)
                    print(f"✓ Saved table {table_index} to SQLite as '{table_name}' (default types)")
            
            # Adding some metadata because future me will thank present me for this
            metadata = []
            for table_info in self.tables:
                # Get column type information
                table_name = f"{self.company_name}_table_{table_info['index']}"
                try:
                    cursor = conn.execute(f"PRAGMA table_info({table_name})")
                    columns_info = cursor.fetchall()
                    column_types = {col[1]: col[2] for col in columns_info}
                except:
                    column_types = {}
                
                metadata.append({
                    'table_name': table_name,
                    'table_index': table_info['index'],
                    'rows': table_info['row_count'],
                    'columns': table_info['column_count'],
                    'column_types': str(column_types),
                    'created_at': datetime.now().isoformat()
                })
            
            metadata_df = pd.DataFrame(metadata)
            metadata_df.to_sql('tables_metadata', conn, if_exists='replace', index=False)
            
            conn.close()
            print(f"✓ SQLite database saved to {db_path} with enhanced data types")
            return True
            
        except Exception as e:
            print(f"✗ Error saving to SQLite: {e}")
            return False
    
    def save_to_duckdb(self):
        """DuckDB is like SQLite but way faster for analytics - now with proper data types!"""
        if not self.tables:
            print("✗ No tables to save. Please extract tables first.")
            return False
        
        try:
            db_path = f"data/databases/{self.company_name}_tables.duckdb"
            conn = duckdb.connect(db_path)
            
            for table_info in self.tables:
                table_index = table_info['index']
                df = table_info['dataframe']
                
                table_name = f"{self.company_name}_table_{table_index}"
                
                try:
                    # DuckDB automatically infers types from pandas DataFrames
                    # But we'll make sure column names are SQL-friendly
                    df_for_insert = df.copy()
                    df_for_insert.columns = [re.sub(r'[^\w]', '_', str(col)) for col in df_for_insert.columns]
                    
                    conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df_for_insert")
                    print(f"✓ Saved table {table_index} to DuckDB as '{table_name}' with proper data types")
                    
                    # Print column types for verification
                    schema_info = conn.execute(f"DESCRIBE {table_name}").fetchdf()
                    print(f"  📊 Column types: {list(zip(schema_info['column_name'], schema_info['column_type']))}")
                    
                except Exception as e:
                    # Fallback method
                    print(f"  ⚠️  Falling back to basic method for table {table_index}: {e}")
                    conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
                    print(f"✓ Saved table {table_index} to DuckDB as '{table_name}' (basic method)")
            
            # Enhanced metadata with column type information
            metadata = []
            for table_info in self.tables:
                table_name = f"{self.company_name}_table_{table_info['index']}"
                
                try:
                    # Get column type information from DuckDB
                    schema_info = conn.execute(f"DESCRIBE {table_name}").fetchdf()
                    column_types = dict(zip(schema_info['column_name'], schema_info['column_type']))
                except:
                    column_types = {}
                
                metadata.append({
                    'table_name': table_name,
                    'table_index': table_info['index'],
                    'rows': table_info['row_count'],
                    'columns': table_info['column_count'],
                    'column_types': str(column_types),
                    'created_at': datetime.now().isoformat()
                })
            
            metadata_df = pd.DataFrame(metadata)
            conn.execute("CREATE OR REPLACE TABLE tables_metadata AS SELECT * FROM metadata_df")
            
            conn.close()
            print(f"✓ DuckDB database saved to {db_path} with enhanced data types")
            return True
            
        except Exception as e:
            print(f"✗ Error saving to DuckDB: {e}")
            return False
    
    def run_complete_pipeline(self):
        """This runs everything in one go - from scraping to storing in all formats"""
        print("=== Web Scraper to Multiple Storage Formats ===")
        print(f"Target URL: {self.url}")
        print(f"Company: {self.company_name}")
        print()
        
        # First, let's grab the HTML from the website
        if not self.fetch_html():
            return False
        
        # Then extract all the tables we can find
        if not self.extract_tables():
            return False
        
        print("\n=== Saving to Multiple Formats ===")
        
        # Now save everything in different formats for maximum flexibility
        self.save_to_csv()     # For Excel lovers
        self.save_to_sqlite()  # For SQL enthusiasts  
        self.save_to_duckdb()  # For data science folks
        
        print("\n=== Pipeline Complete ===")
        print(f"✓ Total tables processed: {len(self.tables)}")
        print("✓ Data saved in formats: CSV, SQLite, DuckDB")
        print("✓ Files located in 'data/' directory")
        
        return True

# Let's test this thing with TCS data
if __name__ == "__main__":
    url = "https://www.screener.in/company/TCS/consolidated/"
    scraper = WebScraperToStorage(url, "TCS")
    scraper.run_complete_pipeline()