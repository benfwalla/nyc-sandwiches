# NYC Sandwiches

Some scripts to turn the New York Times' ["57 Sandwiches That Define New York City"](https://www.nytimes.com/interactive/2024/dining/best-nyc-sandwiches.html) article into a searchable, filterable CSV.

- [Link to Google Sheet](https://docs.google.com/spreadsheets/d/1pmjf6pLDZmWO4UBwBiI3MO3OpazAt4PWD8mxVPwjqTQ/edit?usp=sharing)
- [Link to Google Map View](https://www.google.com/maps/d/u/0/edit?mid=16oLIRoA2pxbuNWc9m4Z1DsVjTI4E32w&usp=sharing)

![57 Sandwiches That Define New York City NY Times](<nyt-hero.png>)

## Files

- `nyc-sandwiches.html` - The original NYT article (saved)
- `output/nyc-sandwiches-data.json` - Raw JSON data from the HTML used to create the CSV
- `csv_extractor/main.py` - The script that creates the CSV
- `output/nyc-sandwiches.csv` - The searchable data
