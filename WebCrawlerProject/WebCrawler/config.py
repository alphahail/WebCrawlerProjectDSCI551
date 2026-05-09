BASE_URL = "https://forums.spacebattles.com"

CREATIVE_WRITING_URL = f"{BASE_URL}/forums/creative-writing.18/?order=last_threadmark&direction=desc&nodes[0]=48&nodes[1]=115"

DB_CONFIG = {
    "host":     "db.pygprovpytqbhbguqtvv.supabase.co",
    "port":     5432,
    "dbname":   "postgres",
    "user":     "postgres",
    "password": "7qN5YfX6PEbHKE7W",   # Change this if we change the password, this will be changed after 2 months after submission
    "sslmode":  "require",
}

LOCAL_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "stories",
    "user":     "postgres",
    "password": "password", # Change this to whatever your postgreSQL local password is
}
# The Supabase database isn't that important, its not linked to anything major and its free so the password is staying here for simplicity

# Delay in Seconds, do not adjust the lower bound any lower, we don't want to spam ping the website and flood them with traffic. 
# Yes, this will be slower, but we cannot be disrespectful in this manner. Also, make sure there is at least a 0.5-1 second gap between
# min and max, or we might trigger the antibot stuff that is meant to target actual bots, not crawlers. Maybe not necessary, but I can't
# find proof that this protection wouldn't hit us, so its safer this way. 
CRAWL_DELAY = (2.0, 5.0)
TEST_DELAY  = (1.0, 2.0)

