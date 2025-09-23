import requests
import bs4
import pandas as pd
import numpy as np
import sqlite3
import duckdb
import os
import warnings
from datetime import datetime

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
        """Cleaning up the messy data that websites usually throw at us"""
        # Getting rid of completely useless empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Column names from websites are usually a disaster, so let's fix them
        df.columns = [str(col).strip().replace('\n', ' ').replace('\r', '') for col in df.columns]
        
        # Replace NaN with empty strings because databases hate NaN values
        df = df.fillna('')
        
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
        """SQLite time - perfect for when I need to run some SQL queries"""
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
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                print(f"✓ Saved table {table_index} to SQLite as '{table_name}'")
            
            # Adding some metadata because future me will thank present me for this
            metadata = []
            for table_info in self.tables:
                metadata.append({
                    'table_name': f"{self.company_name}_table_{table_info['index']}",
                    'table_index': table_info['index'],
                    'rows': table_info['row_count'],
                    'columns': table_info['column_count'],
                    'created_at': datetime.now().isoformat()
                })
            
            metadata_df = pd.DataFrame(metadata)
            metadata_df.to_sql('tables_metadata', conn, if_exists='replace', index=False)
            
            conn.close()
            print(f"✓ SQLite database saved to {db_path}")
            return True
            
        except Exception as e:
            print(f"✗ Error saving to SQLite: {e}")
            return False
    
    def save_to_duckdb(self):
        """DuckDB is like SQLite but way faster for analytics - love this thing"""
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
                conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
                print(f"✓ Saved table {table_index} to DuckDB as '{table_name}'")
            
            # Same metadata setup as SQLite, keeping things consistent
            metadata = []
            for table_info in self.tables:
                metadata.append({
                    'table_name': f"{self.company_name}_table_{table_info['index']}",
                    'table_index': table_info['index'],
                    'rows': table_info['row_count'],
                    'columns': table_info['column_count'],
                    'created_at': datetime.now().isoformat()
                })
            
            metadata_df = pd.DataFrame(metadata)
            conn.execute("CREATE OR REPLACE TABLE tables_metadata AS SELECT * FROM metadata_df")
            
            conn.close()
            print(f"✓ DuckDB database saved to {db_path}")
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