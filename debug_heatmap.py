import streamlit as st
import plotly.express as px
import pandas as pd
import uuid

st.set_page_config(layout="wide")

st.markdown("""
<style>
/* CSS Reset for consistent look */
.stApp { background-color: #0e1117; color: white; }
</style>
""", unsafe_allow_html=True)

st.title("🔥 Heatmap Click Logic Test Lab")

# 1. MOCK DATA
data = [
    {"Varlık": "KSA", "Deger": 100000, "Yuzde": 2.5, "Grup": "FON"},
    {"Varlık": "GMC", "Deger": 50000, "Yuzde": -1.2, "Grup": "FON"},
    {"Varlık": "TUPRS", "Deger": 75000, "Yuzde": 0.5, "Grup": "HISSE"},
    {"Varlık": "THYAO", "Deger": 80000, "Yuzde": 1.8, "Grup": "HISSE"},
    {"Varlık": "USD", "Deger": 120000, "Yuzde": 0.1, "Grup": "DOVIZ"},
]
df = pd.DataFrame(data)

# 2. SESSION STATE MANAGEMENT
if "active_node" not in st.session_state:
    st.session_state.active_node = None

st.write(f"🔍 **Current Active Node:** `{st.session_state.active_node}`")

# 3. DYNAMIC LABEL LOGIC REVISITED (Server Side)
# We want: Default -> Name Only. Active -> Name + Details.
def build_label(row):
    # Eğer bu satır aktifse detay göster
    if st.session_state.active_node == row['Varlık']:
        return f"<b>{row['Varlık']}</b><br><br><span style='font-size:16px; color:#00f2ff;'>₺{row['Deger']:,}<br>%{row['Yuzde']}</span>"
    # Değilse sadece isim
    return f"<b>{row['Varlık']}</b>"

df['LabelText'] = df.apply(build_label, axis=1)

# 4. CHART CREATION
fig = px.treemap(
    df,
    path=[px.Constant("PORTFÖY"), 'Grup', 'Varlık'],
    values='Deger',
    color='Yuzde',
    color_continuous_scale='RdYlGn',
    custom_data=['Varlık', 'LabelText']
)

fig.update_traces(
    hoverinfo='none',
    hovertemplate=None,
    texttemplate="%{customdata[1]}", # Server-side dinamik metin
    textposition="middle center",
    textfont=dict(size=20, family="Arial")
)

fig.update_layout(
    margin=dict(t=0, l=0, r=0, b=0),
    height=400,
    clickmode='event+select', 
    uirevision=True 
)

st.write("### 🖱️ Try clicking a box now (Raw Event Mode)")

# 5. RENDER & CAPTURE
event = st.plotly_chart(
    fig, 
    use_container_width=True, 
    on_select="rerun", 
    key="test_map_v5"
)

# 6. DEBUG VIEW
st.write("Event Output:", event)

# 7. LOGIC HANDLER
if event and "selection" in event:
    points = event["selection"]["points"]
    if points:
        clicked_pt = points[0]
        if "customdata" in clicked_pt:
             clicked_name = clicked_pt["customdata"][0]
             if st.session_state.active_node != clicked_name:
                 st.session_state.active_node = clicked_name
                 st.rerun()
    elif not points and st.session_state.active_node is not None:
         # Boş tıklama yine zum ile karışabilir, şimdilik pasif.
         pass
