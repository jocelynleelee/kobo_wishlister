import requests

class PriceTracker(object):
    """
    wrapper of price tracker flask application
    """

    def __init__(self, base_url='http://127.0.0.1:5000'):
        self.base_url = base_url

    def submit_task(self, book_id):
        endpoint = f'{self.base_url}/api/add_book'
        data = {'book_id': book_id, "API-Key": "hqqBQxYVvlNFCk3wdJMu9A"}
        response = requests.post(endpoint, json=data)
        return response.json()

    def update_wishlist(self):
        pass

    def get_wishlist(self):
        pass


def main():
    pass

if __name__ == "__main__":
    price_tracker = PriceTracker()
    # Example: Call the submit_task function
    result = price_tracker.submit_task('oTVIfBe3GzCvpD3PJkTxNw')
    print(result)