# Import các thư viện cần dùng
# os: dùng để lấy biến môi trường như token
# duckdb: dùng để kết nối và ghi dữ liệu vào MotherDuck
# load_dataset: dùng để tải dataset từ Hugging Face
# login: dùng để đăng nhập Hugging Face bằng token nếu cần
import os
import duckdb
from datasets import load_dataset
from huggingface_hub import login


# Lấy MotherDuck Token và Hugging Face Token từ GitHub Secrets
MOTHERDUCK_TOKEN = os.getenv("MOTHERDUCK_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")


# Kiểm tra nếu chưa có MotherDuck Token thì báo lỗi
# Vì nếu không có token thì không thể kết nối tới MotherDuck
if not MOTHERDUCK_TOKEN:
    raise ValueError("Missing MOTHERDUCK_TOKEN. Please add it to GitHub Secrets.")


# Nếu có Hugging Face Token thì đăng nhập Hugging Face
# Một số dataset cần token mới tải được
if HF_TOKEN:
    login(token=HF_TOKEN)


# Tên database đã tạo trên MotherDuck
DATABASE_NAME = "ecommerce_lakehouse"


# Khai báo tên 2 bộ dữ liệu trên Hugging Face
# Bộ 1: dữ liệu hành vi duyệt web của khách hàng
BROWSING_DATASET = "electricsheepafrica/africa-synth-retail-and-ecommerce-browsing-behavior-logs-nigeria"

# Bộ 2: dữ liệu đơn hàng thương mại điện tử
ORDERS_DATASET = "electricsheepafrica/africa-synth-retail-and-ecommerce-ecommerce-order-data-nigeria"


# Hàm dùng để tải dataset từ Hugging Face và chuyển sang pandas DataFrame
def load_hf_dataset(dataset_name):
    # Tải dataset theo tên đã khai báo
    dataset = load_dataset(dataset_name)

    # Nếu dataset có split tên là "train" thì lấy split train
    if "train" in dataset:
        return dataset["train"].to_pandas()

    # Nếu không có split train thì lấy split đầu tiên trong dataset
    first_split = list(dataset.keys())[0]
    return dataset[first_split].to_pandas()


# Hàm chính để thực hiện quá trình nạp dữ liệu
def main():
    print("Connecting to MotherDuck...")

    # Kết nối tới database trên MotherDuck bằng DuckDB
    con = duckdb.connect(
        f"md:{DATABASE_NAME}?motherduck_token={MOTHERDUCK_TOKEN}"
    )

    # Tạo schema bronze nếu chưa tồn tại
    # Bronze là tầng lưu dữ liệu thô, chưa làm sạch, chưa biến đổi
    print("Creating bronze schema...")
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    # Tải bộ dữ liệu browsing behavior từ Hugging Face
    print("Loading browsing dataset from Hugging Face...")
    browsing_df = load_hf_dataset(BROWSING_DATASET)

    # Tải bộ dữ liệu order data từ Hugging Face
    print("Loading orders dataset from Hugging Face...")
    orders_df = load_hf_dataset(ORDERS_DATASET)

    # Đưa DataFrame browsing_df vào DuckDB để có thể dùng SQL xử lý
    print("Inserting browsing data into MotherDuck...")
    con.register("browsing_df", browsing_df)

    # Tạo hoặc ghi đè bảng bronze_browsing_logs trong schema bronze
    # Dữ liệu được nạp nguyên bản từ Hugging Face vào MotherDuck
    con.execute("""
        CREATE OR REPLACE TABLE bronze.bronze_browsing_logs AS
        SELECT * FROM browsing_df
    """)

    # Đưa DataFrame orders_df vào DuckDB để có thể dùng SQL xử lý
    print("Inserting orders data into MotherDuck...")
    con.register("orders_df", orders_df)

    # Tạo hoặc ghi đè bảng bronze_orders trong schema bronze
    # Đây là bảng chứa dữ liệu đơn hàng thô
    con.execute("""
        CREATE OR REPLACE TABLE bronze.bronze_orders AS
        SELECT * FROM orders_df
    """)

    # Đếm số dòng trong bảng browsing để kiểm tra dữ liệu đã nạp thành công chưa
    browsing_count = con.execute(
        "SELECT COUNT(*) FROM bronze.bronze_browsing_logs"
    ).fetchone()[0]

    # Đếm số dòng trong bảng orders để kiểm tra dữ liệu đã nạp thành công chưa
    orders_count = con.execute(
        "SELECT COUNT(*) FROM bronze.bronze_orders"
    ).fetchone()[0]

    # In thông báo hoàn tất quá trình nạp dữ liệu
    print("Ingestion completed successfully!")
    print(f"bronze_browsing_logs rows: {browsing_count}")
    print(f"bronze_orders rows: {orders_count}")

    # Đóng kết nối tới MotherDuck
    con.close()


# Chạy hàm main khi file ingest.py được thực thi
if __name__ == "__main__":
    main()
