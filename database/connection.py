import mysql.connector
from mysql.connector import MySQLConnection

from config import get_database_settings


def get_connection() -> MySQLConnection:
    """Create a MySQL connection using settings from .env or the environment."""
    return mysql.connector.connect(**get_database_settings())
