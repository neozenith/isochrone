.PHONY: fix_geojson scrape_isochrones all consolidate_isochrones migrate_geojson_geoparquet rentals aux_data isochrones

######### SUPPORT FILES #########
aux_data:
#	uv run export_shapefiles.py
	time uv run extract_postcode_polygons.py
	time uv run extract_stops_within_union.py
	time uv run stops_by_transit_time.py

######### API FETCHING #########
scrape_isochrones:
	uv run batch_isochrones_for_stops.py --status

rentals: 
	uv run process_realestate_candidates.py

######### DATA TIDY UP #########
fix_geojson: scrape_isochrones
	time uv run fix_geojson.py data/geojson/foot/ -o data/geojson_fixed/foot/
	time uv run fix_geojson.py data/geojson/bike/ -o data/geojson_fixed/bike/
	time uv run fix_geojson.py data/geojson/car/ -o data/geojson_fixed/car/


# create the data/isochrones_concatenated/**/*.geojson
consolidate_isochrones: fix_geojson
	time uv run consolidate_isochrones.py

migrate_geojson_geoparquet: consolidate_isochrones
	time uv run migrate_geojson_geoparquet.py

isochrones: aux_data consolidate_isochrones

all: aux_data migrate_geojson_geoparquet rentals
# This will run all the steps to prepare the data for the isochrone viewer
	uv run isochrone_viewer.py

fix:
	uv run ruff format . --respect-gitignore
	uv run ruff check --respect-gitignore --fix-only .
	uv run ruff check --respect-gitignore --statistics .