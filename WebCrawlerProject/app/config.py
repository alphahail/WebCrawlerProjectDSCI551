import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Was getting some annoying issues with trying to access this from the other folder sometimes, copied here for simplicity
DB_CONFIG = {
    "host":     "db.pygprovpytqbhbguqtvv.supabase.co",
    "port":     5432,
    "dbname":   "postgres",
    "user":     "postgres",
    "password": "7qN5YfX6PEbHKE7W",
    "sslmode":  "require",
}

LOCAL_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "stories",
    "user":     "postgres",
    "password": "password", # Change this to whatever your postgreSQL local password is
}

# Flask settings
HOST = "0.0.0.0"   
PORT = 5000
DEBUG = True
