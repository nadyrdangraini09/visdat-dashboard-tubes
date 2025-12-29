import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px

# ======================================================
# 1. KONFIGURASI HALAMAN
# ======================================================
st.set_page_config(
    layout="wide",
    page_title="Houston Restaurant Explorer"
)

# ======================================================
# 2. CSS UNTUK VISUAL POLISH
# ======================================================
st.markdown("""
<style>

/* ===============================
   BACKGROUND UTAMA (PASTEL)
   =============================== */
.stApp {
    background: linear-gradient(
        180deg,
        #f0f9ff 0%,
        #e0f2fe 50%,
        #f8fafc 100%
    );
}

/* ===============================
   SIDEBAR
   =============================== */
section[data-testid="stSidebar"] {
    background-color: #bae6fd;
    padding: 20px;
}

/* Sidebar title */
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label {
    color: #0f172a;
    font-weight: 600;
}

/* ===============================
   JUDUL & TEKS
   =============================== */
h1 {
    color: #0f172a;
    font-weight: 800;
}

h2, h3 {
    color: #1e293b;
}

/* ===============================
   METRIC CARD
   =============================== */
[data-testid="stMetric"] {
    background-color: #ffffff;
    padding: 16px;
    border-radius: 16px;
    border: 1px solid #e5e7eb;
    box-shadow: 0px 6px 16px rgba(0,0,0,0.08);
}

/* ===============================
   EXPANDER
   =============================== */
.stExpander {
    background-color: #ffffff;
    border-radius: 16px;
    border: 1px solid #e5e7eb;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
}

/* ===============================
   SLIDER & INPUT
   =============================== */
.stSlider > div {
    color: #2563eb;
}

</style>
""", unsafe_allow_html=True)

# ======================================================
# 3. LOAD & TRANSFORM DATA
# ======================================================
@st.cache_data
def load_data():
    df = pd.read_csv("restaurants.csv", on_bad_lines="skip")

    price_mapping = {
        "$": "Murah",
        "$$": "Sedang",
        "$$$": "Mahal",
        "$$$$": "Orang Kaya"
    }
    df["priceRange"] = df["priceRange"].map(price_mapping)

    pickup_mapping = {True: "Iya", False: "Tidak"}
    df["asapPickupAvailable"] = df["asapPickupAvailable"].map(pickup_mapping)

    df = df.dropna(subset=["latitude", "longitude"])
    df["averageRating"] = pd.to_numeric(df["averageRating"], errors="coerce")
    df["asapDeliveryTimeMinutes"] = pd.to_numeric(df["asapDeliveryTimeMinutes"], errors="coerce")
    df["asapPickupMinutes"] = pd.to_numeric(df["asapPickupMinutes"], errors="coerce")

    return df

