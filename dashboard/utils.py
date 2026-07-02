"""
utils.py
Các hàm tiện ích dùng chung cho toàn bộ dashboard.
"""
import json

DOW_NAMES = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]


def find_col(df, candidates):
    """Dò cột tồn tại đầu tiên trong danh sách ứng viên
    (đề phòng schema đặt tên cột khác so với dự kiến)."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def to_j(obj):
    """Serialize object Python sang chuỗi JSON để nhúng vào JS trong iframe."""
    return json.dumps(obj)