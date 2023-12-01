
import pandas as pd

def check_definitions(path_to_definitions_as_parquet_file):
    df_definitions_all = pd.read_parquet(path_to_definitions_as_parquet_file, engine='pyarrow')
    assert len(df_definitions_all.columns) == 3

    expected_columns = ['Definition', 'source', 'Embedding']
    for column_heading in df_definitions_all.columns:
        assert column_heading in expected_columns

def check_index(path_to_index_as_parquet_file):
    df_text_all = pd.read_parquet(path_to_index_as_parquet_file, engine='pyarrow')
    assert len(df_text_all.columns) == 4
    expected_columns = ["section", "text", "source", "Embedding"]
    for column_heading in df_text_all.columns:
        assert column_heading in expected_columns


def test_data():

    # Make sure that when you load the manual, there are no NaN values
    df = pd.read_csv("./inputs/ad_manual.csv", sep='|', encoding="utf-8", na_filter=False)
    assert not df.isna().any().any()
    df = pd.read_csv("./inputs/adla_manual.csv", sep='|', encoding="utf-8", na_filter=False)
    assert not df.isna().any().any()

    path_to_definitions_as_parquet_file = "./inputs/ad_definitions.parquet"
    check_definitions(path_to_definitions_as_parquet_file)
    path_to_definitions_as_parquet_file = "./inputs/adla_definitions.parquet"
    check_definitions(path_to_definitions_as_parquet_file)

    path_to_index_as_parquet_file = "./inputs/ad_index.parquet"
    check_index(path_to_index_as_parquet_file)
    path_to_index_as_parquet_file = "./inputs/adla_index.parquet"
    check_index(path_to_index_as_parquet_file)