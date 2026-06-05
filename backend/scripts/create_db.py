"""Crea la base de datos proyecto_terminal_cyad si no existe."""

import sys
from pathlib import Path

# Permite importar decouple desde el directorio del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decouple import config
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

db_name = config("DB_NAME", default="proyecto_terminal_cyad")
db_user = config("DB_USER", default="postgres")
db_password = config("DB_PASSWORD", default="postgres")
db_host = config("DB_HOST", default="localhost")
db_port = config("DB_PORT", default="5432")

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if cur.fetchone():
        print(f"La base de datos '{db_name}' ya existe.")
    else:
        cur.execute(f'CREATE DATABASE "{db_name}"')
        print(f"Base de datos '{db_name}' creada exitosamente.")

    cur.close()
    conn.close()
    print("Conexión a PostgreSQL: OK")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
