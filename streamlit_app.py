# streamlit_app.py

import streamlit as st
import geopandas as gpd
import pydeck as pdk
import matplotlib.pyplot as plt
import matplotlib as mpl
import streamlit.components.v1 as components
import numpy as np
import altair as alt


@st.cache_data
def load_data():
    gdf = gpd.read_file("data/forest_stands_with_elev.geojson")
    gdf = gdf.to_crs(epsg=4326)
    # add color ramp based on canopy height
    min_h, max_h = gdf.mean_canopy.min(), gdf.mean_canopy.max()

    def height_to_color(h):
        # green to red gradient
        ratio = (h - min_h) / (max_h - min_h) if max_h > min_h else 0
        r = int(255 * ratio)
        g = int(255 * (1 - ratio))
        return [r, g, 50, 180]

    gdf["fill_color"] = gdf.mean_canopy.apply(height_to_color)
    return gdf


st.set_page_config(page_title="Forest Stands Canopy Height", layout="wide")
st.title("🌲 Forest Stand Canopy Height Approximation")
st.subheader("Understand the distribution of forest canopy heights in a set of forest stands.")
st.markdown(
    """
    The forest canopy height is estimated based upon a Digital Surface Model freely available from [Copernicus on AWS](https://registry.opendata.aws/copernicus-dem/).
    In this example, a set of forest stands in Finland from [QGIS Training Data – Forestry](https://github.com/qgis/QGIS-Training-Data/tree/master/exercise_data/forestry) is used.
    To approximate the canopy height a greyscale morphological opening window function from scipy with a window size of 150 m^2 was used to estimate a DTM (digital terrain model or bare-earth model) from the provided DSM (digital surface model).  
    Use the **Canopy height range** slider in the sidebar to filter forest plots by mean canopy height, and copy the list of plot IDs within your selected range to the clipboard for further analysis.
    """
)

gdf = load_data()

# Sidebar: filter by canopy height
min_c, max_c = float(gdf.mean_canopy.min()), float(gdf.mean_canopy.max())
sel = st.sidebar.slider("Canopy height range (m)", min_c, max_c, (min_c, max_c))

# Sidebar: color legend for canopy height
norm = mpl.colors.Normalize(vmin=min_c, vmax=max_c)
sm = mpl.cm.ScalarMappable(norm=norm, cmap='RdYlGn_r')
sm.set_array([])  # required for the colorbar

fig, ax = plt.subplots(figsize=(4, 0.5))
fig.colorbar(
    sm,
    cax=ax,
    orientation='horizontal',
    label='Mean Canopy Height (m)'
)
st.sidebar.pyplot(fig)

# Compute the filtered df based on our sidebar selection
filtered = gdf[(gdf.mean_canopy >= sel[0]) & (gdf.mean_canopy <= sel[1])]

# Build a Pydeck PolygonLayer for canopy height extrusion
layer = pdk.Layer(
    "PolygonLayer",
    data=filtered,
    get_polygon="geometry.coordinates",
    get_fill_color="fill_color",
    stroked=True,
    get_line_color=[0, 0, 0, 200],
    get_line_width=1,
    extruded=True,
    get_elevation="get mean_canopy",
    elevation_scale=500,  # TODO Why am I not seeing extrusion effect?
    auto_highlight=True,
    pickable=True,
)

# Compute viewport from filtered data bounds
bounds = filtered.total_bounds  # [minLon, minLat, maxLon, maxLat]
view_state = pdk.ViewState(
    latitude=(bounds[1] + bounds[3]) / 2,
    longitude=(bounds[0] + bounds[2]) / 2,
    zoom=13,
    pitch=45,
    bearing=30,
)

# Render Pydeck chart
deck = pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v9",
    layers=[layer],
    initial_view_state=view_state,
    tooltip={ #  TODO we need min and max and whatever else is in there too
        "text": (
            "Stand ID: {StandID}\n"
            "Mean Elevation: {mean_elev} m\n"
            "Mean Canopy Height: {mean_canopy} m"
        )
    },
)
st.subheader("Forest Stands Map")

st.pydeck_chart(deck, use_container_width=True)



st.subheader("Mean Forest Stand Canopy Height Scatter Plot")
plot_df = filtered.sort_values("mean_canopy").copy()
plot_df['StandID_str'] = plot_df['StandID'].astype(str)

chart = alt.Chart(plot_df).mark_circle(size=60).encode(
    x=alt.X('StandID_str:N', title='Stand ID',axis=alt.Axis(labels=False, ticks=False)),
    y=alt.Y('mean_canopy:Q', title='Mean Canopy Height (m)'),
    tooltip=[
        alt.Tooltip('StandID_str:N', title='Stand ID'),
        alt.Tooltip('mean_canopy:Q', title='Mean Canopy Height (m)')
    ]
).interactive()

st.altair_chart(chart, use_container_width=True)

# Display the loaded GeoDataFrame
st.subheader("Forest Stands Data")
st.dataframe(gdf)


# Copy Stand IDs to clipboard
ids = filtered.sort_values("mean_canopy", ascending=False)["StandID"].tolist()
ids_str = ",".join(map(str, ids))
components.html(
    f"""
<div>
  <textarea id="ids" readonly style="width:100%;height:100px;">{ids_str}</textarea>
  <br/>
  <button onclick="navigator.clipboard.writeText(document.getElementById('ids').value)">
    Copy IDs to clipboard
  </button>
</div>
""",
    height=200,
)
