import duckdb
import pandas as pd
import glob
import os
import json

# Kết nối tới database mới trên MotherDuck
con = duckdb.connect("md:youtube_analytics_lakehouse")

# Tạo schema Bronze
con.execute("create schema if not exists youtube_bronze")

# =========================
# 1. Load CSV video files
# =========================
csv_files = glob.glob("raw_youtube/*videos.csv")

if not csv_files:
    raise FileNotFoundError("Không tìm thấy file CSV trong thư mục raw_youtube")

all_dfs = []

for file in csv_files:
    country_code = os.path.basename(file)[:2].upper()
    print("Loading CSV:", file)

    df = pd.read_csv(file, encoding="latin1")
    df["country_code"] = country_code

    all_dfs.append(df)

videos_df = pd.concat(all_dfs, ignore_index=True)

con.execute("""
create or replace table youtube_bronze.raw_youtube_videos as
select * from videos_df
""")

# =========================
# 2. Load JSON category files
# =========================
json_files = glob.glob("raw_youtube/*_category_id.json")

if not json_files:
    raise FileNotFoundError("Không tìm thấy file JSON trong thư mục raw_youtube")

category_rows = []

for file in json_files:
    country_code = os.path.basename(file)[:2].upper()
    print("Loading JSON:", file)

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data["items"]:
        category_rows.append({
            "country_code": country_code,
            "category_id": int(item["id"]),
            "category_name": item["snippet"]["title"]
        })

category_df = pd.DataFrame(category_rows)

con.execute("""
create or replace table youtube_bronze.raw_youtube_categories as
select * from category_df
""")

# =========================
# 3. Check result
# =========================
print("DONE - Uploaded to MotherDuck database: youtube_analytics_lakehouse")

print(con.execute("""
select country_code, count(*) as total_rows
from youtube_bronze.raw_youtube_videos
group by country_code
order by country_code
""").df())

print(con.execute("""
select count(*) as total_categories
from youtube_bronze.raw_youtube_categories
""").df())

con.close()