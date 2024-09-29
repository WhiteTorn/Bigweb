from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2 import sql

app = Flask(__name__)


# PostgreSQL connection settings
def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="books",
        user="postgres",
        password="pos123"
    )
    return conn


# Check which columns exist in the table
def get_columns_in_table(cursor, table_name):
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s;
    """, (table_name,))
    columns = cursor.fetchall()
    return {col[0].lower(): col[0] for col in columns}  # Return a dict of lowercase -> actual case column names


CUSTOM_TABLE_ORDER = [
    "biblusi_author",
    "sulakauri",
    "palitral_author"
    # Add any other table names in the order you prefer
]


# Function to sort tables based on custom order
def sort_tables(tables):
    def get_table_index(table):
        try:
            return CUSTOM_TABLE_ORDER.index(table[0])
        except ValueError:
            return len(CUSTOM_TABLE_ORDER)  # Put tables not in the custom order at the end

    return sorted(tables, key=get_table_index)



# Home route to render the page
@app.route('/')
def home():
    return render_template('index.html')


# Route to handle search queries with a limit
@app.route('/search', methods=['POST'])
def search():
    data = request.json
    search_term = data.get('query')
    search_type = data.get('search_type')
    conn = get_db_connection()
    cursor = conn.cursor()

    results_limit = 15

    if search_type == 'title':
        results = search_title(cursor, search_term, results_limit)
    elif search_type == 'author':
        results = search_author(cursor, search_term, results_limit)
    else:
        results = []  # Handle invalid search_type

    conn.close()
    return jsonify(results)


def search_title(cursor, search_term, results_limit):
    # Get all table names in the public schema
    cursor.execute("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public';
                """)
    tables = cursor.fetchall()

    all_results = []

    sorted_tables = sort_tables(tables)

    # Loop through each table to find matching titles
    for table in sorted_tables:
        table_name = table[0]

        # Get the columns in the current table
        columns_in_table = get_columns_in_table(cursor, table_name)

        # Skip the table if it doesn't have the "Title" column
        if 'title' not in columns_in_table:
            continue

        # Prepare the dynamic query based on the available columns
        select_columns = [columns_in_table['title']]  # Always include the Title column

        # Dynamically append columns if they exist, otherwise append 'NULL AS' placeholders
        if 'author' in columns_in_table:
            select_columns.append(columns_in_table['author'])
        else:
            select_columns.append(sql.SQL('NULL AS Author'))  # NULL placeholder for missing Author

        if 'price' in columns_in_table:
            select_columns.append(columns_in_table['price'])
        else:
            select_columns.append(sql.SQL('NULL AS Price'))  # NULL placeholder for missing Price

        if 'url' in columns_in_table:
            select_columns.append(columns_in_table['url'])
        else:
            select_columns.append(sql.SQL('NULL AS URL'))  # NULL placeholder for missing URL

        # Build the query dynamically using the correct column names or NULL placeholders
        query = sql.SQL("SELECT {} FROM {} WHERE {} ILIKE %s LIMIT %s").format(
            sql.SQL(', ').join([sql.Identifier(col) if isinstance(col, str) else col for col in select_columns]),
            # Use correct column names or placeholders
            sql.Identifier(table_name),
            sql.Identifier(columns_in_table['title'])  # Use the actual case for "Title"
        )

        cursor.execute(query, (f'%{search_term}%', results_limit))
        results = cursor.fetchall()

        if results:
            # Add results from the current table to all_results
            all_results.append({
                'table_name': table_name.capitalize(),  # Capitalize the table name
                'books': [{'title': row[0], 'author': row[1], 'price': row[2], 'url': row[3]} for row in results]
            })



    # Return the results as JSON to the frontend
    return all_results


