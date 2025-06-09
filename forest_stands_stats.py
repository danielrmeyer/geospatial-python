import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
import numpy as np
from scipy.ndimage import grey_opening

# Load your forest-stands shapefile
# GeoPandas will pull in .shp/.dbf/.shx/.prj automatically.
# These files comes from the QGIS Training data
stands = gpd.read_file("data/vector/forest_stands_2012.shp") #  TODO shape file should be cmd parameter

# The process of getting the raster data is in the README.md
# Lets ensure that the crs of the tile data is the same as the 
# forest stands boundaries.
with rasterio.open("data/raster/N61E025_copernicus.tif") as src:  #  TODO correct tile should be automatically found and downloaded
    raster_crs = src.crs

    if stands.crs != raster_crs:
        stands = stands.to_crs(raster_crs)

    dsm = src.read(1)
    meta = src.meta


# Morphological opening for bare-earth DTM approximation
# Copernicus DSM is ~10 m resolution. A 15×15 (pixel) window therefore spans about 150 m on a side
# TODO do some analysis on the ideal size
dtm_approx = grey_opening(dsm, size=(15, 15))  #  TODO window size should be a parameter
with rasterio.open("data/raster/N61E025_dtm_approx.tif", "w", **meta) as dst:
    dst.write(dtm_approx, 1)

# Compute canopy height model (CHM = DSM - DTM)
chm = dsm - dtm_approx
with rasterio.open("data/raster/N61E025_chm.tif", "w", **meta) as dst:
    dst.write(chm, 1)

stats = zonal_stats(
    vectors=stands.geometry,
    raster="data/raster/N61E025_copernicus.tif",
    stats=["mean"],
    geojson_out=False,
)

stands["mean_elev"] = [x["mean"] for x in stats]

# Compute mean canopy height per stand
stats_chm = zonal_stats(
    vectors=stands.geometry,
    raster="data/raster/N61E025_chm.tif",
    stats=["mean"],  #  TODO compute more states min, max for example
    geojson_out=False,
)
stands["mean_canopy"] = [x["mean"] for x in stats_chm]

print(stands[["StandID", "mean_elev", "mean_canopy"]])

stands.to_crs("EPSG:4326").to_file(
    "data/forest_stands_with_elev.geojson", driver="GeoJSON"
)
