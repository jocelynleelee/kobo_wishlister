import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

KOBO_URL = "https://www.kobo.com/tw/zh/ebook/"
headers = {"Accept-Language": "zh-TW", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"} 

class WishList(object):

    def __init__(self):
        pass

    def load(self):
        with open("wishlist.txt", "r") as fp:
            lines = fp.readlines()
            for book_id in lines:
                book_url = KOBO_URL + book_id
                response = requests.get(book_url, headers)
                if response.status_code != 200:
                    print(f"Error: {response.status_code}")
                    continue
                soup = BeautifulSoup(response.text, 'html.parser')
                book_title = soup.find("h1", "title product-field").text.strip()
                book_price = soup.find('meta', {'property': 'og:price'})["content"]
                book_image = soup.find('meta', {'property': 'og:image'})["content"]
                timestamp = datetime.now().strftime("%m/%d/%Y")
    
    def add(self, book_id):
        book_url = KOBO_URL + book_id
        response = requests.get(book_url, headers)
        # time.sleep(5)
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        book_title = soup.find("h1", "title product-field").text.strip()
        book_price = soup.find('meta', {'property': 'og:price'})["content"]
        book_image = soup.find('meta', {'property': 'og:image'})["content"]
        timestamp = datetime.now()
        book = {"title": book_title,
                "image": book_image,
                "price": book_price, 
                "timestamp": timestamp,
                "id": book_id}
        return book

def main():
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-l', '--load', required=True) 
    # kwargs = vars(parser.parse_args())
    wishlist = WishList()
    wishlist.load()

if __name__ == "__main__":
    main()