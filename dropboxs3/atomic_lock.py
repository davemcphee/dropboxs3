import os
from contextlib import contextmanager

import redis_lock
from redis import StrictRedis

redis_host = os.environ.get('CELERY_BACKEND_URL', 'redis://localhost')
redis_host = redis_host.split('//')[1]
redis_client = StrictRedis(host=redis_host)

LOCK_EXPIRE = 60 * 10  # Locks expire in 10 minutes


@contextmanager
def task_lock(lock_id):
    local_lock = redis_lock.Lock(redis_client, lock_id, expire=LOCK_EXPIRE)
    try:
        yield local_lock.acquire(blocking=False)
    finally:
        try:
            local_lock.release()
        except redis_lock.NotAcquired:
            pass
