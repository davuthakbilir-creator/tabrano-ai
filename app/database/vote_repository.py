import psycopg

from app.database.connection import get_connection



def create_vote(vote_id, product_a_id, product_b_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO votes (vote_id, product_a_id, product_b_id)
        VALUES (%s, %s, %s)
    """, (
        str(vote_id),
        product_a_id,
        product_b_id
    ))

    conn.commit()

    cursor.close()
    conn.close()




def get_vote(vote_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            vote_id,
            product_a_id,
            product_b_id,
            created_at,
            votes_a,
            votes_b

        FROM votes

        WHERE vote_id = %s
    """, (str(vote_id),))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row




def record_choice(vote_id, choice, voter_token):
    """Oy kaydeder. Aynı (vote_id, voter_token) ikinci kez oy kullanmaya
    çalışırsa UNIQUE constraint devreye girer ve False döner."""

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            INSERT INTO vote_choices (vote_id, voter_token, choice)
            VALUES (%s, %s, %s)
        """, (
            str(vote_id),
            voter_token,
            choice
        ))

        column = "votes_a" if choice == "A" else "votes_b"

        cursor.execute(f"""
            UPDATE votes
            SET {column} = {column} + 1
            WHERE vote_id = %s
        """, (str(vote_id),))

        conn.commit()
        recorded = True

    except psycopg.errors.UniqueViolation:

        conn.rollback()
        recorded = False

    finally:

        cursor.close()
        conn.close()

    return recorded




def get_voter_choice(vote_id, voter_token):

    if not voter_token:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT choice
        FROM vote_choices
        WHERE vote_id = %s AND voter_token = %s
    """, (
        str(vote_id),
        voter_token
    ))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row[0] if row else None
