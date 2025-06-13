import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="Customer Geo Insights", layout="wide")

st.title("🌍 Customer Geo Insights")
st.caption("View customer distribution by regions within each country")

# Simulated customer data at regional level
data = [
    # United States
    {"country": "USA", "region": "California", "lat": 37.7749, "lon": -122.4194, "customers": 120},
    {"country": "USA", "region": "Texas", "lat": 29.7604, "lon": -95.3698, "customers": 95},
    {"country": "USA", "region": "New York", "lat": 40.7128, "lon": -74.0060, "customers": 110},

    # India
    {"country": "India", "region": "Delhi", "lat": 28.6139, "lon": 77.2090, "customers": 150},
    {"country": "India", "region": "Mumbai", "lat": 19.0760, "lon": 72.8777, "customers": 130},
    {"country": "India", "region": "Bangalore", "lat": 12.9716, "lon": 77.5946, "customers": 125},

    # Nigeria
    {"country": "Nigeria", "region": "Lagos", "lat": 6.5244, "lon": 3.3792, "customers": 105},
    {"country": "Nigeria", "region": "Abuja", "lat": 9.0579, "lon": 7.4951, "customers": 88},
    {"country": "Nigeria", "region": "Kano", "lat": 12.0022, "lon": 8.5919, "customers": 60},

    # Germany
    {"country": "Germany", "region": "Berlin", "lat": 52.5200, "lon": 13.4050, "customers": 70},
    {"country": "Germany", "region": "Munich", "lat": 48.1351, "lon": 11.5820, "customers": 55},
    {"country": "Germany", "region": "Hamburg", "lat": 53.5511, "lon": 9.9937, "customers": 45},
]

df = pd.DataFrame(data)

# Map layer
layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position='[lon, lat]',
    get_radius='customers * 800',
    get_fill_color='[0, 150, 255, 160]',
    pickable=True,
)

# View config
view_state = pdk.ViewState(
    latitude=10,
    longitude=20,
    zoom=1.4,
    pitch=0,
)

# Show map
st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v9",
    initial_view_state=view_state,
    layers=[layer],
    tooltip={"text": "{country} - {region}\nCustomers: {customers}"}
))

# Optional table
if st.checkbox("Show regional data table"):
    st.dataframe(df)
