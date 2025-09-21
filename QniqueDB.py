import json
from flask import Flask, jsonify, request
import pyodbc
from flask_cors import CORS
import datetime

app = Flask(__name__)
CORS(app)

# --- Hard-coded Credentials for two databases ---
DB_CREDS = {
    "AK": {
        "server": "Lenovo",
        "username": "User1",
        "password": "12345"
    },
    "Test": {
        "server": "Lenovo",
        "username": "User1",
        "password": "12345"
    }
}

# Helper function to establish a database connection
def get_db_connection(database_name):
    """Establishes a database connection using hard-coded credentials."""
    creds = DB_CREDS.get(database_name)
    if not creds:
        raise ValueError(f"No credentials found for database: {database_name}")
        
    connection_string = (
       f"DRIVER={{ODBC Driver 17 for SQL Server}};"
       f"SERVER={creds['server']};"
       f"DATABASE={database_name};"
       f"UID={creds['username']};"
       f"PWD={creds['password']};"
       f"Encrypt=No;"
    )
    return pyodbc.connect(connection_string)

def format_db_data(rows, columns):
    """Format rows into dictionaries, replicating SSMS style for date, datetime, and bit fields."""
    result_data = []
    for row in rows:
        item = {}
        for i, col_name in enumerate(columns):
            value = row[i]

            if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
                # DATE → YYYY-MM-DD
                item[col_name] = value.strftime('%Y-%m-%d')

            elif isinstance(value, datetime.datetime):
                # DATETIME / DATETIME2 → YYYY-MM-DD HH:MM:SS.fffffff
                item[col_name] = value.strftime('%Y-%m-%d %H:%M:%S.%f') + "0"

            elif isinstance(value, bool):
                # BIT → 0/1
                item[col_name] = 1 if value else 0

            elif value is None:
                # NULL handling (explicit "NULL")
                item[col_name] = "NULL"

            else:
                item[col_name] = value

        result_data.append(item)
    return result_data

def get_config():
    """Reads the configuration from config.json."""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'error': 'config.json not found'}, 404
    except json.JSONDecodeError:
        return {'error': 'Invalid JSON format in config.json'}, 500

@app.route('/get_config', methods=['GET'])
def get_tools_config():
    config = get_config()
    if 'error' in config:
        return jsonify(config), config.get('status', 500)
    return jsonify(config)

# Generic endpoint to fetch data
@app.route('/get_data', methods=['GET'])
def get_data():
    database_name = request.args.get('database')
    select_query = request.args.get('query')
    
    if not database_name or not select_query:
        return jsonify({'error': 'Missing database or query parameter'}), 400

    try:
        cnxn = get_db_connection(database_name)
        cursor = cnxn.cursor()
        
        cursor.execute(select_query)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        
        result_data = format_db_data(rows, columns)
        
        cursor.close()
        cnxn.close()

        return jsonify({'headers': columns, 'data': result_data})
    except pyodbc.Error as ex:
        print(f"Database error: {ex}")
        return jsonify({'error': str(ex)}), 500
    except ValueError as ex:
        return jsonify({'error': str(ex)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
