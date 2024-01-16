import time
import random
from app import celery_app, kobo_wishlist
from celery import current_task


@celery_app.task(bind=True, rate_limit='1/5s')
def create_book(self, book_id):
    start_time = time.time()
    this_book = kobo_wishlist.add(book_id)
    time_taken = time.time() - start_time
    current_task().logger.info(f'Task completed in {time_taken:.2f} seconds')
    if not this_book:
        return 'failed to add this book!'
    
    return this_book