# ======================================================
# 4. MAIN APP
# ======================================================
try:
    data = load_data()

    st.title("🍔 Houston Restaurant Interactive Explorer")
    st.markdown(
        "Dashboard interaktif untuk mengeksplorasi lokasi, rating, harga, "
        "dan waktu layanan restoran di Houston."
    )

    # ==================================================
    # SIDEBAR FILTER
    # ==================================================
    st.sidebar.header("🔍 Filter Pencarian")

    search_query = st.sidebar.text_input("Cari Nama Restoran")

    price_order = ["Murah", "Sedang", "Mahal", "Orang Kaya"]
    available_prices = [p for p in price_order if p in data["priceRange"].unique()]
    selected_price = st.sidebar.multiselect(
        "Kategori Harga",
        available_prices,
        default=available_prices
    )

    max_rating = st.sidebar.slider(
        "Rating Maksimal",
        0.0, 5.0, 5.0, 0.1
    )

    max_del_time = int(data["asapDeliveryTimeMinutes"].max())
    selected_del_time = st.sidebar.slider(
        "Maksimum Waktu Kirim (Menit)",
        0, max_del_time, max_del_time
    )

    max_pick_time = int(data["asapPickupMinutes"].max())
    selected_pick_time = st.sidebar.slider(
        "Maksimum Waktu Pickup (Menit)",
        0, max_pick_time, max_pick_time
    )

    selected_pickup = st.sidebar.selectbox(
        "Tersedia Layanan Pickup?",
        ["Semua", "Iya", "Tidak"]
    )

    map_measure = st.sidebar.selectbox(
        "Ukuran Titik Peta Berdasarkan",
        ["Rating Restoran", "Waktu Pengiriman", "Waktu Pickup"]
    )

    # ==================================================
    # FILTER DATA
    # ==================================================
    mask = (
        (data["averageRating"] <= max_rating) &
        (data["priceRange"].isin(selected_price)) &
        (data["asapDeliveryTimeMinutes"] <= selected_del_time) &
        (data["asapPickupMinutes"] <= selected_pick_time)
    )

    if selected_pickup != "Semua":
        mask &= data["asapPickupAvailable"] == selected_pickup

    if search_query:
        mask &= data["name"].str.contains(search_query, case=False, na=False)

    filtered = data[mask]

    # ==================================================
    # MAP
    # ==================================================
    st.subheader("📍 Peta Persebaran Restoran")

    if map_measure == "Rating Restoran":
        radius_calc = "averageRating * 18"
    elif map_measure == "Waktu Pengiriman":
        radius_calc = "asapDeliveryTimeMinutes * 2"
    else:
        radius_calc = "asapPickupMinutes * 5"

    st.pydeck_chart(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/dark-v11",
            initial_view_state=pdk.ViewState(
                latitude=filtered["latitude"].mean() if not filtered.empty else 29.76,
                longitude=filtered["longitude"].mean() if not filtered.empty else -95.36,
                zoom=11,
                pitch=35
            ),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=filtered,
                    get_position="[longitude, latitude]",
                    get_radius=radius_calc,
                    get_fill_color="""
                    priceRange == 'Murah' ? [34,197,94,180] :
                    priceRange == 'Sedang' ? [250,204,21,180] :
                    priceRange == 'Mahal' ? [251,146,60,180] :
                    [239,68,68,180]
                    """,
                    pickable=True,
                )
            ],
            tooltip={
                "html": """
                <b>{name}</b><br/>
                ⭐ Rating: {averageRating}<br/>
                💰 Harga: {priceRange}<br/>
                🚗 Pickup: {asapPickupAvailable}
                """
            }
        )
    )

    st.divider()

    # ==================================================
    # METRICS
    # ==================================================
    st.subheader("📊 Statistik Ringkas")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Restoran Ditemukan", len(filtered))
    m2.metric("Rata-rata Rating", f"{filtered['averageRating'].mean():.2f}" if not filtered.empty else "0")
    m3.metric("Rerata Waktu Kirim", f"{int(filtered['asapDeliveryTimeMinutes'].mean())} mnt" if not filtered.empty else "0")
    m4.metric("Rerata Waktu Pickup", f"{int(filtered['asapPickupMinutes'].mean())} mnt" if not filtered.empty else "0")

    # ==================================================
    # CHARTS
    # ==================================================
    if not filtered.empty:
        c1, c2 = st.columns(2)

        with c1:
            st.write("**Distribusi Kategori Harga**")
            price_counts = filtered["priceRange"].value_counts().reset_index()
            price_counts.columns = ["Kategori", "Jumlah"]

            fig_price = px.pie(
                price_counts,
                values="Jumlah",
                names="Kategori",
                hole=0.45,
                color="Kategori",
                color_discrete_map={
                    "Murah": "#22c55e",
                    "Sedang": "#facc15",
                    "Mahal": "#fb923c",
                    "Orang Kaya": "#ef4444"
                }
            )
            st.plotly_chart(fig_price, use_container_width=True)

        with c2:
            st.write("**Ketersediaan Layanan Pickup**")
            pickup_df = filtered["asapPickupAvailable"].value_counts().reset_index()
            pickup_df.columns = ["Pickup", "Jumlah"]

            fig_pickup = px.bar(
                pickup_df,
                x="Pickup",
                y="Jumlah",
                color="Pickup",
                color_discrete_map={
                    "Iya": "#3b82f6",
                    "Tidak": "#9ca3af"
                }
            )
            st.plotly_chart(fig_pickup, use_container_width=True)

    # ==================================================
    # TABLE
    # ==================================================
    with st.expander("🔍 Lihat Detail Data"):
        st.dataframe(
            filtered[
                [
                    "name",
                    "averageRating",
                    "priceRange",
                    "asapPickupAvailable",
                    "asapDeliveryTimeMinutes",
                    "asapPickupMinutes",
                    "displayAddress"
                ]
            ]
            .style
            .background_gradient(subset=["averageRating"], cmap="YlGn")
            .background_gradient(subset=["asapDeliveryTimeMinutes"], cmap="OrRd")
            .background_gradient(subset=["asapPickupMinutes"], cmap="Blues"),
            use_container_width=True
        )

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
