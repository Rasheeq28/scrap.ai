import re
from bs4 import BeautifulSoup
from utils.helpers import clean_numeric, format_comma_separated

class PropertyParser:
    def __init__(self, html):
        self.soup = BeautifulSoup(html, 'lxml')

    def get_title(self):
        # A. Title
        title = self.soup.find("h2")
        if not title:
            title = self.soup.select_one(".section-container h2")
        return title.text.strip() if title else None

    def get_type(self):
        # B. Type (Apartment, Rent)
        tags = self.soup.select("span.ant-tag")
        types = [t.text.strip() for t in tags if t.text != "Featured"]
        return format_comma_separated(types)

    def get_address(self):
        # C. Address
        addr = self.soup.select_one(".property-heading-location")
        return addr.text.strip() if addr else None

    def get_location(self):
        # D. Location (Area)
        links = self.soup.select("a[href*='/area/']")
        return links[0].text.strip() if links else None

    def get_amenities(self):
        # E. Bedrooms & Bathrooms
        amenities = self.soup.select(".property-heading-ammenities span")
        bedroom = None
        bathroom = None

        for item in amenities:
            text = item.text.lower()
            if "bedroom" in text:
                match = re.search(r"(\d+)", text)
                if match:
                    bedroom = int(match.group(1))
            if "bathroom" in text:
                match = re.search(r"(\d+)", text)
                if match:
                    bathroom = int(match.group(1))
        return bedroom, bathroom

    def get_price(self):
        # F. Price
        price_tag = self.soup.select_one(".property-heading-period-flex-box h2")
        if price_tag:
            return clean_numeric(price_tag.text)
        return None

    def parse_all(self):
        bedroom, bathroom = self.get_amenities()
        return {
            "title": self.get_title(),
            "type": self.get_type(),
            "location": self.get_location(),
            "address": self.get_address(),
            "bedroom": bedroom,
            "bathroom": bathroom,
            "price": self.get_price()
        }
