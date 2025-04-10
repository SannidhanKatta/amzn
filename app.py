from flask import Flask, render_template, request, jsonify
from backend.amazon_scraper import AmazonTVScraper
from flask_cors import CORS
import json
import os
import traceback
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        logger.info("Received scrape request")
        url = request.json.get('url')
        if not url:
            logger.error("No URL provided")
            return jsonify({'error': 'URL is required'}), 400
        
        logger.info(f"Processing URL: {url}")
        if not url.startswith('https://www.amazon.in/') and not url.startswith('http://www.amazon.in/'):
            logger.error("Invalid Amazon India URL")
            return jsonify({'error': 'Only Amazon India URLs are supported'}), 400

        scraper = AmazonTVScraper()
        try:
            logger.info("Initializing scraper...")
            product_data = scraper.extract_product_details(url)
            
            if product_data:
                logger.info("Successfully scraped product details")
                return jsonify(product_data)
            else:
                logger.error("Failed to extract product details")
                return jsonify({'error': 'Failed to extract product details'}), 500
        
        except Exception as e:
            logger.error(f"Scraping error: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Scraping error: {str(e)}'}), 500
        
        finally:
            logger.info("Closing scraper")
            scraper.close()

    except Exception as e:
        logger.error(f"General error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 