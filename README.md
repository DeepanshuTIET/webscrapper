# Web Scraper to Multiple Storage Formats

[![GitHub Repository](https://img.shields.io/badge/GitHub-DeepanshuTIET%2Fwebscrapper-blue?logo=github)](https://github.com/DeepanshuTIET/webscrapper)
[![Python](https://img.shields.io/badge/Python-3.7%2B-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A comprehensive Python web scraper that extracts table data from websites and stores it in multiple formats: **SQLite**, **CSV**, and **DuckDB**.

🔗 **Repository**: [https://github.com/DeepanshuTIET/webscrapper](https://github.com/DeepanshuTIET/webscrapper)

## Features

- 🌐 **Web Scraping**: Extracts HTML tables from any website
- 📊 **Multiple Storage Formats**: 
  - SQLite database for relational queries
  - CSV files for easy data sharing
  - DuckDB for analytics and fast queries
- 🧹 **Data Cleaning**: Automatically cleans and processes table data
- 🎯 **Intelligent Data Type Detection**: Automatically detects and converts data types
  - **Numeric values**: Integers and floats with thousands separators
  - **Currency values**: $, ₹, €, £, ¥ symbols and INR/USD prefixes
  - **Percentage values**: Converts % to decimal format
  - **Date/DateTime**: Various date formats (YYYY-MM-DD, Jan 2023, etc.)
  - **Boolean values**: Yes/No, True/False, Y/N, 1/0, etc.
  - **Proper database schemas**: Uses appropriate column types (INTEGER, REAL, BOOLEAN, DATETIME)
- 📈 **Metadata Tracking**: Keeps track of table statistics, column types, and creation timestamps
- 🔧 **Error Handling**: Robust error handling and logging with fallback to string types
- 📁 **Organized Output**: Creates structured directories for different file types

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/DeepanshuTIET/webscrapper.git
cd webscrapper
```

2. **Install the required dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the scraper:**
```bash
python retriving_html.py
```

## Quick Start

### Basic Usage

```python
from retriving_html import WebScraperToStorage

# Create scraper instance
url = "https://www.screener.in/company/TCS/consolidated/"
scraper = WebScraperToStorage(url, "TCS")

# Run complete pipeline
scraper.run_complete_pipeline()
```

### Advanced Usage

```python
# For more control over the process
scraper = WebScraperToStorage(url, "COMPANY_NAME")

# Step by step execution
if scraper.fetch_html():
    if scraper.extract_tables():
        print(f"Found {len(scraper.tables)} tables")
        
        # Save to specific formats
        scraper.save_to_csv()        # Save as CSV files
        scraper.save_to_sqlite()     # Save to SQLite database
        scraper.save_to_duckdb()     # Save to DuckDB database
        
        # Access extracted data
        for table_info in scraper.tables:
            df = table_info['dataframe']
            print(f"Table has {len(df)} rows and {len(df.columns)} columns")
```

## File Structure

After running the scraper, your files will be organized as:

```
data/
├── csv/
│   ├── COMPANY_table_0.csv
│   ├── COMPANY_table_1.csv
│   └── COMPANY_tables_summary.csv
├── databases/
│   ├── COMPANY_tables.db      (SQLite)
│   └── COMPANY_tables.duckdb  (DuckDB)
└── COMPANY.html              (Raw HTML)
```

## Automatic Data Type Detection

The enhanced web scraper now automatically detects and converts data types, making your scraped data immediately ready for analysis and mathematical operations.

### Supported Data Types

1. **Numeric Values**
   - Integers: `"123"`, `"1,250"`, `"-45"`
   - Floats: `"123.45"`, `"1,250.75"`, `"-45.5"`
   - Handles thousands separators and negative values

2. **Currency Values**
   - Symbol prefixes: `"$1,250.50"`, `"₹50,000"`, `"€1.200,50"`
   - Symbol suffixes: `"1250.50$"`, `"50000₹"`
   - Currency codes: `"USD 1,250.50"`, `"INR 50,000"`

3. **Percentage Values**
   - Standard format: `"15%"`, `"10.5%"`, `"-2.3%"`
   - Converted to decimal: `0.15`, `0.105`, `-0.023`

4. **Date/DateTime Values**
   - ISO format: `"2023-01-15"`, `"2023/01/15"`
   - Month names: `"Jan 2023"`, `"January 15, 2023"`
   - Various separators: `"15-Jan-2023"`, `"15 Jan 2023"`

5. **Boolean Values**
   - Text: `"Yes"/"No"`, `"True"/"False"`, `"Y"/"N"`
   - Numeric: `"1"/"0"`
   - Status: `"On"/"Off"`, `"Enabled"/"Disabled"`

### Before and After Example

```python
# Original scraped data (all strings)
original_data = {
    'Product': ['Product A', 'Product B'],
    'Price': ['$1,250.50', '$850.75'],
    'Discount': ['15%', '10%'],
    'Active': ['Yes', 'No'],
    'Launch_Date': ['Jan 2023', 'Mar 2022']
}

# After automatic conversion
# Price: float64 [1250.50, 850.75]
# Discount: float64 [0.15, 0.10] 
# Active: bool [True, False]
# Launch_Date: datetime64 [2023-01-27, 2022-03-27]

# Now you can perform mathematical operations:
total_price = df['Price'].sum()  # 2101.25
avg_discount = df['Discount'].mean()  # 0.125 (12.5%)
active_products = df['Active'].sum()  # 1
```

### Database Schema Benefits

With proper data type detection, your databases now use appropriate column types:

- **SQLite**: `INTEGER`, `REAL`, `BOOLEAN`, `DATETIME`, `TEXT`
- **DuckDB**: `BIGINT`, `DOUBLE`, `BOOLEAN`, `TIMESTAMP`, `VARCHAR`

This enables:
- Mathematical operations and aggregations
- Proper sorting and filtering
- Better query performance
- Accurate data analysis

## Querying Your Data

### SQLite Queries

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("data/databases/TCS_tables.db")

# View available tables
metadata = pd.read_sql_query("SELECT * FROM tables_metadata", conn)
print(metadata)

# Query specific table
data = pd.read_sql_query("SELECT * FROM TCS_table_0 LIMIT 10", conn)
print(data)

conn.close()
```

### DuckDB Queries

```python
import duckdb

conn = duckdb.connect("data/databases/TCS_tables.duckdb")

# View available tables
metadata = conn.execute("SELECT * FROM tables_metadata").fetchdf()
print(metadata)

# Query with analytics
result = conn.execute("""
    SELECT COUNT(*) as row_count, 
           COUNT(DISTINCT column_name) as unique_values
    FROM TCS_table_0
""").fetchdf()

conn.close()
```

### CSV Analysis

```python
import pandas as pd

# Read summary
summary = pd.read_csv("data/csv/TCS_tables_summary.csv")
print(summary)

# Read specific table
table_data = pd.read_csv("data/csv/TCS_table_0.csv")
print(table_data.describe())
```

## Examples

Check out the [`example_usage.py`](https://github.com/DeepanshuTIET/webscrapper/blob/main/example_usage.py) and [`query_databases.py`](https://github.com/DeepanshuTIET/webscrapper/blob/main/query_databases.py) files for detailed examples.

### Example 1: Financial Data Scraping
```python
# TCS financial data
url = "https://www.screener.in/company/TCS/consolidated/"
scraper = WebScraperToStorage(url, "TCS")
scraper.run_complete_pipeline()
```

### Example 2: Multiple Companies
```python
companies = [
    ("TCS", "https://www.screener.in/company/TCS/consolidated/"),
    ("RELIANCE", "https://www.screener.in/company/RELIANCE/consolidated/"),
    ("INFY", "https://www.screener.in/company/INFY/consolidated/")
]

for company_name, url in companies:
    scraper = WebScraperToStorage(url, company_name)
    scraper.run_complete_pipeline()
    print(f"Completed scraping for {company_name}")
```

## Class Methods

### `WebScraperToStorage`

#### Constructor
- `__init__(url, company_name)`: Initialize scraper with target URL and company name

#### Main Methods
- `run_complete_pipeline()`: Execute the full scraping and storage pipeline
- `fetch_html()`: Download HTML content from the URL
- `extract_tables()`: Parse HTML and extract all tables
- `save_to_csv()`: Export tables to CSV format
- `save_to_sqlite()`: Store tables in SQLite database
- `save_to_duckdb()`: Store tables in DuckDB database

#### Utility Methods
- `clean_dataframe(df)`: Clean and prepare DataFrame for storage

## Dependencies

- `requests`: Web scraping
- `beautifulsoup4`: HTML parsing
- `pandas`: Data manipulation
- `sqlite3`: SQLite database (built-in)
- `duckdb`: DuckDB analytics database
- `numpy`: Numerical operations
- `python-dateutil`: Advanced date parsing for type detection
- `lxml` & `html5lib`: HTML parsing backends

## Error Handling

The scraper includes comprehensive error handling:

- **Network errors**: Handles connection timeouts and HTTP errors
- **Parsing errors**: Skips malformed tables and continues processing
- **Storage errors**: Reports database connection and file writing issues
- **Data validation**: Checks for empty tables and invalid data

## Output Formats

### CSV Files
- Individual CSV file for each table
- Summary CSV with metadata about all tables
- UTF-8 encoding for international characters

### SQLite Database
- One table per scraped HTML table
- Metadata table with table statistics
- SQL-compatible for complex queries

### DuckDB Database
- High-performance analytics database
- Same structure as SQLite but optimized for analytics
- Excellent for data science workflows

## Tips for Best Results

1. **Check robots.txt**: Ensure you're allowed to scrape the target website
2. **Add delays**: For multiple requests, add delays to be respectful
3. **Handle dynamic content**: This scraper works best with static HTML tables
4. **Validate data**: Always check the extracted data for accuracy
5. **Monitor performance**: Large tables may require additional memory

## Troubleshooting

### Common Issues

1. **No tables found**: Website might use JavaScript to load tables
2. **Permission denied**: Check file permissions in the data directory
3. **Import errors**: Install missing dependencies with `pip install -r requirements.txt`
4. **Memory issues**: Large tables might require chunked processing

### Getting Help

- Check the console output for detailed error messages
- Verify the website structure hasn't changed
- Ensure all dependencies are installed correctly
- Open an [issue on GitHub](https://github.com/DeepanshuTIET/webscrapper/issues) if you need help

## Project Structure

```
webscrapper/
├── retriving_html.py      # Main scraper class
├── example_usage.py       # Usage examples
├── query_databases.py     # Database querying examples
├── requirements.txt       # Dependencies
├── .gitignore            # Git ignore rules
├── README.md             # This file
└── data/                 # Output directory (created after running)
    ├── csv/              # CSV files
    ├── databases/        # SQLite and DuckDB files
    └── *.html           # Raw HTML files
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Author

**Deepanshu** - [DeepanshuTIET](https://github.com/DeepanshuTIET)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the pandas team for the excellent `read_html()` function
- Beautiful Soup for making HTML parsing so easy
- DuckDB team for creating such a fast analytics database
