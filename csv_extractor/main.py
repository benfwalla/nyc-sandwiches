import csv
import json
import re
from bs4 import BeautifulSoup


def generate_anchor_id(restaurant_name):
    """Generate URL anchor ID from restaurant name."""
    # Convert to lowercase, replace special chars with hyphens
    anchor = restaurant_name.lower()
    anchor = re.sub(r'[^\w\s-]', '', anchor)  # Remove special chars except spaces and hyphens
    anchor = re.sub(r'[\s]+', '-', anchor)     # Replace spaces with hyphens
    anchor = re.sub(r'-+', '-', anchor)        # Replace multiple hyphens with single
    anchor = anchor.strip('-')                 # Remove leading/trailing hyphens
    return anchor


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
                    
                    address, website, price = parse_metadata(val.get('_metadata', ''))
                    
                    # Clean description (remove HTML tags)
                    description = val.get('blurb', '')
                    description = re.sub(r'<[^>]+>', '', description)  # Remove HTML tags
                    
                    sandwich_data = {
                        'restaurant_name': restaurant_name,
                        'sandwich_name': val.get('sandwich', ''),
                        'category': category_name,
                        'is_featured': 1,
                        'image_url': '',  # Featured sandwiches often don't have images in the data
                        'nyt_link': 'https://www.nytimes.com/interactive/2024/05/21/dining/nyc-sandwiches.html',
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
                        
                        # Generate anchor ID
                        anchor_id = generate_anchor_id(restaurant_name)
                        
                        sandwich_data = {
                            'restaurant_name': restaurant_name,
                            'sandwich_name': sandwich.get('sandwich', ''),
                            'category': category_name,
                            'is_featured': 0,
                            'image_url': image_url,
                            'nyt_link': f'https://www.nytimes.com/interactive/2024/05/21/dining/nyc-sandwiches.html#{anchor_id}',
                            'address': address,
                            'website': website,
                            'price': price,
                            'description': description
                        }
                        
                        sandwiches.append(sandwich_data)
    
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
    save_to_csv(sandwiches, output_file)
    
    # Print first few entries as preview
    if sandwiches:
        print("\nPreview of first sandwich:")
        for key, value in sandwiches[0].items():
            print(f"  {key}: {value[:100] if len(str(value)) > 100 else value}")


if __name__ == "__main__":
    main()
