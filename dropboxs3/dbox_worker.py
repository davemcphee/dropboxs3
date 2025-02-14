import dropbox


class DBoxWorker:
    def __init__(self, app_key, app_secret, refresh_token, auto_login=False) -> None:

        self.app_key = app_key
        self.app_secret = app_secret
        self.refresh_token = refresh_token
        self.dbx = None

        if auto_login:
            self.dbx = self._get_dbx()

    def _get_dbx(self) -> dropbox.Dropbox:
        return dropbox.Dropbox(
            app_key=self.app_key,
            app_secret=self.app_secret,
            oauth2_refresh_token=self.refresh_token,
        )

    def get_images(self, path="/camera uploads"):
        return self.dbx.files_list_folder(path)

    @staticmethod
    def generate_s3_path_chunk(image):
        # dbox only knows how to convert datetime to sub path, s3 upload handles
        # bucket and parent dir(s)
        img_name = image.name.replace(" ", "_")
        img_date = image.client_modified
        s3_path = f"{img_date.year}/{str(img_date.month).zfill(2)}/{img_name}"
        return s3_path

    def get_file_from_dbox(self, image):
        path = image.path_lower
        md, f = self.dbx.files_download(path)
        return md, f.content

    def delete_file_from_dbox(self, image):
        # deletes a dbox image object
        return self.dbx.files_delete_v2(image.path_lower)
