import uuid
from supabase import create_client, Client
from datetime import datetime

url = "https://jjfvrabgqxzdrzkybgvi.supabase.co"  # your Supabase project URL
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpqZnZyYWJncXh6ZHJ6a3liZ3ZpIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTQ5ODcxNCwiZXhwIjoyMDc3MDc0NzE0fQ.zH--_gKxaEgTGU6U6xIWLvUE49xMm3wpVq1fxmvjn_k"  # get this from Supabase Settings → API → Service Role Key

supabase: Client = create_client(url, key)


data = {
    "punch_type": "jab",
    "punch_hand": "left",
    "impact_force": 325.5,
    "punch_velocity": 13.8
}

result = supabase.table("punches").insert(data).execute()
print("✅ Data sent:", result)
