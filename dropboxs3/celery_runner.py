import logging
import math
import os
import random
import sys
from hashlib import md5
from pathlib import Path

import dropbox.files
import yaml
from celery import Celery, chord
from celery.utils.log import get_task_logger

from dropboxs3.atomic_lock import task_lock
from dropboxs3.dbox_worker import DBoxWorker
from dropboxs3.s3_worker import S3Worker

TLOG = get_task_logger(__name__)
LOG = logging.getLogger(__name__)

celery_broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost//")
celery_backend = os.environ.get("CELERY_BACKEND_URL", "redis://localhost")

# map tasks to queues
# all tasks go to default queue ("celery"), video tasks go to video queue
task_routes = {
    "process_video_file": {"queue": "video"},
}

app = Celery("dropboxs3.celery_runner", broker=celery_broker, backend=celery_backend)

app.conf.update(
    task_serializer="pickle",
    result_serializer="pickle",
    accept_content=["pickle", "json", "application/text"],
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_create_missing_queues=True,
    task_routes=task_routes,
)


@app.task(bind=True, max_retries=2, name="migrate_all", queue="celery")
def migrate_all(
    self,
    app_key,
    app_secret,
    refresh_token,
    s3_key_s,
    s3_secret_s,
    s3_bucket_s,
    s3_path_s,
    config_name,
):
    """
    given a dropbox api key, pulls a list of all files in Camera Uploads dir, and
    launches a celery group job to process all of them. Returns a sum of all processed
    files' sizes
    """
    # get a list of all files in this dropbox account's Camera Uploads folder
    TLOG.info("Querying DBX for config {}".format(config_name))

    try:
        db = DBoxWorker(app_key, app_secret, refresh_token, auto_login=True)
        file_list = db.get_images()
    except Exception as e:
        TLOG.error(f"Error querying DBX for config {config_name}: {e}")
        self.retry(exc=e, countdown=int(random.uniform(2, 4) ** self.request.retries))
        return 0

    if len(file_list.entries) == 0:
        TLOG.info(f"Found no files in DBX for config {config_name}; returning")
        return 0
    else:
        TLOG.info(
            f"Got {len(file_list.entries)} files for config {config_name}; starting migration"
        )

    # split files into img and video
    images, videos = split_entries_by_type(file_list)

    # launch a chord for each - videos go into their own queue, to be processed one at a time
    try:
        if len(images) > 0:
            chord(
                [
                    process_image_file.s(
                        app_key,
                        app_secret,
                        refresh_token,
                        s3_key_s,
                        s3_secret_s,
                        s3_bucket_s,
                        s3_path_s,
                        x,
                    ).set(queue="celery")
                    for x in images
                ],
                sum_bytes.s().set(queue="celery"),
            )()

        if len(videos) > 0:
            chord(
                [
                    process_video_file.s(
                        app_key,
                        app_secret,
                        refresh_token,
                        s3_key_s,
                        s3_secret_s,
                        s3_bucket_s,
                        s3_path_s,
                        x,
                    ).set(queue="video")
                    for x in videos
                ],
                sum_bytes.s().set(queue="video"),
            )()
    except Exception as e:
        TLOG.error(
            "migrate_all() failed to start a chord(s) for config {}: {}".format(
                config_name, e
            )
        )
        self.retry(exc=e, countdown=int(random.uniform(2, 4) ** self.request.retries))

    return len(file_list.entries)


def split_entries_by_type(file_list: dropbox.files.ListFolderResult) -> tuple:
    image_types = [".jpg", ".jpeg"]

    images = list()
    videos = list()

    for f in file_list.entries:
        file_type = Path(f.path_lower).suffix
        if file_type in image_types:
            images.append(f)
        else:
            videos.append(f)

    TLOG.info(f"Found {len(images)} images and {len(videos)} videos")
    return images, videos


@app.task(bind=True, name="process_image_file", queue="celery")
def process_image_file(
    self,
    *args,
    **kwargs,
):
    return process_single_file(*args, **kwargs)


@app.task(bind=True, name="process_video_file", queue="video")
def process_video_file(
    self,
    *args,
    **kwargs,
):
    return process_single_file(*args, **kwargs)


