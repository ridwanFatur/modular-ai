import argparse
import socket
import sqlite3
from pathlib import Path

import pandas as pd
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.routing import Mount, Route
from utils_db_helper import (
	get_database_path,
	clean_sql_query,
)

# Initialize FastMCP server with specific configuration for tool exposure
mcp = FastMCP(name="sql-assistant-tools", json_response=False, stateless_http=False)


@mcp.tool()
async def run_sql_query(query: str) -> str:
    """
    Execute a SQL query against the SQLite database and return formatted results.

    Parameters:
    - query: The SQL query to execute

    Returns:
    - Formatted query results as a string, or error message if query fails
    """
    try:
        # Clean the query to remove any markdown formatting
        cleaned_query = clean_sql_query(query)
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(cleaned_query, conn)
        conn.close()
        return df.head().to_string(index=False)
    except Exception as e:
        return f"Query failed: Execution failed on sql '{cleaned_query}': {e}"


@mcp.tool()
async def get_database_schema() -> str:
    """
    Get the complete database schema with enhanced table structures.
    Returns a user-friendly format with table names, columns, types, and sample data.

    Returns:
    - Enhanced database schema as a string with structure and samples
    """
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema_parts = ["DATABASE SCHEMA:\n" + "=" * 80 + "\n"]

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for (table_name,) in tables:
        # Get CREATE statement
        cursor.execute(
            f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';"
        )
        create_stmt = cursor.fetchone()[0]
        schema_parts.append(f"\nTable: {table_name}")
        schema_parts.append("-" * 80)

        # Get column info in a more readable format
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        schema_parts.append("Columns:")
        for col in columns:
            col_name, col_type, not_null, default, pk = (
                col[1],
                col[2],
                col[3],
                col[4],
                col[5],
            )
            pk_marker = " [PRIMARY KEY]" if pk else ""
            not_null_marker = " [NOT NULL]" if not_null else ""
            schema_parts.append(
                f"  - {col_name}: {col_type}{pk_marker}{not_null_marker}"
            )

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        schema_parts.append(f"\nRow count: {row_count}")

        # Get sample data (first 3 rows)
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 3", conn)
            if not df.empty:
                schema_parts.append("\nSample data (first 3 rows):")
                schema_parts.append(df.to_string(index=False))
        except Exception as e:
            schema_parts.append(f"Sample data unavailable: {e}")

        schema_parts.append("\n" + "=" * 80)

    conn.close()
    return "\n".join(schema_parts)


@mcp.tool()
async def get_table_sample(table_name: str, limit: int = 5) -> str:
    """
    Get sample rows from a specific table to understand data patterns.

    Parameters:
    - table_name: Name of the table to sample
    - limit: Number of rows to retrieve (default 5, max 10)

    Returns:
    - Sample rows as formatted string
    """
    try:
        db_path = get_database_path()
        limit = min(limit, 10)  # Cap at 10 rows
        conn = sqlite3.connect(db_path)

        # Verify table exists
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            (table_name,),
        )
        if not cursor.fetchone():
            conn.close()
            return f"Error: Table '{table_name}' does not exist"

        # Get sample data
        df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT {limit}", conn)
        conn.close()

        if df.empty:
            return f"Table '{table_name}' exists but is empty"

        return (
            f"Sample from {table_name} ({len(df)} rows):\n{df.to_string(index=False)}"
        )
    except Exception as e:
        return f"Error retrieving sample from '{table_name}': {e}"


@mcp.tool()
async def validate_sql_syntax(query: str) -> str:
    """
    Validate SQL query syntax without executing it.
    Uses EXPLAIN to check if the query is syntactically valid.

    Parameters:
    - query: SQL query to validate

    Returns:
    - Validation result message
    """
    try:
        cleaned_query = clean_sql_query(query)
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Use EXPLAIN to validate without executing
        cursor.execute(f"EXPLAIN {cleaned_query}")
        conn.close()

        return f"✓ SQL syntax is valid. Query is ready for execution."
    except Exception as e:
        return f"✗ SQL syntax error: {e}\n\nQuery was:\n{cleaned_query}"


@mcp.tool()
async def get_column_stats(table_name: str, column_name: str) -> str:
    """
    Get statistics about a specific column (distinct values, min/max, nulls).
    Useful for understanding data distribution before writing queries.

    Parameters:
    - table_name: Name of the table
    - column_name: Name of the column

    Returns:
    - Column statistics as formatted string
    """
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Verify table and column exist
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        if column_name not in columns:
            conn.close()
            return f"Error: Column '{column_name}' not found in table '{table_name}'. Available columns: {', '.join(columns)}"

        stats = []
        stats.append(f"Statistics for {table_name}.{column_name}:")
        stats.append("-" * 50)

        # Count total and non-null values
        cursor.execute(f"SELECT COUNT(*), COUNT({column_name}) FROM {table_name}")
        total, non_null = cursor.fetchone()
        stats.append(f"Total rows: {total}")
        stats.append(f"Non-null values: {non_null}")
        stats.append(f"Null values: {total - non_null}")

        # Count distinct values
        cursor.execute(f"SELECT COUNT(DISTINCT {column_name}) FROM {table_name}")
        distinct = cursor.fetchone()[0]
        stats.append(f"Distinct values: {distinct}")

        # Get min/max if applicable
        try:
            cursor.execute(
                f"SELECT MIN({column_name}), MAX({column_name}) FROM {table_name}"
            )
            min_val, max_val = cursor.fetchone()
            if min_val is not None:
                stats.append(f"Min value: {min_val}")
                stats.append(f"Max value: {max_val}")
        except:
            pass  # Column type may not support min/max

        # Get sample distinct values (up to 10)
        cursor.execute(f"SELECT DISTINCT {column_name} FROM {table_name} LIMIT 10")
        samples = [str(row[0]) for row in cursor.fetchall() if row[0] is not None]
        if samples:
            stats.append(f"\nSample values: {', '.join(samples[:10])}")

        conn.close()
        return "\n".join(stats)
    except Exception as e:
        return f"Error getting statistics for {table_name}.{column_name}: {e}"


