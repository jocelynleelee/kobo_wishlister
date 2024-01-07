# discount_alert
create a wishlist for books found in Kobo (TW)

- GUI:
  * register
  * login
  * add a book (using book id) to your wishlist
  * check your wishlist


- supported APIs:
  * submit_task(book_id)
  * update_wishlist()
  * get_wishlist()


- modules used:
  * flask: provides the foundation and manipulation of the web application
  * SQLAlchemy: provides the foundation and manipulation of the wishlist database
  * Celery:
    - execute time-consuming and resource-intensive tasks asynchronously (e.g. crawling websites)
    -  perodic tasks: updating prices, sending notifications
    -  parallel process: workload can be distributed to worker proccesses, enabling parallel processing
    -  apply_async (run after `countdown` passes and delay (run right away)
    -  task chaining: tasks in celery can be chained together allowing you to create workflows where a task servers as the input for another.
    -  distributed systems: run across multiple servers or containers
    -  error handling
    -  integration: with message brokers (e.g. RabbitMQ, Redis(current choice), with result backends (e.g. redis or databases), or analytic tools
   
* Redis in celery: serves as the message broker
     - load balancing between celery workers
     - decoupling between adding tasks and executing tasks
     - task queuing: tasks are stored in a queue before being consumed by the celery workers
     - tasks survive even upon application restart or a worker goes down
     - microservices can use message broker to communicate asynchronously through task messages.
     - scalable by increasing the number of workers (horizontal scalability)
    
  




