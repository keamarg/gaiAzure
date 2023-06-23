from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import openai


app = Flask(__name__)
CORS(app)

load_dotenv()  # Load environment variables from the .env file

openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route("/", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        response = openai.ChatCompletion.create(
            model=data["model"],
            messages=data["messages"],
            temperature=1,
        )
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()
