# filter_loc_with_departments_simple.py
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path
import fiona

# ------------------- CONFIG -------------------
INPUT_LOC   = "preFilter_A20260121.loc"            # your previously filtered bbox file
OUTPUT_LOC  = "Colombia_A20260121.loc"
GPKG_PATH   = "Departamentos_Septiembre_2025.gpkg"
LAYER_NAME  = None   # if None, we'll try to guess the layer
USE_BUFFER  = True
BUFFER_KM   = 20.0   # increase/decrease, or set to 0 to disable
# ---------------------------------------------

# 1) Load department polygons from the GPKG
if LAYER_NAME is None:
    # Try to find a layer that looks like departments
    layers = fiona.listlayers(GPKG_PATH)
    # common names: "departamentos", "ADM_1", "DEPARTAMENTOS", etc.
    candidates = [ly for ly in layers if "dep" in ly.lower() or "adm_1" in ly.lower()]
    LAYER_NAME = candidates[0] if candidates else layers[0]
    print(f"Using GPKG layer: {LAYER_NAME}")

deps = gpd.read_file(GPKG_PATH, layer=LAYER_NAME)

# 2) Ensure CRS and reproject to EPSG:4326 (WWLLN points CRS)
if deps.crs is None:
    # Many official Colombian layers are in MAGNA-SIRGAS (EPSG:4686).
    # If you KNOW it's 4686, uncomment the next line:
    deps = deps.set_crs("EPSG:4686")
    raise ValueError("The GPKG layer has no CRS defined. Set the correct CRS before running.")
deps = deps.to_crs("EPSG:4326")

# 3) Dissolve all departments into a single polygon (nationwide)
country_poly = deps.dissolve().geometry.iloc[0]

# 4) Optional buffer (in meters, use a projected CRS)
if USE_BUFFER and BUFFER_KM > 0:
    # MAGNA-SIRGAS / Bogotá zone
    country_poly = gpd.GeoSeries([country_poly], crs="EPSG:4326") \
                      .to_crs("EPSG:3116") \
                      .buffer(BUFFER_KM * 1000) \
                      .to_crs("EPSG:4326") \
                      .geometry.iloc[0]

# 5) Read the .loc file (comma-separated, no header)
col_names = ["date", "time", "lat", "lon", "energy", "nsta"]
df = pd.read_csv(
    INPUT_LOC,
    sep=",",
    header=None,
    names=col_names,
    skipinitialspace=True,
    dtype={"date":"string","time":"string","lat":"float64","lon":"float64","energy":"float64","nsta":"int64"},
    engine="python"
)

# 6) Basic coordinate sanity filter
df = df[df["lat"].between(-90, 90) & df["lon"].between(-180, 180)]

# 7) Quick bbox prefilter using polygon bounds (fast)
minx, miny, maxx, maxy = country_poly.bounds
df_bbox = df[(df["lon"] >= minx) & (df["lon"] <= maxx) & (df["lat"] >= miny) & (df["lat"] <= maxy)]
if df_bbox.empty:
    Path(OUTPUT_LOC).write_text("")  # create empty output
    print("No rows fell inside the national bbox. Saved empty result.")
else:
    # 8) Build GeoDataFrame and perform polygon test (use intersects to include edges)
    gdf = gpd.GeoDataFrame(
        df_bbox,
        geometry=gpd.points_from_xy(df_bbox["lon"], df_bbox["lat"]),
        crs="EPSG:4326"
    )
    inside = gdf[gdf.intersects(country_poly)]

    # 9) Save in the same 5-column .loc format (no header)
    inside[col_names].to_csv(OUTPUT_LOC, index=False, header=False)

    print(f"✅ Saved: {Path(OUTPUT_LOC).resolve()}")
    print(f"➡ Rows kept after polygon filter: {len(inside):,}")
