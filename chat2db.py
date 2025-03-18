import os
import time
import cx_Oracle

import dotenv
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import uuid
import concurrent.futures 

from flask_cors import CORS
from flask import Flask, request, jsonify

from langchain_ollama import OllamaLLM
from langchain_community.utilities import SQLDatabase
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage

dotenv.load_dotenv(override=True)

# Flask App Initialization
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

run_port = os.getenv("FLASK_PORT", 1000)

# secret key for session
app.secret_key = os.environ.get("SECRET_KEY")
user_context = {}

# MySQL Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "service": os.getenv("DB_SERVICE"),
    "port": os.getenv("DB_PORT")
}

model_used = os.getenv("MODEL_USED")

if model_used == "ollama":
    # Initialize Ollama and LangChain
    sql_llm = OllamaLLM(model=os.getenv("LLM_MODEL_NAME"))
    summary_llm = OllamaLLM(model=os.getenv("LLM_MODEL_NAME"))
else:
    # Initialize OpenAI GPT-4o-mini for SQL generation & summarization
    sql_llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    summary_llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

db_uri = (
    f"oracle+cx_oracle://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/?service_name={DB_CONFIG['service']}"
)
sql_database = SQLDatabase.from_uri(db_uri)
sql_chain = create_sql_query_chain(sql_llm, sql_database)

def execute_sql_query(sql_query: str):
    try:
        dsn = cx_Oracle.makedsn(
            DB_CONFIG['host'],
            DB_CONFIG['port'],
            service_name=DB_CONFIG['service']
        )
        connection = cx_Oracle.connect(
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            dsn=dsn,
            encoding="UTF-8"
        )
        cursor = connection.cursor()
        cursor.execute(sql_query)

        # Fetch result if it's a SELECT query
        if sql_query.strip().lower().startswith("select"):
            result = cursor.fetchall()
        else:
            connection.commit()
            result = "Query executed successfully"

        cursor.close()
        connection.close()
        return result
    except Exception as e:
        return str(e)


# Function to generate SQL from prompt
def query_database(prompt):
    db_type = "oracle"
    original_prompt = f"""{prompt}. 
        Berikan sql yang lengkap saja tanpa penjelasan.
        Pastikan sql yang kamu berikan sudah sesuai dengan database dan dapat dijalankan di database {db_type}.
        Hindari penggunaan syntax yang tidak didukung di {db_type}.
        """
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

            # remove backslash and backtick and semicolon
            sql_query = sql_query.replace("\\", "").replace("`", "").replace(";", "")
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
    new_prompt = f"""Kamu berperan sebagai customer service yang ramah dan informatif.

        Berdasarkan pertanyaan dari user berikut:

        {prompt}

        Sistem menghasilkan SQL query berikut:

        {sql_query}

        Dan berikut adalah hasil dari query tersebut:

        {sql_result}

        Buatlah kesimpulan atau penjelasan jawaban untuk user berdasarkan hasil tersebut, dengan bahasa yang sederhana, sopan, dan mudah dimengerti.

        Gaya bahasa harus bersahabat dan humanis, tidak teknis, dan hindari menyebut istilah seperti SQL atau query.

        Gunakan kalimat yang menyampaikan empati dan informatif, serta jelaskan poin penting dari data tersebut.
    """
    response = summary_llm.invoke(new_prompt)
    if isinstance(response, AIMessage):
        response = response.content
    return response

# Function to Generate the Visualization
def generate_visualization(prompt, sql_query, sql_result: str):
    new_prompt = f""""
        Kamu adalah seorang data scientist. Berdasarkan prompt analisis berikut:

        {prompt}

        Dan berdasarkan SQL query berikut:

        {sql_query}

        Serta hasil datanya:

        {sql_result}

        Buatkan kode visualisasi menggunakan Seaborn dan Python yang paling relevan, informatif, dan menarik secara visual sesuai data yang tersedia.

        Tampilkan seluruh data, bukan hanya sampel.

        Jika data kategorikal, gunakan visualisasi seperti bar chart atau pie chart.
        Jika data numerik, gunakan histogram, boxplot, atau scatterplot sesuai relevansi.
        Jika perlu pengelompokan, gunakan grouping atau aggregation yang masuk akal.

        Cukup berikan kode visualisasi lengkap (tidak perlu ada penjelasan), gunakan judul, label sumbu, dan style visual yang menarik.
    """
    visualization = summary_llm.invoke(new_prompt)
    if isinstance(visualization, AIMessage):
        visualization = visualization.content
    return visualization

