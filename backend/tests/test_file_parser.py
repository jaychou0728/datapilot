import pytest
import pandas as pd
from app.utils.file_parser import parse_file, ParseError

def test_parse_csv_utf8(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("name,age\nAlice,30\nBob,25", encoding="utf-8")
    df = parse_file(str(csv_path))
    assert list(df.columns) == ["name", "age"]
    assert len(df) == 2
    assert df["age"].dtype == "int64"

def test_parse_xlsx(tmp_path):
    xlsx_path = tmp_path / "test.xlsx"
    df_input = pd.DataFrame({"name": ["Alice"], "score": [95.5]})
    df_input.to_excel(str(xlsx_path), index=False)
    df = parse_file(str(xlsx_path))
    assert list(df.columns) == ["name", "score"]
    assert len(df) == 1

def test_parse_csv_gbk(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("姓名,年龄\n张三,28", encoding="gbk")
    df = parse_file(str(csv_path))
    assert "姓名" in df.columns

def test_unsupported_extension(tmp_path):
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("hello")
    with pytest.raises(ParseError, match="不支持的文件格式"):
        parse_file(str(txt_path))

def test_empty_csv(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("name,age\n")
    with pytest.raises(ParseError, match="文件中没有数据"):
        parse_file(str(csv_path))
