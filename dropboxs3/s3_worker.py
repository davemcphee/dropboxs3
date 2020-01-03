#!/usr/bin/env python3

import boto3


class S3Worker(object):
    def __init__(self, key=None, secret=None, bucket=None, path=None, auto_login=False):
        self.key        = key
        self.secret     = secret
        self.bucket     = bucket
        self.path       = path
        self.auto_login = auto_login
        self.client     = None

        if self.auto_login:
            assert all([key, secret, bucket, path])
            self.client = self._get_client()

        if not self.path.endswith('/'):
            self.path += '/'

    def _get_client(self):
        try:
            return boto3.client('s3', aws_access_key_id=self.key, aws_secret_access_key=self.secret)
        except Exception:
            raise

    def check_if_uploaded(self, image):
        # given an image from DB, has it already been uploaded?
        return False

    def upload_to_s3(self, image_bytes, path, check=False):
        full_path = self.path + path
        # image is a requests.model.con
        if check:
            if self.check_if_uploaded(full_path):
                return
        try:
            self.client.put_object(Bucket=self.bucket, Key=full_path, Body=image_bytes)
        except Exception:
            raise
