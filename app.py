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


def execute_query(query):
    connection = psycopg2.connect(connection_string)
    cursor = connection.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    connection.close()
    return result


@app.route("/projects", methods=["GET"])
def get_projects():
    try:
        # Example query to check if projects exist in the database
        query = "SELECT COUNT(*) FROM projects"
        result = execute_query(query)
        count = result[0][0]  # Retrieve the count value from the result
        if count > 0:
            return jsonify({"message": "Projects exist in the database"})
        else:
            return jsonify({"message": "No projects found in the database"})
        # # Example query to retrieve projects from the database
        # query = "SELECT * FROM projects"
        # result = execute_query(query)
        # # Format the result as JSON and return it
        # projects = [{"id": row[0], "name": row[1]} for row in result]
        # return jsonify(projects)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
