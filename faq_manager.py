import sqlite3

# Initialize SQLite database with a specific name
def init_db(db_name="faqs.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            question TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Add or update FAQ count in a specific database
def log_faq(question, db_name="faqs.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO faqs (question, count)
        VALUES (?, 1)
        ON CONFLICT(question)
        DO UPDATE SET count = count + 1
    ''', (question,))
    conn.commit()
    conn.close()

# Get top FAQs from a specific database
def get_top_faqs(limit=5, db_name="faqs.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT question FROM faqs
        ORDER BY count DESC
        LIMIT ?
    ''', (limit,))
    faqs = [row[0] for row in cursor.fetchall()]
    conn.close()
    return faqs
