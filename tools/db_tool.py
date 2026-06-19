import os
from dotenv import load_dotenv
from api.monitor import monitor
from mysql.connector import connect, Error
from langchain_core.tools import tool

load_dotenv()

# Load configuration for convenience
def get_db_config():
    """Get database configuration from environment variables."""
    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE"),
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
        "collation": os.getenv("MYSQL_COLLATION", "utf8mb4_unicode_ci"),
        "autocommit": True,
        "sql_mode": os.getenv("MYSQL_SQL_MODE", "TRADITIONAL")
    }
    # Remove None values
    config = {k: v for k, v in config.items() if v is not None}

    # Validate required keys
    required_keys = ["user", "password", "database"]
    missing_keys = [k for k in required_keys if k not in config]
    if missing_keys:
        raise ValueError(f"Missing core database configuration: {', '.join(missing_keys)}")

    return config

@tool
def list_sql_tables() -> str:
    """
    Query all available tables in the current database.
    Action: Helps the model identify available tables for subsequent custom SQL queries.
    :return: List of tables or error message.
    """
    # Telemetry: Report tool usage to frontend
    monitor.report_tool(tool_name="list_sql_tables", args={})
    
    config = get_db_config()

    try:
        with connect(**config) as conn:
            with conn.cursor() as cursor:
                sql = "show tables"
                cursor.execute(sql)
                tables = cursor.fetchall()
                if not tables:
                    return "No tables available."
                
                table_names = [table[0] for table in tables]
                return f"Available tables: {', '.join(table_names)}"
    except Error as e:
        return f"Query exception: {str(e)}"

@tool
def get_table_data(table_name: str) -> str:
    """
    Query data from a specified table. 
    Action: Must be called after list_sql_tables to validate table name.
    Useful for: 1. Querying single-table data. 2. Providing schema information (columns & format) for multi-table queries.
    :param table_name: Name of the table.
    :return: Data in CSV-like format (header in first row, values separated by commas).
    """
    monitor.report_tool(tool_name="get_table_data", args={"table_name": table_name})

    config = get_db_config()
    try:
        with connect(**config) as conn:
            with conn.cursor() as cursor:
                sql = f"select * from {table_name} limit 100"
                cursor.execute(sql)
                
                description = cursor.description
                if not description:
                    return f"Table: {table_name} is empty."
                
                columns = [desc[0] for desc in description]
                rows = cursor.fetchall()
                results = [",".join(map(str, row)) for row in rows]

                header_str = ",".join(columns)
                data_str = "\n".join(results)
                return f"{header_str}\n{data_str}"
    except Error as e:
        return f"Query exception: {str(e)}"

@tool
def execute_sql_query(query: str) -> str:
    """
    Execute a custom SQL query. 
    Action: Ensure you have called list_sql_tables and get_table_data first to verify table names and schema.
    :param query: The custom SQL statement to execute.
    :return: Data in CSV-like format.
    """
    monitor.report_tool(tool_name="execute_sql_query", args={"query": query})

    config = get_db_config()
    try:
        with connect(**config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                
                description = cursor.description
                if not description:
                    return f"Custom SQL query returned no result, query: {query}"
                
                columns = [desc[0] for desc in description]
                rows = cursor.fetchall()
                results = [",".join(map(str, row)) for row in rows]

                header_str = ",".join(columns)
                data_str = "\n".join(results)
                return f"{header_str}\n{data_str}"
    except Error as e:
        return f"Query exception: {str(e)}"

if __name__ == "__main__":
    # Test execution
    print(execute_sql_query("SELECT * FROM `drugs` dgs join sales_records srd on dgs.drug_id = srd.drug_id"))
    