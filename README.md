Arch
====

given a list of (dropbox_API, s3_api), pull list of files in DB/camera uploads

celery beat creates a scheduled task to clean out files from db account and writes them to S3.

Each schedule needs:
* DB API key
* S3 key, secret, bucket_name, bucket_key_path

where should a set of configs come from? DB? yaml?

yaml config:
###
redis:
  broker_url: redis://redis//
  backend_url: redis://redis

beat_configs:
  - alexs:
    db_api: ""
    s3_key: ""
    s3_secret: ""
    s3_bucket: ""
    s3_key_path: ""
###

