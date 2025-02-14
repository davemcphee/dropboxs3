from unittest import TestCase, mock
import datetime
import pytest
from collections import namedtuple

import responses

from dropboxs3.dbox_worker import DBoxWorker
from dropbox.files import ListFolderResult, FileMetadata, PhotoMetadata, Dimensions
from dropbox.stone_validators import Union as StoneValidatorUnion

IMAGE_PATH = "/camera uploads/2020-01-05 21.39.05.jpg"

FILE_ENTRY = {
    ".tag": "file",
    "client_modified": f"{datetime.datetime(2020, 1, 6, 3, 39, 5).strftime('%Y-%m-%dT%H:%M:%SZ')}",
    "id": "id:0I34Sg0NuugAAAAAAAEJcg",
    "name": "2020-01-05 21.39.05.jpg",
    "path_lower": IMAGE_PATH,
    "rev": "59b70671fa8b501c386a6",
    "server_modified": f"{datetime.datetime(2020, 1, 9, 3, 39, 5).strftime('%Y-%m-%dT%H:%M:%SZ')}",
    "size": 12345,
}


class TestDBoxWorker(TestCase):
    def setUp(self):
        responses.add(
            responses.POST,
            "https://api.dropboxapi.com/oauth2/token",
            json={"access_token": "fake_token", "expires_in": "1836102896"},
            status=201,
        )
        responses.add(
            responses.POST,
            "https://api.dropboxapi.com/2/files/list_folder",
            json={
                "entries": [FILE_ENTRY],
                "cursor": "fake_cursor",
                "has_more": False,
            },
            status=201,
        )
        responses.add(
            responses.POST,
            "https://content.dropboxapi.com/2/files/download",
            headers={"dropbox-api-result": "{\"foo\": \"bar\""},
            json={

            },
            status=201,
        )

    def test_autologin(self):
        db = DBoxWorker(None, None, None, auto_login=False)
        self.assertIsNone(db.dbx)

    def test_get_dbx(self):
        db = DBoxWorker(
            app_key="fake_key",
            app_secret="fake_secret",
            refresh_token="fake_refresh_token",
            auto_login=True,
        )
        self.assertIsNotNone(db.dbx)

    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    @responses.activate
    def test_get_images(self):
        db = DBoxWorker(
            app_key="fake_key",
            app_secret="fake_secret",
            refresh_token="fake_refresh_token",
            auto_login=True,
        )

        # we should get a single image from the fake JSON FILE_ENTRY
        images = db.get_images(path="/fake_path")
        self.assertEqual(1, len(images.entries))

    @responses.activate
    def test_get_file_from_dbox(self):
        db = DBoxWorker(
            app_key="fake_key",
            app_secret="fake_secret",
            refresh_token="fake_refresh_token",
            auto_login=True,
        )

        FakeImageObj = namedtuple("fake_image", ["path_lower"])
        fake_image = FakeImageObj(IMAGE_PATH)
        image = db.get_file_from_dbox(fake_image)
        self.assertTrue(False)



"""
POST https://api.dropboxapi.com/oauth2/token
https://api.dropboxapi.com/2/files/list_folder
"""
