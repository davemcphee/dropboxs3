#!/usr/bin/env python3

import dropbox


class DBoxWorker(object):
    def __init__(self, db_api_key=None,
                 celery=False,
                 auto_login=False):

        self.db_api_key = db_api_key
        self.celery     = celery
        self.auto_login = auto_login
        self.dbx        = None

        if not any([db_api_key]):
            raise ValueError('missing required args')

        if self.auto_login:
            self.dbx = self._get_dbx()

    def _get_dbx(self):
        try:
            dbx = dropbox.Dropbox(self.db_api_key)
        except Exception:
            raise
        return dbx

    def get_images(self, path='/camera uploads'):
        try:
            files = self.dbx.files_list_folder(path)
        except Exception:
            raise
        return files

    @staticmethod
    def generate_s3_path_chunk(image):
        # dbox only knows how to convert datetime to sub path, s3 upload handles
        # bucket and parent dir(s)
        img_name = image.name.replace(' ', '_')
        img_date = image.client_modified
        s3_path = f'{img_date.year}/{str(img_date.month).zfill(2)}/{img_name}'
        return s3_path

    def get_file_from_dbox(self, image):
        path = image.path_lower
        try:
            md, f = self.dbx.files_download(path)
        except Exception:
            raise
        return md, f.content

    def delete_file_from_dbox(self, image):
        # takes a dbox image object
        try:
            self.dbx.files_delete_v2(image.path_lower)
        except Exception:
            raise
