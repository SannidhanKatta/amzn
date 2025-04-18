from flask import Flask, render_template, request, jsonify
from backend.amazon_scraper import AmazonTVScraper
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not url.startswith('https://www.amazon.in/') and not url.startswith('http://www.amazon.in/'):
            return jsonify({'error': 'Only Amazon India URLs are supported'}), 400

        scraper = AmazonTVScraper()
        try:
            print("Scraping product details...")
            product_data = scraper.extract_product_details(url)
            
            if product_data:
                return jsonify(product_data)
            else:
                return jsonify({'error': 'Failed to extract product details'}), 500
        
        except Exception as e:
            return jsonify({'error': f'Scraping error: {str(e)}'}), 500
        
        finally:
            scraper.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 