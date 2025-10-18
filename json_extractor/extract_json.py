import json
import re
import subprocess

def extract_json_from_html(html_file, output_file):
    """Extract and beautify the JSON data from the HTML file using Node.js."""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the line with "const data = "
    pattern = r'const data = (\[.*?\]);'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("Could not find JSON data in HTML file")
        return
    
    js_data = match.group(1)
    
    # Create a temporary JavaScript file to convert JS object to JSON
    js_code = f"""
const data = {js_data};
console.log(JSON.stringify(data, null, 2));
"""
    
    with open('temp_extract.js', 'w', encoding='utf-8') as f:
        f.write(js_code)
    
    try:
        # Run with Node.js
        result = subprocess.run(['node', 'temp_extract.js'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        
        # Parse the output to ensure it's valid JSON
        data = json.loads(result.stdout)
        
        # Write beautified JSON to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully extracted and beautified JSON to {output_file}")
        print(f"📊 JSON structure: {type(data)}")
        if isinstance(data, list):
            print(f"📦 Array length: {len(data)}")
            if len(data) > 1 and isinstance(data[1], dict):
                print(f"🔑 Top-level keys: {list(data[1].keys())}")
        
        # Get file size
        import os
        size = os.path.getsize(output_file)
        print(f"📄 File size: {size:,} bytes ({size/1024:.1f} KB)")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Node.js: {e}")
        print(f"stderr: {e.stderr}")
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON output: {e}")
    except FileNotFoundError:
        print("❌ Node.js not found. Please install Node.js to extract the JSON data.")
        print("   Alternatively, the data is embedded in the HTML at line 104.")
    finally:
        # Clean up temp file
        import os
        if os.path.exists('temp_extract.js'):
            os.remove('temp_extract.js')

if __name__ == "__main__":
    extract_json_from_html('../nyc-sandwiches.html', '../output/nyc-sandwiches-data.json')
