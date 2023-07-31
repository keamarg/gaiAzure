from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
import os
import uuid

import psycopg2  # for postgres
import openai

# import logging

# logging.basicConfig(level=logging.DEBUG)  # Enable logging for DEBUG level


app = Flask(__name__)
app.secret_key = "your_secret_key"  # Set a secret key for the session

CORS(app)
load_dotenv()  # Load environment variables from the .env file

openai.api_type = "azure"
openai.api_base = "https://keaopenai.openai.azure.com/"
openai.api_version = "2023-03-15-preview"  # subject to change
openai.api_key = os.getenv("AZURE_API_KEY")

# Configure the session interface
app.config["SESSION_TYPE"] = "filesystem"

# Get the PostgreSQL connection string from environment variable
connection_string = os.getenv("AZURE_POSTGRESQL_CONNECTIONSTRING")


def test_database_connection():
    try:
        print("testing database connection")
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


@app.route("/database", methods=["GET", "POST"])
def database():
    print("this is the /database endpoint")

    # Initialize the session ID if it doesn't exist
    session_id = session.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())  # Generate a new session ID
        session["session_id"] = session_id  # Store the session ID in the session

    if request.method == "GET":
        try:
            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor()

            # Retrieve the entry based on the session ID
            cursor.execute("SELECT content FROM chatdata WHERE id = %s", (session_id,))
            entry = cursor.fetchone()

            if entry:
                # Return the content of the entry
                return entry[0]
            else:
                cursor.close()
                conn.close()
                return "Entry not found"

        except psycopg2.Error as e:
            print(f"Error retrieving data from the database: {e}")
            return "Unable to retrieve data"

    elif request.method == "POST":
        content = request.get_json().get("content")  # request.form.get("content")
        if content:
            try:
                conn = psycopg2.connect(connection_string)
                cursor = conn.cursor()

                # Check if the session ID already exists in the database
                cursor.execute(
                    "SELECT * FROM chatdata WHERE session_id = %s", (session_id,)
                )
                existing_entry = cursor.fetchone()

                if existing_entry:
                    # Update the existing entry by appending the new content
                    new_content = existing_entry[1] + content
                    cursor.execute(
                        "UPDATE chatdata SET content = %s WHERE session_id = %s",
                        (new_content, session_id),
                    )
                else:
                    # Insert a new entry with the session ID and content
                    cursor.execute(
                        "INSERT INTO chatdata (session_id, content) VALUES (%s, %s)",
                        (session_id, content),
                    )

                conn.commit()
                cursor.close()
                conn.close()

                return "Data saved to the database"

            except psycopg2.Error as e:
                print(f"Error saving data to the database: {e}")
                return "Unable to save data"
        else:
            return "Invalid request: missing content"


@app.route("/", methods=["POST"])
def chat():
    print("this is the / endpoint")
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
    app.run(debug=True)
