from app.database.connection import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        vote_id UUID PRIMARY KEY,
        product_a_id TEXT NOT NULL,
        product_b_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        votes_a INTEGER DEFAULT 0,
        votes_b INTEGER DEFAULT 0
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS vote_choices (
        id SERIAL PRIMARY KEY,
        vote_id UUID NOT NULL REFERENCES votes(vote_id),
        voter_token TEXT NOT NULL,
        choice CHAR(1) NOT NULL CHECK (choice IN ('A', 'B')),
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(vote_id, voter_token)
    )
""")

conn.commit()
cursor.close()
conn.close()

print("Oylama tabloları oluşturuldu.")
