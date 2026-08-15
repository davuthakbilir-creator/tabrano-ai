from connection import get_connection

conn = get_connection()

print("✅ PostgreSQL bağlantısı başarılı!")

conn.close()