from flask import Flask, jsonify
import time
import pymysql
import os
import subprocess
import json
import csv
import logging
import cryptography

app = Flask(__name__)

# -----------------------------
# 🔹 Configure Logging (Docker Captures Logs)
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# -----------------------------
# 🔹 Database Configuration
# -----------------------------

# ✅ Load Environment Variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
    "port": int(os.getenv("MYSQL_PORT", 3306))  # Ensure port is an integer
}

# ✅ Retry Connection Logic
MAX_RETRIES = 10
for attempt in range(MAX_RETRIES):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        logger.info("✅ Database connection successful!")
        break  # Exit loop on successful connection
    except pymysql.err.OperationalError as e:
        logger.warning(f"⚠️ Attempt {attempt + 1}/{MAX_RETRIES}: Unable to connect with {DB_CONFIG}"
                       f". Retrying in 5 seconds...")
        time.sleep(5)
else:
    logger.error("❌ Max retries exceeded. Could not connect to the database.")
    raise Exception("❌ Max retries exceeded. Could not connect to the database.")

# -----------------------------
# ✅ Ensure Database Table Exists
# -----------------------------
def create_table():
    """Creates a table for storing live market data if it does not already exist."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            price DECIMAL(18,8) NOT NULL,
            uniswap_liquidity DECIMAL(30,8),
            curve_liquidity DECIMAL(30,8),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    logger.info("✅ Database table `market_data` checked/created.")

create_table()  # Ensure table is created on startup

def import_csv_to_db():
    """Imports CSV data into MySQL."""
    cur = conn.cursor()

    with open("historical_data.csv", "r") as file:
        reader = csv.reader(file)
        headers = next(reader)  # Extract headers

        for row in reader:
            date = row[0]
            for i in range(1, len(headers)):  # Skip the date column
                symbol = headers[i]
                price = float(row[i]) if row[i] else 0  # Handle empty values
                cur.execute("""
                    INSERT INTO market_data (symbol, price, timestamp)
                    VALUES (%s, %s, %s)
                """, (symbol, price, date))

    conn.commit()
    cur.close()
    logger.info("✅ CSV data successfully imported into MySQL.")

# -----------------------------
# 🔹 Flask API Endpoints
# -----------------------------

@app.route("/")
def read_root():
    return jsonify({"message": "Hello, World!"})

@app.route("/users")
def get_users():
    """Fetches users from the database."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users;")
        users = cur.fetchall()
        cur.close()
        logger.info("✅ Users fetched successfully from database.")
        return jsonify({"users": users})
    except Exception as e:
        logger.error(f"❌ Error fetching users: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route("/live-data")
def fetch_and_store_live_data():
    """
    Calls an external Python script (`fetch_live_data.py`) to get:
    - Live price
    - Liquidity from Uniswap & Curve
    - Timestamp
    Stores data in MySQL & returns it to the frontend.
    """
    try:
        # ✅ Call the external script
        result = subprocess.run(["python", "fetch_live_data.py"], capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"❌ Error in fetch_live_data.py: {result.stderr}")
            raise Exception(f"Error in fetch_live_data.py: {result.stderr}")

        # ✅ Parse JSON output from script
        live_data = json.loads(result.stdout)

        # ✅ Store the fetched data in the database
        cur = conn.cursor()

        for symbol, data in live_data.items():
            price = data["price"]
            uniswap_liquidity = data.get("uniswap_liquidity", None)
            curve_liquidity = data.get("curve_liquidity", None)
            timestamp = data["timestamp"]

            cur.execute("""
                INSERT INTO market_data (symbol, price, uniswap_liquidity, curve_liquidity, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """, (symbol, price, uniswap_liquidity, curve_liquidity, timestamp))

        conn.commit()
        cur.close()
        logger.info(f"✅ Live data stored successfully for {len(live_data)} symbols.")

        # ✅ Return live data to the frontend
        return jsonify({"status": "success", "live_data": live_data})

    except Exception as e:
        logger.error(f"❌ Error fetching live data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route("/historical-data")
def get_historical_data():
    """
    Fetches stored market data from MySQL.
    Returns the latest price, liquidity, and timestamp for each asset.
    """
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute("""
            SELECT symbol, price, uniswap_liquidity, curve_liquidity, timestamp
            FROM market_data
            ORDER BY timestamp DESC
        """)

        historical_data = cur.fetchall()
        cur.close()
        logger.info(f"✅ Retrieved {len(historical_data)} historical records.")

        return jsonify({"status": "success", "historical_data": historical_data})

    except Exception as e:
        logger.error(f"❌ Error fetching historical data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(host="localhost", port=8000, debug=True)
