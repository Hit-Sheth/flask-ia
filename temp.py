import sqlite3

DATABASE = "ia.db"

conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row 
cursor = conn.cursor()

# Insert data into exam_taker table
# cursor.execute('''
# delete from exam_taker;
# ''')
# cursor.execute('''
# delete from test_questions;
# ''')
# cursor.execute('''delete from test_response;''')
# cursor.execute('''
# delete from tests;
# ''')
cursor.execute('''
   alter table test_response add test_id
''')
conn.commit()
conn.close()

print("Data inserted successfully.")