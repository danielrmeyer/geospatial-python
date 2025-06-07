import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
import numpy as np
from scipy.ndimage import grey_opening

#  Load your forest-stands shapefile
#  GeoPandas will pull in .shp/.dbf/.shx/.prj automatically.
#  These files comes from the QGIS Training data
stands = gpd.read_file("data/vector/forest_stands_2012.shp")

#  The process of getting the raster data is in the README.md
with rasterio.open("data/raster/N61E025_copernicus.tif") as src:
    raster_crs = src.crs


if stands.crs != raster_crs:
    stands = stands.to_crs(raster_crs)

# Compute an approximate DTM and CHM from the DSM
# DSM -> Digital Surface Model
# DTM -> Digital Terrain Model
# The DSM includes the tops of trees and building etc.
# The DTM should model the ground terrain.
with rasterio.open("data/raster/N61E025_copernicus.tif") as src:
    dsm = src.read(1)
    meta = src.meta

# Morphological opening for bare-earth DTM approximation
# Copernicus DSM is ~10 m resolution. A 15×15 (pixel) window therefore spans about 150 m on a side
# TODO do some analysis on the idea size
dtm_approx = grey_opening(dsm, size=(15, 15))
with rasterio.open("data/raster/N61E025_dtm_approx.tif", "w", **meta) as dst:
    dst.write(dtm_approx, 1)

# Compute canopy height model (CHM = DSM - DTM)
chm = dsm - dtm_approx
with rasterio.open("data/raster/N61E025_chm.tif", "w", **meta) as dst:
    dst.write(chm.astype(rasterio.float32), 1)

stats = zonal_stats(
    vectors=stands.geometry,
    raster="data/raster/N61E025_copernicus.tif",
    stats=["mean"],
    geojson_out=False,
)

stands["mean_elev"] = [feat["mean"] for feat in stats]

# Compute mean canopy height per stand
stats_chm = zonal_stats(
    vectors=stands.geometry,
    raster="data/raster/N61E025_chm.tif",
    stats=["mean"],
    geojson_out=False,
)
stands["mean_canopy"] = [feat["mean"] for feat in stats_chm]

print(stands[["StandID", "mean_elev", "mean_canopy"]])

stands.to_crs("EPSG:4326").to_file(
    "data/forest_stands_with_elev.geojson", driver="GeoJSON"
)
