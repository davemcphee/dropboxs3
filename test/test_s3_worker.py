import pytest

from dropboxs3 import S3Worker


@pytest.fixture
def s3w():
    s3w = S3Worker(key='123456', secret='xxx', bucket='bucket', path='none', auto_login=False)
    return s3w


def test_truth():
    assert True


def test_check_if_uploaded(s3w):
    assert s3w.check_if_uploaded('image') is False

