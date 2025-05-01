# 🤖 Natural Language to Database – Ask Questions, Get Answers & Graphs

## Overview

Working with databases can be tricky—especially if you’re not familiar with SQL. Whether you’re a data analyst, business user, or just curious, wouldn’t it be nice if you could simply ask:

> "What was the total sales last month?"  
> "Show me a bar chart of users by country"

This project makes that possible.

You just type your question in **plain English**, and the system handles the rest: querying the database, analyzing the data, and even generating Python code to create **tables and graphs**.

---

## 🌟 What It Can Do

- 🔍 Ask questions in natural language — no SQL required.
- 🧠 AI translates your question into a database query.
- 📊 Automatically generates Python code to show results and graphs.
- 🛢️ Works with various types of databases (e.g., PostgreSQL, MySQL, SQLite).
- 🖥️ Run it locally using **Flask**, with support for **Ollama** (local LLM) or **OpenAI**.

---

## 💡 How It Works

1. You connect your database (any standard type).
2. Ask a question like:
   - "How many orders were placed in the last 7 days?"
   - "Give me a pie chart of customer segments."
3. The system:
   - Translates your question into an SQL query using a language model.
   - Runs the query on your database.
   - Generates Python code to create tables or visualizations from the result.
4. You get an instant answer — with optional charts!

---

## 🧰 Requirements

- Python 3.8+
- Flask
- An accessible database (SQLite, PostgreSQL, etc.)
- LLM backend:
  - **OpenAI API key** _or_
  - **Ollama** installed and running locally

---

## ⚙️ How to Use

1. Clone the repository:

```bash
git clone https://github.com/ahmad20/chat2db.git
cd chat2db
```
2. Install the required packages:

```bash
pip install -r requirements.txt
```
3. Set your config in .env:

- For OpenAI: OPENAI_API_KEY=your-key
- For Ollama: make sure it’s installed and running

Run the app:

```bash
flask run
```

4.Open your browser:

```bash
http://localhost:5000
```

Enter your question, connect your database, and start exploring with natural language!

## 📝 Example Use Case
Let’s say you're analyzing a customer database.

You ask:
```
"How many users signed up each month this year?"
```

The chatbot responds with:

- A summary of the results
- Graph
- Table

All without writing a single line of SQL or Python yourself.

## 🙌 Contributions
Have an idea for improving database compatibility, refining queries, or expanding graph types?
Pull requests and feature suggestions are welcome!

Made with 🧠 AI + 🛢️ data to make querying databases accessible to everyone.