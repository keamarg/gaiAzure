from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
# import uuid

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


@app.route("/chatdatabase", methods=["GET", "POST"])
def database():
    print("this is the /chatdatabase endpoint")

    if request.method == "GET":
        try:
            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor()

            # Retrieve all the entries from the chatdata table
            cursor.execute("SELECT session_id, conversation_data FROM chatdata")
            data = cursor.fetchall()

            # Create a dictionary to hold the chat data with session_id as the key
            all_chat_data = {}

            for row in data:
                session_id = row[0]
                conversation_data = row[1]

                # Add the conversation_data under the corresponding session_id key
                all_chat_data[session_id] = conversation_data

            cursor.close()
            conn.close()

            return jsonify(all_chat_data)

        except psycopg2.Error as e:
            print(f"Error retrieving data from the database: {e}")
            return jsonify({"error": "Unable to retrieve data"}), 500

    elif request.method == "POST":
        # Initialize the session ID if it doesn't exist
        session_id = session.get("session_id")
        if not session_id:
            session_id = request.get_json().get("session_id")#str(uuid.uuid4())  # Generate a new session ID
            session["session_id"] = session_id  # Store the session ID in the session

        content = request.get_json().get("content")
        role = request.get_json().get("role")

    if content:
        try:
            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor()

            # Retrieve the existing conversation data for the session_id
            cursor.execute("SELECT conversation_data FROM chatdata WHERE session_id = %s", (session_id,))
            existing_data = cursor.fetchone()

            if existing_data:
                # Append the new message to the existing conversation data
                existing_data = existing_data[0]
                existing_data.append({ role: content})
                cursor.execute(
                    "UPDATE chatdata SET conversation_data = %s WHERE session_id = %s",
                    (json.dumps(existing_data), session_id),
                )
            else:
                # Insert a new entry with the session_id and conversation data
                conversation_data = [{role: content}]
                cursor.execute(
                    "INSERT INTO chatdata (session_id, conversation_data) VALUES (%s, %s)",
                    (session_id, json.dumps(conversation_data)),
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
    
@app.route("/postsdatabase", methods=["GET", "POST"])
def posts_endpoint():
    print("this is the /postsdatabase endpoint")

    if request.method == "GET":
        try:
            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor()

            # Retrieve all the posts from the posts_data table
            cursor.execute("SELECT id, username, content FROM posts_data")
            data = cursor.fetchall()

            # Create a list to hold all the posts
            all_posts = []

            for row in data:
                post_id = row[0]
                username = row[1]
                content = row[2]

                # Create a dictionary for each post
                post_data = {
                    "id": post_id,
                    "username": username,
                    "content": content
                }

                all_posts.append(post_data)

            cursor.close()
            conn.close()

            return jsonify(all_posts)

        except psycopg2.Error as e:
            print(f"Error retrieving data from the database: {e}")
            return jsonify({"error": "Unable to retrieve data"}), 500

    elif request.method == "POST":
        username = request.get_json().get("username")
        content = request.get_json().get("content")

        if username and content:
            try:
                conn = psycopg2.connect(connection_string)
                cursor = conn.cursor()

                # Insert the new post into the posts_data table
                cursor.execute(
                    "INSERT INTO posts_data (username, content) VALUES (%s, %s)",
                    (username, content),
                )

                conn.commit()
                cursor.close()
                conn.close()

                return "post added successfully"

            except psycopg2.Error as e:
                print(f"Error saving data to the database: {e}")
                return "Unable to save data"
        else:
            return "Invalid request: missing user or content"
    else:
        return "Method not allowed"

if __name__ == "__main__":
    app.run(debug=True)