def search_author(cursor, search_term, results_limit):
    # Get all table names in the public schema
    cursor.execute("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public';
                """)
    tables = cursor.fetchall()

    all_results = []

    sorted_tables = sort_tables(tables)

    # Loop through each table to find matching titles
    for table in sorted_tables:
        table_name = table[0]

        # Get the columns in the current table
        columns_in_table = get_columns_in_table(cursor, table_name)

        # Skip the table if it doesn't have the "Title" column
        if 'author' not in columns_in_table:
            continue

        # Prepare the dynamic query based on the available columns
        select_columns = [columns_in_table['title']]  # Always include the Title column

        # Dynamically append columns if they exist, otherwise append 'NULL AS' placeholders
        if 'author' in columns_in_table:
            select_columns.append(columns_in_table['author'])
        else:
            select_columns.append(sql.SQL('NULL AS Author'))  # NULL placeholder for missing Author

        if 'price' in columns_in_table:
            select_columns.append(columns_in_table['price'])
        else:
            select_columns.append(sql.SQL('NULL AS Price'))  # NULL placeholder for missing Price

        if 'url' in columns_in_table:
            select_columns.append(columns_in_table['url'])
        else:
            select_columns.append(sql.SQL('NULL AS URL'))  # NULL placeholder for missing URL

        # Build the query dynamically using the correct column names or NULL placeholders
        query = sql.SQL("SELECT {} FROM {} WHERE {} ILIKE %s LIMIT %s").format(
            sql.SQL(', ').join([sql.Identifier(col) if isinstance(col, str) else col for col in select_columns]),
            # Use correct column names or placeholders
            sql.Identifier(table_name),
            sql.Identifier(columns_in_table['author'])  # Use the actual case for "Title"
        )

        cursor.execute(query, (f'%{search_term}%', results_limit))
        results = cursor.fetchall()

        if results:
            # Add results from the current table to all_results
            all_results.append({
                'table_name': table_name.capitalize(),  # Capitalize the table name
                'books': [{'title': row[0], 'author': row[1], 'price': row[2], 'url': row[3]} for row in results]
            })

    # Return the results as JSON to the frontend
    return all_results

# Route to handle fetching 5 random books from each table
@app.route('/random_books', methods=['POST'])
def random_books():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all table names in the public schema
    cursor.execute("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public';
                """)
    tables = cursor.fetchall()

    all_results = []

    # Limit the number of results per table
    results_limit = 5

    # Loop through each table to get random books
    for table in tables:
        table_name = table[0]

        # Get the columns in the current table
        columns_in_table = get_columns_in_table(cursor, table_name)

        # Skip the table if it doesn't have the "Title" column
        if 'title' not in columns_in_table:
            continue

        # Prepare the dynamic query based on the available columns
        select_columns = [columns_in_table['title']]  # Always include the Title column

        # Dynamically append columns if they exist, otherwise append 'NULL AS' placeholders
        if 'author' in columns_in_table:
            select_columns.append(columns_in_table['author'])
        else:
            select_columns.append(sql.SQL('NULL AS Author'))  # NULL placeholder for missing Author

        if 'price' in columns_in_table:
            select_columns.append(columns_in_table['price'])
        else:
            select_columns.append(sql.SQL('NULL AS Price'))  # NULL placeholder for missing Price

        if 'url' in columns_in_table:
            select_columns.append(columns_in_table['url'])
        else:
            select_columns.append(sql.SQL('NULL AS URL'))  # NULL placeholder for missing URL

        # Build the query dynamically using the correct column names or NULL placeholders
        query = sql.SQL("SELECT {} FROM {} ORDER BY RANDOM() LIMIT %s").format(
            sql.SQL(', ').join([sql.Identifier(col) if isinstance(col, str) else col for col in select_columns]),
            # Use correct column names or placeholders
            sql.Identifier(table_name)
        )

        cursor.execute(query, (results_limit,))
        results = cursor.fetchall()

        if results:
            # Add results from the current table to all_results
            all_results.append({
                'table_name': table_name.capitalize(),  # Capitalize the table name
                'books': [{'title': row[0], 'author': row[1], 'price': row[2], 'url': row[3]} for row in results]
            })

    conn.close()

    # Return the results as JSON to the frontend
    return jsonify(all_results)


if __name__ == '__main__':
    app.run(debug=True)