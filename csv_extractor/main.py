import csv
import json
import re
import os
import time
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup


def generate_slug(restaurant_name):
    """Generate URL slug from restaurant name."""
    # Convert to lowercase
    slug = restaurant_name.lower()
    # Remove special characters (apostrophes, commas, ampersands, etc) - keep only letters, numbers, spaces, hyphens
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace spaces with hyphens
    slug = slug.replace(' ', '-')
    # Replace multiple hyphens with single hyphen
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def clean_address_for_geocoding(address):
    """Clean address to improve geocoding accuracy."""
    if not address:
        return ''
    
    # Remove cross streets in parentheses - e.g., "178 East Seventh Street (Avenue B)" -> "178 East Seventh Street"
    address = re.sub(r'\s*\([^)]+\)', '', address)
    
    # Add "New York, NY" if not already present
    if 'New York' not in address and 'NY' not in address:
        address = f"{address}, New York, NY"
    
    return address.strip()


def geocode_address(address, api_key):
    """Geocode an address using OpenCage API."""
    # Skip if address is empty or "Multiple locations"
    if not address or address.lower() == 'multiple locations':
        return None, None
    
    # Clean the address
    clean_addr = clean_address_for_geocoding(address)
    
    # URL encode the address
    encoded_address = urllib.parse.quote(clean_addr)
    
    # Build the API URL
    url = f'https://api.opencagedata.com/geocode/v1/json?q={encoded_address}&key={api_key}&limit=1&no_annotations=1'
    
    try:
        # Make the request
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
        
        # Check if we got results
        if data.get('results') and len(data['results']) > 0:
            geometry = data['results'][0]['geometry']
            return geometry['lat'], geometry['lng']
        else:
            print(f"  No results for: {clean_addr}")
            return None, None
    
    except Exception as e:
        print(f"  Error geocoding '{clean_addr}': {e}")
        return None, None


def parse_metadata(metadata_html):
    """Parse metadata HTML to extract address, price, and website."""
    if not metadata_html:
        return '', '', ''
    
    # Parse HTML to extract link
    soup = BeautifulSoup(metadata_html, 'html.parser')
    
    # Extract website
    link = soup.find('a')
    website = link.get('href', '') if link else ''
    
    # Get plain text
    text = soup.get_text()
    
    # Extract price
    price_match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
    price = price_match.group(1) if price_match else ''
    
    # Extract address (everything before price)
    if price_match:
        address = text[:price_match.start()].strip().rstrip(',')
    else:
        # If no price, address is before website
        if link:
            address = text.split(link.get_text())[0].strip().rstrip(',')
        else:
            address = text.strip()
    
    return address, website, price


