import os
import sqlite3
import pandas as pd
import re

__all__ = [
    'set_database_path',
    'get_database_path',
    'clean_sql_query',
    'run_query',
    'get_db_schema',
    'get_structured_schema',
]

_CURRENT_DB_PATH = None
_DB_PATH_ENV_VAR = "SQL_ASSISTANT_DB_PATH"

def set_database_path(db_path: str):
    global _CURRENT_DB_PATH
    _CURRENT_DB_PATH = db_path
    os.environ[_DB_PATH_ENV_VAR] = db_path

def get_database_path() -> str:
    global _CURRENT_DB_PATH

    if _CURRENT_DB_PATH is not None:
        return _CURRENT_DB_PATH

    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        db_path = os.environ.get(_DB_PATH_ENV_VAR)
        if db_path is not None:
            return db_path
    except:
        pass

    raise ValueError(
        "Database path not set. Please ensure:\n"
        "  1. main.py calls set_database_path() before workflow execution, OR\n"
        "  2. SQL_ASSISTANT_DB_PATH environment variable is set, OR\n"
        f"  3. {_DB_PATH_ENV_VAR} is defined in .env file"
    )

def clean_sql_query(query: str) -> str:
    if not query:
        return query

    pydantic_pattern = r"(?:reviewed_sqlquery|sqlquery)\s*=\s*['\"](.+?)['\"]"
    pydantic_match = re.search(pydantic_pattern, query, flags=re.DOTALL)
    if pydantic_match:
        query = pydantic_match.group(1)

    query = re.sub(r"^```sql\s*", "", query, flags=re.MULTILINE)
    query = re.sub(r"^```\s*$", "", query, flags=re.MULTILINE)
    query = re.sub(r"```sql", "", query)
    query = re.sub(r"```", "", query)

    query = query.strip()
    return query

def run_query(query, db_path):
    try:
        cleaned_query = clean_sql_query(query)
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(cleaned_query, conn)
        conn.close()
        return df.head().to_string(index=False)
    except Exception as e:
        return f"Query failed: Execution failed on sql '{cleaned_query}': {e}"

def get_db_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    schema = ""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for (table_name,) in tables:
        cursor.execute(
            f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';"
        )
        create_stmt = cursor.fetchone()[0]
        schema += create_stmt + ";\n\n"
    conn.close()
    return schema

def get_structured_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    lines = ["Available tables and columns:"]
    for (table_name,) in tables:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        lines.append(f"- {table_name}: {', '.join(columns)}")
    conn.close()
    return "\n".join(lines)

if __name__ == "__main__":
    print("Database helper module.")