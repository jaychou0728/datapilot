import pandas as pd
from pathlib import Path

class ParseError(Exception):
    pass

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
ENCODINGS = ["utf-8", "gbk", "gb2312", "latin-1"]

def parse_file(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ParseError(f"不支持的文件格式: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}")

    if ext == ".csv":
        df = _read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    if df.empty:
        raise ParseError("文件中没有数据")

    df.columns = [str(col).strip() for col in df.columns]
    return df

def _read_csv(file_path: str) -> pd.DataFrame:
    for enc in ENCODINGS:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ParseError("无法识别文件编码，请将文件保存为 UTF-8 格式")