def extract_sandwiches_from_json(json_file):
    """Extract sandwich data from the NYT JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sandwiches = []
    body = data[1]['data']['body']
    
    # Process each category section
    for item in body:
        if item.get('type') != 'category-section':
            continue
        
        content = item.get('value', {}).get('content', [])
        
        # Extract category name
        category_name = ''
        for c in content:
            if c.get('type') == 'scrolly-mask':
                val = c.get('value', {})
                cat_hed = val.get('category_hed', '')
                if cat_hed:
                    category_name = cat_hed
                    break
        
        # Process sections within this category
        for c in content:
            if c.get('type') != 'section':
                continue
            
            section_body = c.get('value', {}).get('body', [])
            
            for sb in section_body:
                # Process featured sandwiches
                if sb.get('type') == 'featured':
                    val = sb.get('value', {})
                    
                    restaurant_name = val.get('restaurant', '')
                    if not restaurant_name:
                        continue
                    
                    # Featured sandwiches use 'metadata' (no underscore)
                    address, website, price = parse_metadata(val.get('metadata', ''))
                    
                    # Clean description (remove HTML tags)
                    description = val.get('blurb', '')
                    description = re.sub(r'<[^>]+>', '', description)  # Remove HTML tags
                    
                    # Generate slug for featured sandwich
                    slug = generate_slug(restaurant_name)
                    
                    sandwich_data = {
                        'restaurant_name': restaurant_name,
                        'sandwich_name': val.get('sandwich', ''),
                        'category': category_name,
                        'is_featured': 1,
                        'image_url': '',  # Featured sandwiches often don't have images in the data
                        'nyt_link': f'https://www.nytimes.com/shared/v2/interactive/2024/dining/best-nyc-sandwiches/{slug}.html',
                        'address': address,
                        'website': website,
                        'price': price,
                        'description': description
                    }
                    
                    sandwiches.append(sandwich_data)
                
                # Process gridwich sandwiches
                elif sb.get('type') == 'gridwich':
                    items = sb.get('value', {}).get('items', [])
                    
                    for sandwich in items:
                        restaurant_name = sandwich.get('restaurant', '')
                        if not restaurant_name:
                            continue
                        
                        address, website, price = parse_metadata(sandwich.get('metadata', ''))
                        
                        # Extract image URL
                        media = sandwich.get('media', {})
                        image_url = ''
                        if media:
                            # Get the base URL and construct the image path
                            output_path = media.get('outputPath', '')
                            file_name = media.get('fileName', '')
                            extensions = media.get('extensions', [])
                            widths = media.get('widths', [])
                            
                            if output_path and file_name and extensions and widths:
                                # Use smallest width with webp extension if available
                                ext = 'webp' if 'webp' in extensions else extensions[0]
                                width = widths[0]
                                base_name = file_name.rsplit('.', 1)[0]
                                image_url = f"{output_path}/{base_name}-@@-{width}.{ext}"
                        
                        # Clean description
                        description = sandwich.get('blurb', '')
                        description = re.sub(r'<[^>]+>', '', description)
                        
                        # Generate slug for URL
                        slug = generate_slug(restaurant_name)
                        
                        sandwich_data = {
                            'restaurant_name': restaurant_name,
                            'sandwich_name': sandwich.get('sandwich', ''),
                            'category': category_name,
                            'is_featured': 0,
                            'image_url': image_url,
                            'nyt_link': f'https://www.nytimes.com/shared/v2/interactive/2024/dining/best-nyc-sandwiches/{slug}.html',
                            'address': address,
                            'website': website,
                            'price': price,
                            'description': description
                        }
                        
                        sandwiches.append(sandwich_data)
    
    return sandwiches


def add_geocoding(sandwiches):
    """Add latitude and longitude to sandwiches using OpenCage API."""
    # Get API key from environment
    api_key = os.environ.get('OPENCAGE_API_KEY')
    
    if not api_key:
        print("Warning: OPENCAGE_API_KEY not found in environment. Skipping geocoding.")
        print("Set it in your .env file or export it: export OPENCAGE_API_KEY=your_key")
        # Add empty lat/lng to all sandwiches
        for sandwich in sandwiches:
            sandwich['latitude'] = ''
            sandwich['longitude'] = ''
        return sandwiches
    
    print(f"\nGeocoding {len(sandwiches)} addresses...")
    geocoded_count = 0
    skipped_count = 0
    
    for i, sandwich in enumerate(sandwiches, 1):
        address = sandwich.get('address', '')
        
        # Skip if no address or "Multiple locations"
        if not address or address.lower() == 'multiple locations':
            sandwich['latitude'] = ''
            sandwich['longitude'] = ''
            skipped_count += 1
            continue
        
        print(f"  [{i}/{len(sandwiches)}] Geocoding: {sandwich['restaurant_name']}...")
        
        lat, lng = geocode_address(address, api_key)
        
        if lat and lng:
            sandwich['latitude'] = lat
            sandwich['longitude'] = lng
            geocoded_count += 1
        else:
            sandwich['latitude'] = ''
            sandwich['longitude'] = ''
        
        # Rate limiting: free tier allows 1 request per second
        # Add a small delay to be safe
        if i < len(sandwiches):  # Don't sleep after the last one
            time.sleep(1.1)
    
    print(f"\nGeocoding complete: {geocoded_count} geocoded, {skipped_count} skipped")
    return sandwiches


def save_to_csv(sandwiches, output_file):
    """Save sandwich data to CSV file."""
    fieldnames = [
        'restaurant_name',
        'sandwich_name',
        'category',
        'is_featured',
        'image_url',
        'nyt_link',
        'address',
        'website',
        'price',
        'latitude',
        'longitude',
        'description'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sandwiches)
    
    print(f"Successfully extracted {len(sandwiches)} sandwiches to {output_file}")


def main():
    json_file = '../output/nyc-sandwiches-data.json'
    output_file = '../output/nyc-sandwiches.csv'
    
    print(f"Extracting sandwich data from {json_file}...")
    sandwiches = extract_sandwiches_from_json(json_file)
    
    print(f"Found {len(sandwiches)} sandwiches")
    
    # Add geocoding
    sandwiches = add_geocoding(sandwiches)
    
    save_to_csv(sandwiches, output_file)
    
    # Print first few entries as preview
    if sandwiches:
        print("\nPreview of first sandwich:")
        for key, value in sandwiches[0].items():
            print(f"  {key}: {value[:100] if len(str(value)) > 100 else value}")


if __name__ == "__main__":
    main()
