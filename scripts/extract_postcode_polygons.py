# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pyarrow",
#   "shapely",
#   "requests"
# ]
# ///

import pathlib
from pathlib import Path

import geopandas as gpd
import pandas as pd
from utils import dirty, save_geodataframe

SCRIPT_DIR = Path(__file__).parent.resolve()

# INPUTS
POSTCODES_CSV = SCRIPT_DIR.parent / "postcodes.csv"
STOPS_GEOJSON = SCRIPT_DIR.parent / "data/public_transport_stops.parquet"
POSTCODE_POLYGONS = (
    SCRIPT_DIR.parent
    / "data/originals_converted/boundaries/POA_2021_AUST_GDA2020_SHP/POA_2021_AUST_GDA2020.parquet"
)

BOUNDARIES_BASE = SCRIPT_DIR.parent / "data/originals_converted/boundaries"
BOUNDARIES = BOUNDARIES_BASE.rglob("**/*.parquet")

input_to_output_mapping = {
    "postcodes": [POSTCODE_POLYGONS, POSTCODES_CSV],
    "postcodes_with_trams": POSTCODE_POLYGONS,
    "postcodes_with_trams_trains": POSTCODE_POLYGONS,
}
for b in BOUNDARIES:
    output_target = b.stem.lower()
    input_to_output_mapping[output_target] = b


# OUTPUTS
OUTPUT_ROOT = SCRIPT_DIR.parent / "data/geojson/ptv/boundaries/"


def check_output_up_to_date():
    """
    Check if the output files are up to date with respect to the input files.
    """
    files_to_process = {}
    for target, input_file in input_to_output_mapping.items():
        selected_output_file = (
            OUTPUT_ROOT / f"selected_{target}.geojson"
        )  # Selects subset of polygons
        unioned_output_file = (
            OUTPUT_ROOT / f"unioned_{target}.geojson"
        )  # Unions the selected polygons

        if dirty([selected_output_file, unioned_output_file], input_file):
            files_to_process[target] = input_file
            print(f"{target} needs processing.")

    return files_to_process


def filter_for_target(
    target, gdf_polygons, gdf_stops, code_col=None, code_list=None
) -> gpd.GeoDataFrame:
    """
    Filter the GeoDataFrame of polygons based on the target and code list.
    """
    if target in ["postcodes"]:
        return gdf_polygons[gdf_polygons[code_col].astype(str).isin(code_list)]
    else:
        return gpd.sjoin(gdf_polygons, gdf_stops, how="inner", predicate="intersects")


def extract_postcode_polygons():
    # Load the GeoJSON file
    work_to_do = check_output_up_to_date().items()
    if len(work_to_do) == 0:
        print("All outputs are up to date. No work to do.")
        return

    postcode_boundaries = gpd.read_parquet(POSTCODE_POLYGONS)

    # Load postcodes from CSV (expects a column named 'postcode')
    postcodes = pd.read_csv(POSTCODES_CSV)
    postcode_list = postcodes.iloc[:, 1].astype(str).tolist()

    gdf_stops = gpd.read_parquet(STOPS_GEOJSON)
    gdf_stops_trams_trains = gdf_stops[gdf_stops["MODE"].isin(["METRO TRAIN", "METRO TRAM"])].copy()
    gdf_stops_trams = gdf_stops[gdf_stops["MODE"].isin(["METRO TRAM"])].copy()

    for target, input_file in work_to_do:
        print(f"Processing target: {target} with input file: {input_file}")
        if target == "postcodes":
            gdf_polygons = filter_for_target(
                target, postcode_boundaries, gdf_stops, "POA_CODE21", postcode_list
            )
        elif target == "postcodes_with_trams":
            gdf_polygons = filter_for_target(target, postcode_boundaries, gdf_stops_trams)
        elif target == "postcodes_with_trams_trains":
            gdf_polygons = filter_for_target(target, postcode_boundaries, gdf_stops_trams_trains)
        else:
            # For other targets, load the specific boundary file
            print(
                f"Loading input file: {input_file} {pathlib.Path(input_file).stat().st_size / 1024 / 1024:.2f} MB"
            )
            gdf_input = gpd.read_parquet(input_file)
            gdf_polygons = filter_for_target(target, gdf_input, gdf_stops_trams_trains)

        gdf = gdf_polygons
        unioned_geom = gdf.geometry.union_all()
        unioned_gdf = gpd.GeoDataFrame(geometry=[unioned_geom], crs=gdf.crs)

        selected_output_file = OUTPUT_ROOT / f"selected_{target}.geojson"
        unioned_output_file = OUTPUT_ROOT / f"unioned_{target}.geojson"

        save_geodataframe(gdf, selected_output_file)
        save_geodataframe(unioned_gdf, unioned_output_file)


if __name__ == "__main__":
    extract_postcode_polygons()
    print("Postcode polygons extracted and saved.")
