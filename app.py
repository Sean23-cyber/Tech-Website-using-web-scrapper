from flask import Flask, render_template, jsonify, request
from scraper import NewsScraper
import threading
from datetime import datetime
import json
import atexit

import os

app = Flask(__name__)

# Cache for storing scraped articles
articles_cache = {
    'data': [],
    'last_updated': None,
    'in_progress': False,
    'current_source': 'techcrunch'  # 'techcrunch' or 'wired'
}



def cleanup_on_exit():
    """Function to run when server shuts down"""
    try:
        if os.path.exists('news_data.json'):
            os.remove('news_data.json')
            print("Cleaned up news_data.json on shutdown")
    except Exception as e:
        print(f"Error during cleanup: {e}")

# Register the cleanup function
atexit.register(cleanup_on_exit)






def run_scraper(source=None):
    """Run the scraper for a specific source and update the cache"""
    if articles_cache['in_progress']:
        return
    
    articles_cache['in_progress'] = True
    try:
        scraper = NewsScraper()
        
        # If no source specified, use current source
        if not source:
            source = articles_cache['current_source']
        
        # Scrape based on selected source
        if source == 'techcrunch':
            scraper.scrape_techcrunch_ai()
        elif source == 'wired':
            scraper.scrape_wired_tech()
        else:
            # Default to techcrunch if invalid source
            source = 'techcrunch'
            scraper.scrape_techcrunch_ai()
        
        articles_cache['data'] = [article.to_dict() for article in scraper.articles]
        articles_cache['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        articles_cache['current_source'] = source
        
        # Save to JSON file
        with open('news_data.json', 'w', encoding='utf-8') as f:
            json.dump(articles_cache['data'], f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"Error running scraper: {e}")
    finally:
        articles_cache['in_progress'] = False

@app.route('/')
def index():
    # Start scraping in background if cache is empty or stale (older than 1 hour)
    if (not articles_cache['data'] or 
        not articles_cache['last_updated'] or
        (datetime.now() - datetime.strptime(articles_cache['last_updated'], "%Y-%m-%d %H:%M:%S")).total_seconds() > 3600):
        threading.Thread(target=run_scraper).start()
    
    return render_template('index.html', 
                         articles=articles_cache['data'],
                         last_updated=articles_cache['last_updated'],
                         current_source=articles_cache['current_source'])

@app.route('/api/articles')
def get_articles():
    return jsonify({
        'articles': articles_cache['data'],
        'last_updated': articles_cache['last_updated'],
        'current_source': articles_cache['current_source']
    })

@app.route('/api/refresh', methods=['GET'])
def refresh_articles():
    # Get the source from query parameters
    source = request.args.get('source', 'next')
    
    if source == 'next':
        # Cycle through sources in order: techcrunch -> wired
        sources = ['techcrunch', 'wired']
        current_index = sources.index(articles_cache['current_source']) if articles_cache['current_source'] in sources else 0
        next_index = (current_index + 1) % len(sources)
        source = sources[next_index]
    elif source not in ['techcrunch', 'wired']:
        source = 'techcrunch'  # Default to techcrunch if invalid source
    
    threading.Thread(target=run_scraper, kwargs={'source': source}).start()
    return jsonify({
        'status': 'refresh_started',
        'source': source
    })

if __name__ == '__main__':
    # Load any existing data
    if os.path.exists('news_data.json'):
        try:
            with open('news_data.json', 'r', encoding='utf-8') as f:
                articles_cache['data'] = json.load(f)
                articles_cache['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Error loading cache: {e}")
    
    app.run(debug=True)

