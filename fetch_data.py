import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# Step A: Load your secret API key from .env
load_dotenv()
NASA_API_KEY = os.getenv("NASA_API_KEY")

# Step B: Fetch disaster/event data from EONET (no key needed for this one)
print("Fetching EONET events...")
eonet_resp = requests.get(
    "https://eonet.gsfc.nasa.gov/api/v3/events",
    params={"status": "all", "limit": 2000}
)
events = eonet_resp.json()["events"]
print(f"Got {len(events)} events")

# Step C: Flatten events into rows, convert lat/lon to 3D coordinates
rows = []
category_list = []  # keep track of category names so we can number them

for e in events:
    cat_name = e["categories"][0]["title"] if e["categories"] else "Unknown"
    if cat_name not in category_list:
        category_list.append(cat_name)
    cat_id = category_list.index(cat_name)

    for g in e["geometry"]:
        if g["type"] != "Point":
            continue  # skip polygon-shaped events for simplicity
        lon, lat = g["coordinates"][0], g["coordinates"][1]
        t = datetime.fromisoformat(g["date"].replace("Z", "+00:00"))
        rows.append({
            "id": e["id"],
            "title": e["title"],
            "category": cat_name,
            "category_id": cat_id,
            "lat": lat,
            "lon": lon,
            "date": g["date"],
            "time": t.timestamp()
        })

df = pd.DataFrame(rows)
print(f"Flattened into {len(df)} point rows")

# Step D: Convert lat/lon into XYZ coordinates on a sphere
R = 100  # radius of our "globe" — arbitrary units ParaView will use
lat_r = np.radians(df["lat"])
lon_r = np.radians(df["lon"])
df["x"] = R * np.cos(lat_r) * np.cos(lon_r)
df["y"] = R * np.cos(lat_r) * np.sin(lon_r)
df["z"] = R * np.sin(lat_r)

# Step E: Use the NASA API key for something real — pull the
# Astronomy Picture of the Day for a handful of the most recent event dates.
# This demonstrates genuine api.nasa.gov key usage alongside EONET.
recent_dates = sorted(df["date"].unique())[-5:]  # last 5 unique dates in data
apod_lookup = {}

print("Fetching APOD images for sample dates using your API key...")
for date_str in recent_dates:
    date_only = date_str[:10]  # "2024-06-01T00:00:00Z" -> "2024-06-01"
    resp = requests.get(
        "https://api.nasa.gov/planetary/apod",
        params={"api_key": NASA_API_KEY, "date": date_only}
    )
    if resp.status_code == 200:
        apod_lookup[date_only] = resp.json().get("url", "")
    else:
        apod_lookup[date_only] = ""

df["date_only"] = df["date"].str[:10]
df["apod_url"] = df["date_only"].map(apod_lookup).fillna("")

# Step F: Save everything to a CSV file inside the data/ folder
output_path = "data/eonet_events.csv"
df.to_csv(output_path, index=False)
print(f"Saved {len(df)} rows to {output_path}")