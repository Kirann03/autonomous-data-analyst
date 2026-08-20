import pandas as pd
import pytest

from etl.extract import extract_csv


def test_extract_csv_reads_a_csv_file(tmp_path):
    source = tmp_path / "sales.csv"
    source.write_text("product,quantity\nWidget,2\n", encoding="utf-8")
    result = extract_csv(source)
    pd.testing.assert_frame_equal(result, pd.DataFrame({"product": ["Widget"], "quantity": [2]}))


def test_extract_csv_rejects_a_non_csv_file(tmp_path):
    source = tmp_path / "sales.xlsx"
    source.write_text("not an Excel file", encoding="utf-8")
    with pytest.raises(ValueError, match="Only CSV"):
        extract_csv(source)
