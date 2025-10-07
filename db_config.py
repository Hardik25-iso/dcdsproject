import mysql.connector
from mysql.connector import Error

def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',        # <-- CHANGE THIS
            password='root',   # <-- CHANGE THIS
            database='orphanagepune_db' # <-- UPDATED NAME
        )
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None