import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS personajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    experiencia INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS misiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    experiencia INTEGER DEFAULT 0,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS misiones_personaje (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personaje_id INTEGER,
    mision_id INTEGER,
    orden INTEGER,
    estado BOOLEAN DEFAULT 0,
    FOREIGN KEY (personaje_id) REFERENCES personajes(id),
    FOREIGN KEY (mision_id) REFERENCES misiones(id)
)
""")

conn.commit()
conn.close()
