import datetime
import pytest
from collections import namedtuple

from unittest.mock import Mock

from dropboxs3 import DBoxWorker

from dropbox.files import ListFolderResult, FileMetadata, PhotoMetadata, Dimensions
from dropbox.stone_validators import Union as StoneValidatorUnion


IMAGE = FileMetadata(name='2020-01-05 21.39.05.jpg', id='id:0I34Sg0NuugAAAAAAAEJcg',
                     client_modified=datetime.datetime(2020, 1, 6, 3, 39, 5),
                     server_modified=datetime.datetime(2020, 1, 6, 3, 39, 12),
                     rev='59b70671fa8b501c386a6', size=3555594,
                     path_lower='/camera uploads/2020-01-05 21.39.05.jpg',
                     path_display='/Camera Uploads/2020-01-05 21.39.05.jpg',
                     parent_shared_folder_id=None, media_info=None, symlink_info=None, sharing_info=None,
                     is_downloadable=True, export_info=None, property_groups=None,
                     has_explicit_shared_members=None,
                     content_hash='e76e398626b42825f4d98247d9e72677444891078ecba06f334d7ec22825f475')

PHOTO_METADATA = PhotoMetadata(dimensions=Dimensions(height=4032, width=3024), location=None,
                               time_taken=datetime.datetime(2020, 1, 5, 21, 37, 5))

LIST_FOLDER_RESULTS = ListFolderResult(entries=[IMAGE],
                                       cursor='AAGU8Pk5ogR7MpsoWS1JYd8Cug6oYTd6eiUCZp74F3thzZ2N5UL3b3XErdXETFg0J3vSB_nTKcGZ1zbXVsCM4DCx-4ISMswTL2M0NShmLn6k5-4yaV8dJUR2iw9-TZjJdQhHcUzI9bzrS_uY89W9XPJUPUo83akRND28IY0_NAWcSJnR4OjIQTp3B3MH8mz-cFNxuH6ruuD1Xu1Idox-9h5aBZiyjgvXCioS_wMMkaDlhw', has_more=False)


@pytest.fixture
def dbw():
    def mocked_dropbox_api(*args, **kwargs):
        class MockedDBX:
            def __init__(self, api_key):
                self.stuff = api_key

            def files_list_folder(self, path):
                return LIST_FOLDER_RESULTS

            def files_download(self, path):
                md = IMAGE
                md.media_info = PHOTO_METADATA
                Request_Content = namedtuple('ReqContent', ['content'])
                photo_bytez = Request_Content(bytes('some random string', 'utf-8'))
                return md, photo_bytez

        return MockedDBX('api_key')

    dbw = DBoxWorker(db_api_key='asdf', auto_login=False)

    StoneValidatorUnion.validate_type_only = Mock()

    dbw.dbx = mocked_dropbox_api()  # Mock(side_effect=mocked_dropbox_api)
    return dbw


def test_truth():
    assert True


def test_raises():
    with pytest.raises(ValueError):
        DBoxWorker()


def test_setup(dbw):
    assert dbw


def test_generate_s3_path_chunk_no_md(dbw):
    file_name = '2019-04-24 15.11.32.mp4'
    file_date = datetime.datetime(2019, 4, 24, 15, 11, 21)
    desired_output = '2019/04/2019-04-24_15.11.32.mp4'
    DBoxImage = namedtuple('image', ['name', 'client_modified'])
    image = DBoxImage(file_name, file_date)
    assert dbw.generate_s3_path_chunk(IMAGE) == '2020/01/2020-01-05_21.39.05.jpg'


def test_get_images(dbw):
    get_images_result = dbw.get_images()
    assert hasattr(get_images_result, 'entries')
    assert isinstance(get_images_result.entries, list)
    assert get_images_result.entries[0].name == '2020-01-05 21.39.05.jpg'


def test_get_file_from_dbox(dbw):
    md, image_bytes = dbw.get_file_from_dbox(IMAGE)
    assert hasattr(md, 'media_info')
