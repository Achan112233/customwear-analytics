from redis import Redis
from rq import Queue, Worker

from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    queues = [Queue(settings.segmentation_queue, connection=connection)]
    Worker(queues, connection=connection).work()
