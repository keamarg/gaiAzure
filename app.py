from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

import psycopg2  # for postgres
import openai

# import logging

# logging.basicConfig(level=logging.DEBUG)  # Enable logging for DEBUG level


app = Flask(__name__)

CORS(app)
load_dotenv()  # Load environment variables from the .env file

openai.api_type = "azure"
openai.api_base = "https://keaopenai.openai.azure.com/"
openai.api_version = "2023-03-15-preview"  # subject to change
openai.api_key = os.getenv("AZURE_API_KEY")

# Get the PostgreSQL connection string from environment variable
connection_string = os.getenv("POSTGRES_CONNECTION_STRING")


def test_database_connection():
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] == 1
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        return False


@app.route("/database")
def database():
    if test_database_connection():
        return "Database connection successful"
    else:
        return "Unable to connect to the database"


@app.route("/", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        response = openai.ChatCompletion.create(
            # model=data["model"],
            engine=data["engine"],
            # deployment_id="gpt-3.5-turbo",
            messages=data["messages"],
            temperature=data["temperature"],
            max_tokens=data["max_tokens"],
            top_p=data["top_p"],
            frequency_penalty=data["frequency_penalty"],
            presence_penalty=data["presence_penalty"],
            stop=data["stop"],
        )
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()