@mcp.tool()
async def list_tables() -> str:
    """
    List all tables in the database.

    Returns:
    - Comma-separated list of table names
    """
    print(f"Database Path: {get_database_path()}")
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return ", ".join(tables) if tables else "No tables found"
    except Exception as e:
        return f"Error listing tables: {e}"


@mcp.tool()
async def count_rows(table_name: str) -> str:
    """
    Count total rows in a specific table.

    Parameters:
    - table_name: Name of the table

    Returns:
    - Row count as string
    """
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        conn.close()
        return f"Table '{table_name}' has {count} rows"
    except Exception as e:
        return f"Error counting rows in '{table_name}': {e}"


@mcp.tool()
async def check_table_exists(table_name: str) -> str:
    """
    Check if a table exists in the database.

    Parameters:
    - table_name: Name of the table to check

    Returns:
    - Confirmation message
    """
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            (table_name,),
        )
        exists = cursor.fetchone() is not None
        conn.close()
        if exists:
            return f"✓ Table '{table_name}' exists"
        else:
            return f"✗ Table '{table_name}' does not exist"
    except Exception as e:
        return f"Error checking table '{table_name}': {e}"


def find_free_port(start_port: int = 8150, max_attempts: int = 10) -> int:
    """
    Find an available port starting from start_port.

    Args:
        start_port: Starting port number to check
        max_attempts: Maximum number of ports to try

    Returns:
        Available port number

    Raises:
        RuntimeError: If no free port is found
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"No free port found in range {start_port}-{start_port + max_attempts - 1}"
    )


def update_env_file(host: str, port: int) -> None:
    """
    Update or create .env file with MCP_SERVER_URL.

    Args:
        host: Server host
        port: Server port
    """
    # Find project root (where .env should be)
    current_file = Path(__file__)
    project_root = current_file.parent
    env_file = project_root / ".env"

    mcp_url = f"http://{host}:{port}/sse"

    # Read existing .env content
    env_lines = []
    mcp_line_found = False

    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if line.startswith("MCP_SERVER_URL="):
                    env_lines.append(f"MCP_SERVER_URL={mcp_url}\n")
                    mcp_line_found = True
                else:
                    env_lines.append(line)

    # Add MCP_SERVER_URL if not found
    if not mcp_line_found:
        env_lines.append(f"MCP_SERVER_URL={mcp_url}\n")

    # Write back to .env
    with open(env_file, "w") as f:
        f.writelines(env_lines)

    print(f"✓ Updated {env_file} with MCP_SERVER_URL={mcp_url}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run MCP server for SQL Assistant database tools"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to listen on (default: auto-detect starting from 8150)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    args = parser.parse_args(argv)
    
    print(f"Database Path: {get_database_path()}")

    # Find available port if not specified
    if args.port is None:
        try:
            args.port = find_free_port(start_port=8150)
            print(f"🔍 Auto-detected free port: {args.port}")
        except RuntimeError as e:
            print(f"❌ Error: {e}")
            return 1
    else:
        # Check if specified port is available
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((args.host, args.port))
        except OSError:
            print(
                f"⚠️  Warning: Port {args.port} is already in use, finding alternative..."
            )
            try:
                args.port = find_free_port(start_port=args.port + 1)
                print(f"🔍 Using alternative port: {args.port}")
            except RuntimeError as e:
                print(f"❌ Error: {e}")
                return 1

    # Update .env file with the port being used
    try:
        update_env_file(args.host, args.port)
    except Exception as e:
        print(f"⚠️  Warning: Failed to update .env file: {e}")

    # Create the SSE application for MCP communication
    sse_subapp = mcp.sse_app()

    # Set up routing with user-friendly redirects
    app = Starlette(
        routes=[
            Route("/", lambda request: RedirectResponse(url="/sse")),
            Route("/sse/", lambda request: RedirectResponse(url="/sse")),
            Mount("/", app=sse_subapp),
        ]
    )

    # Start the server
    print(f"\n🚀 Starting MCP server for SQL Assistant tools...")
    print(f"📡 Server listening on {args.host}:{args.port}")
    print(f"🔗 SSE endpoint: http://{args.host}:{args.port}/sse")
    print(f"\n✨ Keep this terminal running!\n")
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
