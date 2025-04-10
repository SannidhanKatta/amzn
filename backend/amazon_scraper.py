from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup
import requests
import json
import os
import time
from datetime import datetime
import pandas as pd
from urllib.parse import urljoin
import re
import sys
import platform
import subprocess
import traceback

class AmazonTVScraper:
    def __init__(self):
        self.setup_driver()
        
    def _get_chrome_version(self):
        try:
            if platform.system() == 'Windows':
                # First try the default Chrome location
                paths = [
                    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                    r'C:\Users\%s\AppData\Local\Google\Chrome\Application\chrome.exe' % os.getenv('USERNAME')
                ]
                
                for path in paths:
                    if os.path.exists(path):
                        try:
                            # Try using powershell instead of wmic
                            command = f'powershell -command "(Get-Item \'{path}\').VersionInfo.FileVersion"'
                            output = subprocess.check_output(command, shell=True)
                            version = output.decode('utf-8').strip()
                            if version:
                                return version
                        except:
                            try:
                                # Fallback to reading version file
                                version_file = os.path.join(os.path.dirname(path), 'VERSION')
                                if os.path.exists(version_file):
                                    with open(version_file, 'r') as f:
                                        return f.read().strip()
                            except:
                                continue
                
                print("Chrome executable found but couldn't determine version.")
                return None
            return None
        except Exception as e:
            print(f"Error getting Chrome version: {e}")
            return None

    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Simplified driver setup
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
        except Exception as e:
            print(f"Error setting up Chrome driver: {str(e)}")
            print("\nTo fix this, please follow these steps:")
            print("1. Open Command Prompt as Administrator")
            print("2. Run these commands:")
            print("   pip uninstall selenium webdriver-manager")
            print("   pip install selenium==4.18.1 webdriver-manager==4.0.1")
            print("3. Download ChromeDriver manually:")
            print("   - Go to https://chromedriver.chromium.org/downloads")
            print("   - Download the version that matches your Chrome version")
            print("   - Extract chromedriver.exe to your project folder")
            print("4. Then run the script again")
            sys.exit(1)
        
    def get_page_content(self, url):
        try:
            self.driver.get(url)
            # Wait for the main product content to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "productTitle"))
            )
            # Scroll to load all dynamic content
            self.scroll_page()
            return self.driver.page_source
        except Exception as e:
            print(f"Error loading page: {e}")
            return None

    def scroll_page(self):
        # Scroll slowly to load all dynamic content
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def extract_product_details(self, url):
        page_content = self.get_page_content(url)
        if not page_content:
            return None
        
        soup = BeautifulSoup(page_content, 'lxml')
        product_data = {}
        
        # Product Name
        product_data['product_name'] = self._get_product_name(soup)
        
        # Rating and Number of Ratings
        rating_info = self._get_rating_info(soup)
        product_data.update(rating_info)
        
        # Price Information
        price_info = self._get_price_info(soup)
        product_data.update(price_info)
        
        # Bank Offers
        product_data['bank_offers'] = self._get_bank_offers(soup)
        
        # About this item
        product_data['about_this_item'] = self._get_about_this_item(soup)
        
        # Product Information
        product_data['product_information'] = self._get_product_information(soup)
        
        # Product Images
        product_data['product_images'] = self._get_product_images(soup)
        
        # Manufacturer Images
        product_data['manufacturer_images'] = self._get_manufacturer_images(soup)
        
        # Generate AI Review Summary based on collected data
        product_data['ai_review_summary'] = self._generate_ai_review_summary(product_data)
        
        return product_data

    def _get_product_name(self, soup):
        try:
            return soup.find('span', id='productTitle').text.strip()
        except:
            return None

    def _get_rating_info(self, soup):
        try:
            rating_element = soup.find('span', class_='a-icon-alt')
            ratings_count_element = soup.find('span', id='acrCustomerReviewText')
            
            rating = rating_element.text.split(' out of')[0] if rating_element else None
            ratings_count = ratings_count_element.text.split(' ratings')[0] if ratings_count_element else None
            
            return {
                'rating': rating,
                'number_of_ratings': ratings_count
            }
        except:
            return {'rating': None, 'number_of_ratings': None}

    def _get_price_info(self, soup):
        try:
            # Get the selling price
            price = soup.find('span', class_='a-price-whole')
            current_price = None
            if price:
                try:
                    price_text = price.text.strip().replace(',', '')
                    current_price = float(price_text)
                except:
                    current_price = None

            # Get the MRP
            mrp = None
            # Try different possible price elements
            price_elements = [
                soup.find('span', {'class': 'a-price a-text-price'}),
                soup.find('span', {'class': 'priceBlockStrikePriceString'}),
                soup.find('span', {'data-a-strike': 'true'})
            ]
            
            for element in price_elements:
                if element:
                    try:
                        # Try to find the price within a child span
                        price_span = element.find('span')
                        if price_span:
                            mrp_text = price_span.text
                        else:
                            mrp_text = element.text
                            
                        # Clean up the price text
                        mrp_text = mrp_text.strip()
                        # Remove currency symbols and non-numeric characters
                        mrp_text = re.sub(r'[^\d.,]', '', mrp_text)
                        # Remove commas
                        mrp_text = mrp_text.replace(',', '')
                        
                        # Convert to float
                        mrp = float(mrp_text)
                        print(f"Found MRP: {mrp}")  # Debug print
                        
                        # If we successfully got a valid MRP, break the loop
                        if mrp > 0:
                            break
                    except Exception as e:
                        print(f"Error parsing MRP from element: {e}")
                        continue

            # Calculate discount percentage
            discount = None
            if current_price and mrp and current_price < mrp:
                discount = ((mrp - current_price) / mrp) * 100
                # Round to 2 decimal places
                discount = f"{discount:.2f}%"
                print(f"Calculated discount: {discount}")  # Debug print

            return {
                'selling_price': current_price,
                'mrp': mrp,
                'discount_percentage': discount
            }
        except Exception as e:
            print(f"Error in price info extraction: {e}")
            return {'selling_price': None, 'mrp': None, 'discount_percentage': None}

    def _get_bank_offers(self, soup):
        # Define bank patterns at the method level so it's available throughout the method
        bank_patterns = {
            'HDFC': ['hdfc', 'h.d.f.c'],
            'SBI': ['sbi', 's.b.i'],
            'ICICI': ['icici', 'i.c.i.c.i'],
            'Axis': ['axis']
        }
        
        try:
            bank_offers = []
            
            # First try to find and click the bank offers card
            try:
                # Wait for the bank offers section to be present
                bank_offer_elements = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "a-carousel-card"))
                )
                
                # Click on the bank offer card if found
                for element in bank_offer_elements:
                    try:
                        if any(text in element.text for text in ['Bank Offer', 'Credit Card', '₹3,000']):
                            element.click()
                            time.sleep(2)  # Wait for side panel to load
                            break
                    except:
                        continue
                
                # Get the updated page content after clicking
                page_content = self.driver.page_source
                soup = BeautifulSoup(page_content, 'lxml')
                
                # Look for offers in the side panel
                side_panel = soup.find('div', {'id': 'InstantBankDiscount-sideSheet'})
                if side_panel:
                    # Find all offer items
                    offer_items = side_panel.find_all(['div', 'li'], class_=['a-section vsx-offers-desktop-lv_item', 'a-section vsx-offers-desktop-lv__item'])
                    
                    if not offer_items:
                        # Try alternative selectors
                        offer_items = side_panel.find_all(['div', 'li'], class_=['a-section a-spacing-mini'])
                    
                    for item in offer_items:
                        offer = {}
                        
                        # Get the full offer text
                        offer_text = item.get_text(strip=True)
                        if not offer_text or len(offer_text) < 10:  # Skip empty or very short texts
                            continue
                        
                        # Store the full offer text first
                        offer['offer_text'] = offer_text
                        
                        # Extract bank name
                        offer_text_lower = offer_text.lower()
                        for bank, patterns in bank_patterns.items():
                            if any(pattern in offer_text_lower for pattern in patterns):
                                offer['bank_name'] = bank
                                break
                    
                        # Extract discount amount (more precise pattern)
                        discount_match = re.search(r'(?:Flat|Get|Up to)?\s*(?:INR|Rs\.|₹)?\s*(\d+(?:,\d+)?(?:\.\d{2})?)\s*(?:Instant\s+)?(?:Discount|Cashback)', offer_text, re.IGNORECASE)
                        if discount_match:
                            try:
                                offer['discount_amount'] = float(discount_match.group(1).replace(',', ''))
                            except ValueError:
                                print(f"Error converting discount amount: {discount_match.group(1)}")
                        
                        # Extract minimum purchase value
                        min_purchase_match = re.search(r'(?:Min(?:imum)?\s*purchase|Min\s*value)\s*(?:of\s*)?(?:INR|Rs\.|₹)?\s*(\d+(?:,\d+)?(?:\.\d{2})?)', offer_text, re.IGNORECASE)
                        if min_purchase_match:
                            try:
                                offer['min_purchase'] = float(min_purchase_match.group(1).replace(',', ''))
                            except ValueError:
                                print(f"Error converting minimum purchase: {min_purchase_match.group(1)}")
                        
                        # Check for EMI information
                        if 'EMI' in offer_text:
                            offer['emi_available'] = True
                            emi_duration_match = re.search(r'(\d+)\s*month', offer_text)
                            if emi_duration_match:
                                offer['emi_duration'] = int(emi_duration_match.group(1))
                        else:
                            offer['emi_available'] = False
                        
                        if offer:  # Only add if we found some details
                            bank_offers.append(offer)
            
            except Exception as e:
                print(f"Error processing bank offers in side panel: {e}")
                traceback.print_exc()
            
            # If no offers found in side panel, try to get them from the main page
            if not bank_offers:
                print("Trying to find bank offers in main content...")
                # Look for bank offer cards in the main content
                bank_cards = soup.find_all(['div', 'span'], string=re.compile(r'(?:Bank\s+Offer|Credit\s+Card|₹\s*\d+(?:,\d+)?(?:\.\d{2})?\s*(?:discount|cashback))', re.IGNORECASE))
                
                for card in bank_cards:
                    card_text = card.get_text(strip=True)
                    if card_text and len(card_text) > 10:  # Skip empty or very short texts
                        offer = {
                            'offer_text': card_text,
                            'source': 'main_page'
                        }
                        
                        # Try to extract basic offer details
                        for bank, patterns in bank_patterns.items():
                            if any(pattern in card_text.lower() for pattern in patterns):
                                offer['bank_name'] = bank
                                break
                        
                        # Try to extract amount
                        amount_match = re.search(r'(?:INR|Rs\.|₹)?\s*(\d+(?:,\d+)?(?:\.\d{2})?)', card_text)
                        if amount_match:
                            try:
                                offer['discount_amount'] = float(amount_match.group(1).replace(',', ''))
                            except ValueError:
                                pass
                        
                        bank_offers.append(offer)
            
            if not bank_offers:
                print("No bank offers found")
            else:
                print(f"Found {len(bank_offers)} bank offers")
            
            return bank_offers

        except Exception as e:
            print(f"Error extracting bank offers: {e}")
            traceback.print_exc()
            return []

    def _get_about_this_item(self, soup):
        try:
            about_section = soup.find('div', {'id': 'feature-bullets'})
            if about_section:
                items = about_section.find_all('span', class_='a-list-item')
                return [item.text.strip() for item in items]
            return []
        except:
            return []

    def _get_product_information(self, soup):
        try:
            info = {}
            tech_details = soup.find('table', {'id': 'productDetails_techSpec_section_1'})
            if tech_details:
                rows = tech_details.find_all('tr')
                for row in rows:
                    label = row.find('th')
                    value = row.find('td')
                    if label and value:
                        info[label.text.strip()] = value.text.strip()
            return info
        except:
            return {}

    def _get_product_images(self, soup):
        try:
            images = []
            
            # Find all image thumbnails with the specific class structure
            thumbnails = soup.find_all('li', {'class': 'a-spacing-small item imageThumbnail a-declarative'})
            
            # If not found, try alternative class name
            if not thumbnails:
                thumbnails = soup.find_all('li', {'class': 'a-spacing-small'})
            
            for thumb in thumbnails:
                try:
                    # Find the image element within the thumbnail
                    img = thumb.find('img')
                    if img:
                        # Get the data-old-hires attribute or src
                        if 'data-old-hires' in img.attrs:
                            image_url = img['data-old-hires']
                        elif 'src' in img.attrs:
                            # Convert thumbnail URL to high resolution
                            image_url = img['src']
                            # Remove size specifications to get base URL
                            base_url = image_url.split('._')[0]
                            # Add high resolution suffix
                            image_url = f"{base_url}._SL1500_.jpg"
                        
                        # Skip video thumbnails and small icons
                        if not any(x in image_url.lower() for x in ['video', 'play', 'sprite', 'icon', 'gif']):
                            if image_url not in images:
                                images.append(image_url)
                except Exception as e:
                    print(f"Error processing thumbnail: {e}")
                    continue
            
            # If no images found in thumbnails, try the main product image
            if not images:
                main_image = soup.find('div', {'id': 'imgTagWrapperId'})
                if main_image:
                    img = main_image.find('img')
                    if img and 'src' in img.attrs:
                        image_url = img['src']
                        base_url = image_url.split('._')[0]
                        images.append(f"{base_url}._SL1500_.jpg")
            
            # Try another way to find images using data attributes
            if not images:
                image_elements = soup.find_all('img', {'data-a-dynamic-image': True})
                for img in image_elements:
                    try:
                        # Parse the JSON data from data-a-dynamic-image attribute
                        image_data = json.loads(img['data-a-dynamic-image'])
                        # Get the URL with highest resolution
                        if image_data:
                            # Get the first URL from the image data
                            image_url = list(image_data.keys())[0]
                            base_url = image_url.split('._')[0]
                            high_res_url = f"{base_url}._SL1500_.jpg"
                            if high_res_url not in images:
                                images.append(high_res_url)
                    except:
                        continue
            
            return images
            
        except Exception as e:
            print(f"Error extracting product images: {e}")
            return []

    def _get_manufacturer_images(self, soup):
        try:
            images = []
            manufacturer_section = soup.find('div', {'id': 'aplus'})
            if manufacturer_section:
                image_elements = manufacturer_section.find_all('img')
                for img in image_elements:
                    if 'src' in img.attrs:
                        images.append(img['src'])
            return list(set(images))  # Remove duplicates
        except:
            return []

    def _generate_ai_review_summary(self, product_data):
        try:
            # Extract key information
            price = product_data.get('selling_price', 0)
            features = product_data.get('about_this_item', [])
            tech_info = product_data.get('product_information', {})
            
            # Initialize summary parts
            summary_parts = []
            
            # Analyze display features
            resolution = tech_info.get('Resolution', '').lower()
            if '3840 x 2160' in resolution or '4k' in resolution:
                summary_parts.append("This TV offers crisp 4K Ultra HD resolution")
            
            # Analyze screen size
            screen_size = tech_info.get('Standing screen display size', '')
            if screen_size:
                summary_parts.append(f"With a {screen_size} display")
            
            # Analyze smart features
            smart_features = []
            for feature in features:
                if 'smart' in feature.lower():
                    if 'alexa' in feature.lower() or 'google assistant' in feature.lower():
                        smart_features.append("voice control capabilities")
                    if 'wifi' in feature.lower() or 'wireless' in feature.lower():
                        smart_features.append("wireless connectivity")
                    if 'streaming' in feature.lower() or 'ott' in feature.lower():
                        smart_features.append("access to streaming services")
            
            if smart_features:
                summary_parts.append("Features " + ", ".join(smart_features))
            
            # Analyze sound
            sound_output = tech_info.get('Speakers Maximum Output Power', '')
            if sound_output:
                summary_parts.append(f"Equipped with {sound_output} speaker output")
            
            # Price analysis
            if price:
                if price < 25000:
                    price_segment = "budget-friendly"
                elif price < 50000:
                    price_segment = "mid-range"
                else:
                    price_segment = "premium"
                summary_parts.append(f"This {price_segment} TV offers")
            
            # Value proposition
            if product_data.get('discount_percentage'):
                summary_parts.append(f"Currently available at a {product_data['discount_percentage']} discount")
            
            # Combine all parts
            if summary_parts:
                summary = ". ".join(summary_parts) + "."
                summary += " Based on the specifications and features, this TV provides "
                
                if price and price < 30000:
                    summary += "good value for budget-conscious buyers looking for a smart TV with basic features."
                elif price and price < 50000:
                    summary += "a balanced mix of features and performance for the average user."
                else:
                    summary += "a premium viewing experience with advanced features for demanding users."
                
                return summary
            
            return "Unable to generate review summary due to insufficient product information."
            
        except Exception as e:
            print(f"Error generating AI review summary: {e}")
            return None

    def save_to_json(self, data, filename='tv_details.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def close(self):
        self.driver.quit()

def main():
    url = input("Please enter the Amazon India Smart TV product URL: ")
    scraper = AmazonTVScraper()
    
    try:
        print("Scraping product details...")
        product_data = scraper.extract_product_details(url)
        
        if product_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tv_details_{timestamp}.json"
            scraper.save_to_json(product_data, filename)
            print(f"Data successfully saved to {filename}")
        else:
            print("Failed to extract product details")
    
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        scraper.close()

if __name__ == "__main__":
    main() 