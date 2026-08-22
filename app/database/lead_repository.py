from app.database.connection import get_connection



def ensure_leads_table():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()

    cursor.close()
    conn.close()




def create_lead(full_name, phone):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO leads (full_name, phone)
        VALUES (%s, %s)
        RETURNING id, created_at
    """, (
        full_name,
        phone
    ))

    lead_id, created_at = cursor.fetchone()

    conn.commit()

    cursor.close()
    conn.close()

    return lead_id, created_at
