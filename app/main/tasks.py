from app import celery_app, kobo_wishlist

@celery_app.task
def create_book(current_user_id, book_id):
    this_book = kobo_wishlist.add(book_id)
    if not this_book:
        return 'failed to add this book!'
    
    return this_book