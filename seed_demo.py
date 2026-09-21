import sqlite3
from app import DB_PATH, now

conn = sqlite3.connect(DB_PATH)
# Optional sample data. Run only if you want demonstration content.
conn.execute("""
INSERT INTO jobs(title,organization,category,description,eligibility,important_dates,official_url,created_at,updated_at,status)
VALUES(?,?,?,?,?,?,?,?,?,?)
""", (
    "Sample TN Government Job Update",
    "TnJobOrbit Demo",
    "TNPSC",
    "Replace this demo entry from the Admin Dashboard with a real notification.",
    "Add eligibility here.",
    "Add dates here.",
    "https://www.tnpsc.gov.in/",
    now(), now(), "published"
))
conn.commit()
conn.close()
print("Sample job added.")