def process_single_file(
    app_key,
    app_secret,
    refresh_token,
    s3_key_s,
    s3_secret_s,
    s3_bucket_s,
    s3_path_s,
    image,
):
    """
    given a dropbox API key and image, downloads image and writes to S3, then deletes
    image from dropbox
    Atomic?
    We don't retry anything of the three non-atomic steps in this task. If the file remains in dropbox, a future
    migrate_all will retry it, until it's deleted.
    """
    task_id = "{}-{}-{}-{}".format(
        app_key, s3_key_s, s3_secret_s, image.path_lower, app.oid
    )
    task_hash = md5(task_id.encode("utf-8")).hexdigest()
    TLOG.info(f"processing file {image.path_lower}")

    with task_lock(task_hash) as lock_acquired:
        if not lock_acquired:
            LOG.info(
                f"Failed to acquire lock for {image.path_lower} - already being processed"
            )
            return 0
        else:
            # download image from dropbox
            try:
                TLOG.debug(f"Downloading {image.path_lower} from dropbox")
                db = DBoxWorker(app_key, app_secret, refresh_token, auto_login=True)
                m, f = db.get_file_from_dbox(image)
            except Exception as e:
                TLOG.error(
                    f"dropbox download error on {image.path_lower} :: error: {e}"
                )
                return 0

            # upload to S3
            s3_path_for_file = "n/a"
            try:
                TLOG.debug("Uploading to S3 {}".format(image.path_lower))
                s3_path_for_file = db.generate_s3_path_chunk(m)
                s3 = S3Worker(
                    key=s3_key_s,
                    secret=s3_secret_s,
                    bucket=s3_bucket_s,
                    path=s3_path_s,
                    auto_login=True,
                )
                s3.upload_to_s3(f, s3_path_for_file)
            except Exception as e:
                TLOG.error(f"S3 upload error on {s3_path_for_file} :: error: {e}")
                return 0

            # delete image from dropbox
            try:
                TLOG.debug(f"Deleting {image.path_lower} from dropbox")
                del_result = db.delete_file_from_dbox(image)
            except Exception as e:
                TLOG.error(f"dropbox delete error on {image.path_lower}: {del_result}")
                TLOG.error(f"{e}")
                return 0

            TLOG.info(f"successfully migrated {image.path_lower}")
            return m.size


@app.task(name="sum_bytes")
def sum_bytes(args):
    res = "n/a"
    try:
        res = convert_size(sum(args))
    except TypeError:
        pass
    return res


def convert_size(size_bytes):
    """
    utility func for logging bytes transferred
    """
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def setup_celery_beats_scheduler():
    # import configs from YAML on startup - only runs in beat process, not worker
    LOG.error("IN BEATS SETUP")

    try:
        with open("./config/config.yaml", "r") as config_file:
            yaml_config = yaml.load(config_file, Loader=yaml.Loader)
    except FileNotFoundError as e:
        LOG.error(f"Couldn't find config/config.yaml: {e}")
        raise
    except yaml.YAMLError as e:
        LOG.error(f"yaml error parsing config/config.yaml: {e}")
        raise

    dict_of_schedules = dict()
    config_names = list()

    for job in yaml_config["worker_configs"]:
        config_names.append(job)

        sched = {
            "task": "migrate_all",
            "schedule": yaml_config["worker_configs"][job]["interval"],
            "args": (
                yaml_config["worker_configs"][job]["app_key"],
                yaml_config["worker_configs"][job]["app_secret"],
                yaml_config["worker_configs"][job]["refresh_token"],
                yaml_config["worker_configs"][job]["s3_key"],
                yaml_config["worker_configs"][job]["s3_secret"],
                yaml_config["worker_configs"][job]["s3_bucket"],
                yaml_config["worker_configs"][job]["s3_key_path"],
                job,
            ),
        }
        dict_of_schedules["migrate_{}".format(job)] = sched
        LOG.info(
            f"Adding schedule {job} every {yaml_config['worker_configs'][job]['interval']}s"
        )

    app.conf.beat_schedule = dict_of_schedules


# run this on beats scheduler only
IM_A_BEAT = sys.argv and sys.argv[0].endswith("celery") and "beat" in sys.argv
if IM_A_BEAT:
    print("IM A BEAT !!!")
    LOG.warning("IM A BEAT (IN A LOG) (BUT NOT A TLOG!")
    setup_celery_beats_scheduler()
