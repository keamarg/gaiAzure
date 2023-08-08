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

            # Retrieve all the posts from the posts table
            cursor.execute("SELECT id, username, content FROM posts")
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
                    "content": content,
                    "comments": []
                }

                # Retrieve comments for the current post
                cursor.execute("SELECT id, username, content FROM comments WHERE post_id = %s", (post_id,))
                comments_data = cursor.fetchall()

                for comment_row in comments_data:
                    comment_id = comment_row[0]
                    comment_username = comment_row[1]
                    comment_content = comment_row[2]

                    # Create a dictionary for each comment
                    comment_data = {
                        "id": comment_id,
                        "username": comment_username,
                        "content": comment_content,
                        "replies": []
                    }

                    # # Retrieve replies for the current comment
                    # cursor.execute("SELECT id, username, content FROM replies WHERE comment_id = %s", (comment_id,))
                    # replies_data = cursor.fetchall()

                    # for reply_row in replies_data:
                    #     reply_id = reply_row[0]
                    #     reply_username = reply_row[1]
                    #     reply_content = reply_row[2]

                    #     # Create a dictionary for each reply
                    #     reply_data = {
                    #         "id": reply_id,
                    #         "username": reply_username,
                    #         "content": reply_content
                    #     }

                    #     # Add the reply to the comment's 'replies' list
                    #     comment_data["replies"].append(reply_data)

                    # Add the comment to the post's 'comments' list
                    post_data["comments"].append(comment_data)

                all_posts.append(post_data)

            cursor.close()
            conn.close()

            return jsonify(all_posts)

        except psycopg2.Error as e:
            print(f"Error retrieving data from the database: {e}")
            return jsonify({"error": "Unable to retrieve data"}), 500

    elif request.method == "POST":
        data = request.get_json()
        post_id = data.get("post_id")
        username = data.get("username")
        content = data.get("content")

        if post_id:
            # This is a request to add a comment
            if username and content:
                try:
                    conn = psycopg2.connect(connection_string)
                    cursor = conn.cursor()

                    # Check if the post_id exists in the posts table
                    cursor.execute("SELECT id FROM posts WHERE id = %s", (post_id,))
                    existing_post = cursor.fetchone()

                    if not existing_post:
                        return jsonify({"error": "Invalid request: post not found"}), 400

                    # Insert the new comment into the comments table
                    cursor.execute(
                        "INSERT INTO comments (post_id, username, content) VALUES (%s, %s, %s) RETURNING id",
                        (post_id, username, content),
                    )

                    comment_id = cursor.fetchone()[0]

                    conn.commit()
                    cursor.close()
                    conn.close()

                    return jsonify({"message": "Comment added successfully", "comment_id": comment_id})

                except psycopg2.Error as e:
                    print(f"Error saving data to the database: {e}")
                    return jsonify({"error": "Unable to save data"}), 500
            else:
                return jsonify({"error": "Invalid request: missing username or content"}), 400

        else:
            # This is a request to add a new post
            if username and content:
                try:
                    conn = psycopg2.connect(connection_string)
                    cursor = conn.cursor()

                    # Insert the new post into the posts table
                    cursor.execute(
                        "INSERT INTO posts (username, content) VALUES (%s, %s) RETURNING id",
                        (username, content),
                    )

                    post_id = cursor.fetchone()[0]

                    conn.commit()
                    cursor.close()
                    conn.close()

                    return jsonify({"message": "Post added successfully", "post_id": post_id})

                except psycopg2.Error as e:
                    print(f"Error saving data to the database: {e}")
                    return jsonify({"error": "Unable to save data"}), 500
            else:
                return jsonify({"error": "Invalid request: missing username or content"}), 400

    else:
        return jsonify({"error": "Method not allowed"}), 405


if __name__ == "__main__":
    app.run(debug=True)
