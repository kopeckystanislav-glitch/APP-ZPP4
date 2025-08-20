
from __future__ import annotations
import streamlit as st

def render_tab(ctx):
    st.subheader("🗣️ Svědectví")
    ctx.data["witnesses"] = st.text_area(
        "Záznam svědectví / výpovědí",
        value=ctx.data.get("witnesses",""),
        height=220, key=ctx.key("wit")
    )
