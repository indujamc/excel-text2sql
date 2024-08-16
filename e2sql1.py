import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
import os

# Configure Google Gemini API Key
genai.configure(api_key="AIzaSyCe1Q3jSavb0lTvUSNtSfJEdl15ZZ47oUk")

## Function To Load Google Gemini Model and provide queries as response
def get_gemini_response(question, prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt, question])
    return response.text

## Function To Retrieve Query Results from the Database
def read_sql_query(sql, db):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return rows

## Function To Create Table from DataFrame
def create_table_from_df(conn, df, table_name):
    cursor = conn.cursor()
    # Replace spaces with underscores in column names
    columns = df.columns
    columns = [col.replace(" ", "_") for col in columns]
    columns_sql = ', '.join([f'"{col}" TEXT' for col in columns])
    create_table_sql = f'''
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {columns_sql}
    )
    '''
    cursor.execute(create_table_sql)
    conn.commit()

## Function To Insert Data from DataFrame into Database
def insert_data_from_df(conn, df, table_name):
    cursor = conn.cursor()
    # Replace spaces with underscores in column names
    columns = df.columns
    columns = [col.replace(" ", "_") for col in columns]
    placeholders = ', '.join(['?'] * len(columns))
    insert_sql = f'''
    INSERT INTO {table_name} ({', '.join([f'"{col}"' for col in columns])})
    VALUES ({placeholders})
    '''
    for index, row in df.iterrows():
        cursor.execute(insert_sql, tuple(row))
    conn.commit()
    
## Function To Fetch Column Names from Database
def get_table_columns(db, table_name):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    return columns

## Function To Delete All Tables in the Database Except 'sqlite_sequence'
def delete_all_tables(db):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table_name in tables:
        if table_name[0] != 'sqlite_sequence':  # Skip 'sqlite_sequence' table
            cursor.execute(f'DROP TABLE IF EXISTS {table_name[0]};')
    conn.commit()
    conn.close()

## Streamlit App
st.set_page_config(page_title="SQL Query App")

# Table name input
table_name = st.text_input("Enter the table name:", value="DYNAMIC_TABLE")

# File uploader
st.title("Query your Excel")
uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

if uploaded_file is not None:
    # Delete existing tables in the database
    delete_all_tables('finance1.sqlite')

    # Read the Excel file
    df = pd.read_excel(uploaded_file)
    # Connect to SQLite database
    conn = sqlite3.connect('finance1.sqlite')

    # Create table dynamically based on column names
    create_table_from_df(conn, df, table_name)

    # Insert data into table
    insert_data_from_df(conn, df, table_name)

    # Close the connection
    conn.close()

    st.success("Data successfully imported into the database!")

# Query input
st.header("Ask a Question to Generate SQL Query")

if 'question' not in st.session_state:
    st.session_state.question = ""

question = st.text_input("Input: ", value=st.session_state.question)
submit = st.button("Ask the question")

if submit:
    # Save the question to session state
    st.session_state.question = question

    # Fetch columns from the database
    columns = get_table_columns("finance1.sqlite", table_name)

    # Construct dynamic prompt
    column_list = ', '.join(columns)
    prompt = f"""
You are an expert in converting English questions to SQL queries!
The SQL database has the name {table_name} and has the following columns: {', '.join([col.replace(" ", "_") for col in columns])}.

For example,
Example 1 - How many records are present?,
the SQL command will be something like this: SELECT COUNT(*) FROM {table_name};

Example 2 - List all records where [column_name]='value',
the SQL command will be something like this: SELECT * FROM {table_name} WHERE [column_name]='value';

Example 3 - What is the average of [column_name]?,
the SQL command will be something like this: SELECT AVG([column_name]) FROM {table_name};

Also, the SQL code should not have 
at the beginning or end, and avoid using the word "sql" in the output.
"""

    # Get the response from Google Gemini
    response = get_gemini_response(question, prompt)
    
    st.subheader("Your Question")
    st.write(question)  # Display the user's input
    
    st.subheader("Generated SQL Query")
    st.write(response)  # Display the generated SQL query

    # Retrieve query results from the database
    query_result = read_sql_query(response, "finance1.sqlite")

    st.subheader("Query Results")
    if query_result:
        for row in query_result:
            st.write(row)
    else:
        st.write("No results found.")