# Function to Generate the Table
def generate_table(prompt, sql_query, sql_result: str):
    new_prompt = (
        f"Kamu adalah seorang data scientist. Berdasarkan prompt {prompt} dan sql query {sql_query} dan hasilnya {sql_result}, "
        f"buatkan kode visualisasi berupa tabel yang cocok untuk data yang ada menggunakan pandas dan python. "
        f"Cukup berikan kode visualisasi saja, dan buat semenarik mungkin."
    )
    table_code = summary_llm.invoke(new_prompt)
    if isinstance(table_code, AIMessage):
        return table_code.content
    return table_code

# Run Visualization
def run_visualization_code(visualization_code, sql_result):
    import matplotlib
    matplotlib.use('Agg')
    df = pd.DataFrame(sql_result)
    local_vars = {"df": df, "plt": plt, "sns": sns}

    try:
        exec(visualization_code, {}, local_vars)
        
        # Save image to static/visuals with unique name
        filename = f"{uuid.uuid4().hex}.png"
        save_dir = os.path.join("static", "visuals")
        os.makedirs(save_dir, exist_ok=True)
        
        image_path = os.path.join(save_dir, filename)
        plt.savefig(image_path)
        plt.clf()
        
        return image_path  # can return full URL path if needed
    except Exception as e:
        return str(e)

# Run Table Code
def run_table_code(code: str, data: list) -> str:
    import pandas as pd
    import os
    import uuid

    # Create DataFrame
    df = pd.DataFrame(data)

    # Create directory if it doesn't exist
    os.makedirs("static/tables", exist_ok=True)

    # Prepare path to save table
    table_path = f"static/tables/{uuid.uuid4()}.html"

    # Execution environment
    exec_env = {"df": df, "pd": pd}

    # Execute the generated code
    try:
        exec(code, exec_env)
        # After execution, df may be updated
        styled_df = exec_env.get("styled_df")  # in case LLM outputs a styled df
        final_df = exec_env.get("df", df)

        # Save the result to HTML
        if styled_df is not None:
            styled_df.to_html(table_path)
        else:
            final_df.to_html(table_path)
    except Exception as e:
        print("Error executing table code:", e)
        raise RuntimeError(f"Failed to run table code: {e}")

    print("Table saved to:", table_path)
    return table_path




# Flask API Route
@app.route('/generate', methods=['POST'])
def generate():
    start = time.time()
    data = request.json
    prompt = data.get("prompt", "")
    user_id = data.get("user_id", "default")

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    query_result = query_database(prompt)
    sql_query = query_result.get("sql")
    sql_result = query_result.get("result")

    if not sql_query or not sql_result:
        return jsonify({"error": "Failed to generate SQL or get results"}), 500
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        summary_future = executor.submit(generate_response, prompt, sql_query, sql_result)
        visualization_future = executor.submit(generate_visualization, prompt, sql_query, sql_result)
        table_future = executor.submit(generate_table, prompt, sql_query, sql_result)

        response_text = summary_future.result()
        visualization_text = visualization_future.result()
        table_code = table_future.result()
        

    visualization_text = visualization_text.split("```python\n")[1].split("\n```")[0]
    table_text = table_code.split("```python\n")[1].split("\n```")[0]

    image_path = run_visualization_code(visualization_text, sql_result)
    table_path = run_table_code(table_text, sql_result)
    table_path = f"http://127.0.0.1:{run_port}/static/tables/{table_path.split('/')[-1]}"

    # Store in context
    user_context[user_id] = {
        "sql": sql_query,
        "result": sql_result,
        "viz_code": visualization_text,
        "table_code": table_text,
        "image_path": image_path,
        "table_path": table_path,

    }

    print(f"Time taken: {time.time() - start} seconds")
    return jsonify({
        "response": response_text,
        "image_path": user_context[user_id]["image_path"],
        "table_path": user_context[user_id]["table_path"],
    })

# Run Flask App
if __name__ == "__main__":
    app.run(debug=True, port=run_port)
