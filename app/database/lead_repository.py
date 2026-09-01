from app.database.connection import get_connection



def ensure_leads_table():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            consent_kvkk BOOLEAN NOT NULL DEFAULT FALSE,
            consent_marketing BOOLEAN NOT NULL DEFAULT FALSE,
            consent_version TEXT,
            consent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cursor.execute("""
        ALTER TABLE leads
            ADD COLUMN IF NOT EXISTS consent_kvkk BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS consent_marketing BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS consent_version TEXT,
            ADD COLUMN IF NOT EXISTS consent_at TIMESTAMP
    """)

    conn.commit()

    cursor.close()
    conn.close()




def create_lead(
    full_name,
    phone,
    consent_kvkk,
    consent_marketing,
    consent_version
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO leads (
            full_name,
            phone,
            consent_kvkk,
            consent_marketing,
            consent_version,
            consent_at
        )
        VALUES (%s, %s, %s, %s, %s, NOW())
        RETURNING id, created_at
    """, (
        full_name,
        phone,
        consent_kvkk,
        consent_marketing,
        consent_version
    ))

    lead_id, created_at = cursor.fetchone()

    conn.commit()

    cursor.close()
    conn.close()

    return lead_id, created_at
