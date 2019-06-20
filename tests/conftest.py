from os import listdir, path
from pathlib import Path

import petl as etl
import pytest

# -------------------------------------
# CONSTANTS

TEST_DATA_DIR = Path(path.dirname(path.abspath(__file__))) / "data"
TEST_CSVS = [str(TEST_DATA_DIR / i) for i in listdir(str(TEST_DATA_DIR))]

TEST_CSV_10min = TEST_DATA_DIR / "results_10min.csv"
TEST_CSV_24hr = TEST_DATA_DIR / "results_24hr.csv"

@pytest.fixture
def read_test_calculator_inputs():
    """read test calculator results into dictionaries for the purposes of testing
    """

    # test_csvs = {
    #     "10-min": TEST_CSV_10min
    #     "24-hr": TEST_CSV_24hr
    # }

    # test_data = {}
    # for duration, table_path in test_csvs:
    #     t = etl.fromcsv(table_path).dicts()
    #     test_data[duration] = {
            
    #     }
    pass