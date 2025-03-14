import os
import time
import pymysql

import dotenv

from flask_cors import CORS
from flask import Flask, request, jsonify

from langchain_ollama import OllamaLLM
from langchain_community.utilities import SQLDatabase
from langchain.chains.sql_database.query import create_sql_query_chain

dotenv.load_dotenv(override=True)

# Flask App Initialization
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# MySQL Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
}

# Initialize Ollama and LangChain
sql_llm = OllamaLLM(model=os.getenv("LLM_MODEL_NAME"))
summary_llm = OllamaLLM(model=os.getenv("LLM_MODEL_NAME"))

db_uri = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['db']}"
sql_database = SQLDatabase.from_uri(db_uri)
sql_chain = create_sql_query_chain(sql_llm, sql_database)

# Function to execute SQL query
def execute_sql_query(sql_query: str):
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute(sql_query)
        result = cursor.fetchall()
        connection.close()
        return result
    except Exception as e:
        return str(e)

# Function to generate SQL from prompt
def query_database(prompt):
    original_prompt = f"{prompt}. Berikan sql yang lengkap saja tanpa penjelasan. Pastikan sql yang kamu berikan sudah sesuai dengan database dan dapat dijalankan"
    query_with_context = {"question": original_prompt}

    for _ in range(3):  # Retry logic for error handling
        sql_syntax = sql_chain.invoke(query_with_context)

        try:
            if "```sql" in sql_syntax:
                sql_query = sql_syntax.split("```sql\n")[1].split("\n```")[0].replace("\n", " ")
            elif "SQLQuery" in sql_syntax:
                sql_query = sql_syntax.split("SQLQuery: ")[1].replace("\n", " ")
            else:
                sql_query = sql_syntax

            res = execute_sql_query(sql_query)

            if isinstance(res, Exception) or (isinstance(res, str) and res.startswith("Error")):
                query_with_context = {
                    "question": f"Fix this error: {str(res)}. The original prompt is: {original_prompt}"
                }
            else:
                return {"sql": sql_query, "result": res}

        except Exception as e:
            query_with_context = {"question": f"Fix the error: {str(e)}. The original prompt is: {original_prompt}"}
            continue

    return {"sql": None, "result": None}

# Function to generate a friendly response
def generate_response(prompt, sql_query, sql_result):
    new_prompt = f"Kamu adalah customer service yang ramah. Berdasarkan pertanyaan user {prompt}, didapatkan sql query seperti berikut: {sql_query}. Hasilnya adalah {sql_result}. Buatkan kesimpulan dari data yang diberikan dengan bahasa yang mudah dipahami oleh user."
    response = summary_llm.invoke(new_prompt)
    return response

# Flask API Route
@app.route('/generate', methods=['POST'])
def generate():
    start = time.time()
    data = request.json
    prompt = data.get("prompt", "")

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    query_result = query_database(prompt)
    sql_query = query_result.get("sql")
    sql_result = query_result.get("result")

    if not sql_query or not sql_result:
        return jsonify({"error": "Failed to generate SQL or get results"}), 500

    response_text = generate_response(prompt, sql_query, sql_result)
    print(f"Time taken: {time.time() - start} seconds")
    return jsonify({"query": sql_query, "result": sql_result, "response": response_text})

# Run Flask App
if __name__ == "__main__":
    app.run(debug=True, port=1000)
