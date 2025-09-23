"""
Some examples of how to query the scraped data
Basically showing you how to get your data back out after scraping
"""

import sqlite3
import duckdb
import pandas as pd

def query_sqlite_data(company_name="TCS"):
    """Let's see what's in our SQLite database"""
    print(f"=== Checking out the SQLite data for {company_name} ===")
    
    db_path = f"data/databases/{company_name}_tables.db"
    
    try:
        conn = sqlite3.connect(db_path)
        
        # First, let's see what tables we have
        print("Here's what tables are available:")
        metadata_df = pd.read_sql_query("SELECT * FROM tables_metadata", conn)
        print(metadata_df)
        print()
        
        # Now let's peek at each table
        for _, row in metadata_df.iterrows():
            table_name = row['table_name']
            print(f"Sample data from {table_name}:")
            
            # Just grab a few rows to see what's there
            sample_df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5", conn)
            print(sample_df)
            print()
            
            # And check out the column structure
            table_info = pd.read_sql_query(f"PRAGMA table_info({table_name})", conn)
            print(f"Columns in {table_name}:")
            print(table_info[['name', 'type']])
            print("-" * 50)
        
        conn.close()
        
    except Exception as e:
        print(f"Oops, something went wrong with SQLite: {e}")

def query_duckdb_data(company_name="TCS"):
    """Time to check out the DuckDB database - this one's faster for analytics"""
    print(f"=== Diving into DuckDB data for {company_name} ===")
    
    db_path = f"data/databases/{company_name}_tables.duckdb"
    
    try:
        conn = duckdb.connect(db_path)
        
        # Let's see what tables DuckDB has for us
        print("What's available in DuckDB:")
        metadata_df = conn.execute("SELECT * FROM tables_metadata").fetchdf()
        print(metadata_df)
        print()
        
        # Browse through each table
        for _, row in metadata_df.iterrows():
            table_name = row['table_name']
            print(f"Peeking at {table_name}:")
            
            # Quick sample of the data
            sample_df = conn.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchdf()
            print(sample_df)
            print()
            
            # Check the structure
            schema_df = conn.execute(f"DESCRIBE {table_name}").fetchdf()
            print(f"Schema for {table_name}:")
            print(schema_df)
            print("-" * 50)
        
        conn.close()
        
    except Exception as e:
        print(f"DuckDB gave us some trouble: {e}")

def advanced_queries(company_name="TCS"):
    """Some fancier queries to show what you can do with the data"""
    print(f"=== Getting fancy with {company_name} data ===")
    
    # Let's try some more interesting SQLite stuff
    print("SQLite - doing some detective work:")
    try:
        db_path = f"data/databases/{company_name}_tables.db"
        conn = sqlite3.connect(db_path)
        
        # Let's analyze what kind of data we're dealing with
        tables = pd.read_sql_query("SELECT table_name FROM tables_metadata", conn)
        
        for table_name in tables['table_name']:
            print(f"\nStatistics for {table_name}:")
            try:
                # Basic info about the table structure
                columns_df = pd.read_sql_query(f"PRAGMA table_info({table_name})", conn)
                print(f"  Total columns: {len(columns_df)}")
                
                # How much data do we have?
                count_df = pd.read_sql_query(f"SELECT COUNT(*) as row_count FROM {table_name}", conn)
                print(f"  Total rows: {count_df['row_count'].iloc[0]}")
                
            except Exception as e:
                print(f"  Error analyzing {table_name}: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"SQLite got cranky: {e}")
    
    # Now let's see what DuckDB can tell us
    print("\nDuckDB - time for some analytics:")
    try:
        db_path = f"data/databases/{company_name}_tables.duckdb"
        conn = duckdb.connect(db_path)
        
        # DuckDB is great for this kind of analysis
        tables = conn.execute("SELECT table_name FROM tables_metadata").fetchdf()
        
        for table_name in tables['table_name']:
            print(f"\nAnalysis for {table_name}:")
            try:
                # Get detailed statistics
                stats_query = f"""
                SELECT 
                    column_name,
                    data_type,
                    COUNT(*) as total_rows,
                    COUNT(column_name) as non_null_rows,
                    COUNT(*) - COUNT(column_name) as null_rows
                FROM (
                    SELECT * FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                ) cols
                CROSS JOIN {table_name}
                GROUP BY column_name, data_type
                """
                
                # Basic stats that are actually useful
                basic_info = conn.execute(f"SELECT COUNT(*) as total_rows FROM {table_name}").fetchdf()
                print(f"  Total rows: {basic_info['total_rows'].iloc[0]}")
                
                # What types of data are we working with?
                describe_df = conn.execute(f"DESCRIBE {table_name}").fetchdf()
                print(f"  Columns: {len(describe_df)}")
                print("  Column types:", describe_df['column_type'].value_counts().to_dict())
                
            except Exception as e:
                print(f"  Error analyzing {table_name}: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"DuckDB didn't like that: {e}")

def read_csv_data(company_name="TCS"):
    """Sometimes you just want to work with good old CSV files"""
    print(f"=== Checking out the CSV files for {company_name} ===")
    
    try:
        # Let's start with the summary to see what we've got
        summary_df = pd.read_csv(f"data/csv/{company_name}_tables_summary.csv")
        print("Here's what CSV files we created:")
        print(summary_df)
        print()
        
        # Now let's peek into each file
        for _, row in summary_df.iterrows():
            filename = f"data/csv/{row['filename']}"
            print(f"Taking a look at {filename}:")
            
            df = pd.read_csv(filename)
            print(f"  Size: {df.shape[0]} rows, {df.shape[1]} columns")
            print(f"  Columns: {list(df.columns)}")
            print("  Here's a taste of the data:")
            print(df.head(3))
            print("-" * 50)
            
    except Exception as e:
        print(f"CSV reading hit a snag: {e}")

if __name__ == "__main__":
    # Let's check out all the different ways to access our data
    query_sqlite_data("TCS")
    print("\n" + "="*80 + "\n")
    
    query_duckdb_data("TCS")
    print("\n" + "="*80 + "\n")
    
    advanced_queries("TCS")
    print("\n" + "="*80 + "\n")
    
    read_csv_data("TCS")
