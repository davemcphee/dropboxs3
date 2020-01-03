import datetime
import pytest
from collections import namedtuple

# from unittest.mock import Mock

from dropboxs3 import DBoxWorker


@pytest.fixture
def dbw():
    return DBoxWorker(db_api_key='asdf', auto_login=False)


def test_truth():
    assert True


def test_raises():
    with pytest.raises(ValueError):
        DBoxWorker()


def test_setup(dbw):
    assert dbw


def test_s3_path(dbw):
    file_name = '2019-04-24 15.11.32.mp4'
    file_date = datetime.datetime(2019, 4, 24, 15, 11, 21)
    desired_output = '2019/04/2019-04-24_15.11.32.mp4'

    DBoxImage = namedtuple('image', ['name', 'client_modified'])

    image = DBoxImage(file_name, file_date)

    assert dbw.generate_s3_path_chunk(image) == desired_output
