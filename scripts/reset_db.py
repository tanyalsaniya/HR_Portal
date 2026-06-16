# scripts/reset_db.py
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def reset_db():
    db_name = os.getenv('DB_NAME', 'hr_portal')
    db_user = os.getenv('DB_USER', 'hr_user')
    db_pass = os.getenv('DB_PASSWORD', 'postgres')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')

    print(f"Connecting to database {db_name} on {db_host}:{db_port} as user {db_user}...")
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_pass,
            host=db_host,
            port=db_port
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Dropping public schema...")
        cursor.execute("DROP SCHEMA IF EXISTS public CASCADE;")
        
        print("Recreating public schema...")
        cursor.execute("CREATE SCHEMA public;")
        cursor.execute("GRANT ALL ON SCHEMA public TO public;")
        cursor.execute(f"GRANT ALL ON SCHEMA public TO {db_user};")
        
        print("Database schema reset successfully.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error resetting database: {e}")

if __name__ == '__main__':
    reset_db()
