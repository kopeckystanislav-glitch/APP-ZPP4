
from __future__ import annotations
import streamlit as st

def render_tab(ctx):
    st.subheader("🌦️ Podmínky prostředí")
    cond = ctx.data.get("conditions") or {}
    c1,c2,c3 = st.columns(3)
    with c1:
        cond["weather"] = st.text_input("Počasí", value=cond.get("weather",""), key=ctx.key("cond_w"))
    with c2:
        try: prev = float(cond.get("temperature_c", 0))
        except Exception: prev = 0.0
        cond["temperature_c"] = int(st.number_input("Teplota [°C]", value=float(round(prev)), step=1.0, format="%.0f", key=ctx.key("cond_t")))
    with c3:
        cond["visibility"] = st.text_input("Viditelnost", value=cond.get("visibility",""), key=ctx.key("cond_vis"))
    ctx.data["conditions"] = cond
