"""
Optional integration tests for database connectivity and SQL helpers.
Requires FACTDARI_TEST_DB_CONN_STR to be set.
"""
import os
import time
import pytest
import pyodbc

import factdari


@pytest.fixture(scope="module")
def db_conn_str():
    conn_str = os.environ.get("FACTDARI_TEST_DB_CONN_STR")
    if not conn_str:
        pytest.skip("FACTDARI_TEST_DB_CONN_STR not set")
    try:
        with pyodbc.connect(conn_str):
            pass
    except pyodbc.Error as exc:
        pytest.skip(f"Cannot connect to test DB: {exc}")
    return conn_str


@pytest.fixture(scope="module")
def test_table_name(db_conn_str):
    name = f"FactDariTest_{os.getpid()}_{int(time.time())}"
    table = f"dbo.[{name}]"
    create_sql = f"""
        CREATE TABLE {table} (
            ID INT IDENTITY(1,1) PRIMARY KEY,
            Name NVARCHAR(50) NULL
        )
    """
    drop_sql = f"DROP TABLE {table}"
    with pyodbc.connect(db_conn_str) as conn:
        cur = conn.cursor()
        cur.execute(create_sql)
        conn.commit()
    try:
        yield name
    finally:
        try:
            with pyodbc.connect(db_conn_str) as conn:
                cur = conn.cursor()
                cur.execute(drop_sql)
                conn.commit()
        except pyodbc.Error:
            pass


@pytest.mark.integration
def test_fetch_query_basic(db_conn_str):
    app = factdari.FactDariApp.__new__(factdari.FactDariApp)
    app.CONN_STR = db_conn_str

    rows = app.fetch_query("SELECT 1 AS Value")

    assert rows
    assert rows[0][0] == 1


@pytest.mark.integration
def test_execute_insert_and_update(db_conn_str, test_table_name):
    app = factdari.FactDariApp.__new__(factdari.FactDariApp)
    app.CONN_STR = db_conn_str
    table = f"dbo.[{test_table_name}]"

    new_id = app.execute_insert_return_id(
        f"INSERT INTO {table} (Name) OUTPUT INSERTED.ID VALUES (?)",
        ("initial",),
    )

    assert isinstance(new_id, int)

    updated = app.execute_update(
        f"UPDATE {table} SET Name = ? WHERE ID = ?",
        ("updated", new_id),
    )

    assert updated is True

    rows = app.fetch_query(f"SELECT ID, Name FROM {table} WHERE ID = ?", (new_id,))
    assert rows == [(new_id, "updated")]
