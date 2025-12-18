import psycopg2

print("SCRIPT STARTED")

def main():
    print("CONNECTING...")
    conn = psycopg2.connect(
        "postgres://avnadmin:AVNS_suApGTQmnYdC8q4U-32@kpi-events-4all-kpi-alumni-events4all.g.aivencloud.com:20391/defaultdb?sslmode=require"
    )

    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]

    print("CONNECTED OK")
    print(version)

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
