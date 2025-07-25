#!/usr/bin/env python
"""
isochrone_viewer.py - Minimal Holoviz Panel app with DeckGL map.

Shows a map centered and zoomed to the bounding box:
  Top-left:   -37.713453, 144.895298
  Bottom-right: -37.814206, 144.989262
"""

# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "panel",
#   "pydeck",
#   "geopandas",
#   "pyarrow",
#   "duckdb",
#   "duckdb-extensions",
#   "duckdb-extension-spatial",
#   "python-dotenv>=1.0.0",
#   "shapely",
# ]
# ///

import os

import panel as pn
import param

pn.extension("deckgl", template="material", sizing_mode="stretch_width")

from dotenv import load_dotenv

load_dotenv()

# Bounding box coordinates
TOP_LEFT = (-37.713453, 144.895298)  # (lat, lon)
BOTTOM_RIGHT = (-37.814206, 144.989262)  # (lat, lon)

# Calculate center
center_lat = (TOP_LEFT[0] + BOTTOM_RIGHT[0]) / 2
center_lon = (TOP_LEFT[1] + BOTTOM_RIGHT[1]) / 2

# DeckGL initial view state
map_style = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"


class App(pn.viewable.Viewer):
    """A Panel app that displays a DeckGL map with isochrones and PTV lines.

    Inspired by: https://panel.holoviz.org/gallery/nyc_deckgl.html
    """

    data = param.DataFrame(precedence=-1)  # Raw data

    view = param.DataFrame(precedence=-1)  # Filtered view for the current time bucket

    play = param.Event(label="▷")
    speed = param.Integer(default=1, bounds=(1, 10), label="Speed", precedence=-1)
    max_time_bucket = 10
    time_bucket = param.Integer(default=0, bounds=(0, max_time_bucket), label="Time Bucket")

    def __init__(self, **params):
        super().__init__(**params)
        self.app = pn.pane.DeckGL(self.spec, sizing_mode="stretch_both", height=800)
        self._update_layers()
        self.app.param.watch(self._update_layers, "click_state")
        self._playing = False
        self._cb = pn.state.add_periodic_callback(
            self._update_time_bucket, 1000 // self.speed, start=False
        )

    @param.depends("view", watch=True)
    def _update_layers(self):
        # gdf = load_ptv_lines_data()  # Load the PTV lines data
        # layer = layer_for(gdf)  # Create a layer from the GeoDataFrame
        layers = []
        # self.app[1] = pn.pane.DeckGL(pdk.Deck(layers=layers), height=800)  # Update the DeckGL pane

    # @param.depends('view', 'radius', watch=True)
    # def _update_arc_view(self, event=None):
    #     data = self.data if self.view is None else self.view
    #     lon, lat, = (-73.9857, 40.7484)
    #     if self.deck_gl:
    #         lon, lat = self.deck_gl.click_state.get('coordinate', (lon, lat))
    #     tol = self.radius / 100000
    #     self.arc_view = data[
    #         (data.pickup_x>=float(lon-tol)) &
    #         (data.pickup_x<=float(lon+tol)) &
    #         (data.pickup_y>=float(lat-tol)) &
    #         (data.pickup_y<=float(lat+tol))
    #     ]

    @param.depends("view")
    def spec(self):
        return {
            "initialViewState": {
                "bearing": 0,
                "latitude": center_lat,
                "longitude": center_lon,
                "maxZoom": 15,
                "minZoom": 5,
                "pitch": 0,
                "zoom": 11,
            },
            "mapProvider": "google_maps",  # Use Google Maps as the base map
            "apiKeys": {
                "google_maps": os.environ.get(
                    "GOOGLE_MAPS_API_KEY", ""
                ),  # Replace with your Google Maps API key
            },
            "mapStyle": map_style,
            "layers": [],
            "views": [{"@@type": "MapView", "controller": True}],
        }

    def _update_time_bucket(self):
        self.time_bucket = (self.time_bucket + 1) % self.max_time_bucket

    @param.depends("time_bucket", watch=True, on_init=True)
    def _update_time_bucket_view(self):
        # self.view = self.data[self.data.time_bucket==self.time_bucket]
        print(f"Updating view for time bucket {self.time_bucket}")

    @param.depends("speed", watch=True)
    def _update_speed(self):
        self._cb.period = 1000 // self.speed

    @param.depends("play", watch=True)
    def _play_pause(self):
        if self._playing:
            self._cb.stop()
            self.param.play.label = "▷"
            self.param.speed.precedence = -1
        else:
            self._cb.start()
            self.param.play.label = "❚❚"
            self.param.speed.precedence = 1
        self._playing = not self._playing

    @property
    def controls(self):
        return pn.Param(self.param, show_name=False)

    def __panel__(self):
        return pn.Column(
            self.app,
            self.controls,
            min_height=800,
            sizing_mode="stretch_both",
        )
