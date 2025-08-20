
from __future__ import annotations
import streamlit as st
from ..utils import safe_date, safe_time

def _addr_inputs(ctx, data: dict) -> dict:
    a1, a2, a3 = st.columns([1,1,1])
    with a1:
        data["kraj"]  = st.text_input("Kraj",  value=data.get("kraj",""),  key=ctx.key("addr_kraj"))
        data["obec"]  = st.text_input("Obec / Město", value=data.get("obec",""), key=ctx.key("addr_obec"))
    with a2:
        data["ulice"] = st.text_input("Ulice", value=data.get("ulice",""), key=ctx.key("addr_ulice"))
        data["cp"]    = st.text_input("Číslo popisné", value=data.get("cp",""), key=ctx.key("addr_cp"))
    with a3:
        data["co"]       = st.text_input("Číslo orientační", value=data.get("co",""), key=ctx.key("addr_co"))
        data["parcelni"] = st.text_input("Číslo parcelní", value=data.get("parcelni",""), key=ctx.key("addr_parc"))
        data["psc"]      = st.text_input("PSČ", value=data.get("psc",""), key=ctx.key("addr_psc"))
    return data

def render_tab(ctx):
    st.subheader("📆 Událost")
    ev = ctx.data.get("event") or {}

    c1,c2,c3 = st.columns(3)
    with c1:
        ev["datum_vzniku"] = st.date_input("Datum vzniku",
            value=safe_date(ev.get("datum_vzniku")), key=ctx.key("ev_dv")).isoformat()
    with c2:
        ev["cas_vzniku"] = st.time_input("Čas vzniku",
            value=safe_time(ev.get("cas_vzniku")), step=60, key=ctx.key("ev_cv")).strftime("%H:%M:%S")
    with c3:
        st.caption("")

    c4,c5,c6 = st.columns(3)
    with c4:
        ev["datum_zpozorovani"] = st.date_input("Datum zpozorování",
            value=safe_date(ev.get("datum_zpozorovani")), key=ctx.key("ev_dz")).isoformat()
    with c5:
        ev["cas_zpozorovani"] = st.time_input("Čas zpozorování",
            value=safe_time(ev.get("cas_zpozorovani")), step=60, key=ctx.key("ev_cz")).strftime("%H:%M:%S")
    with c6:
        st.caption("")

    c7,c8,c9 = st.columns(3)
    with c7:
        ev["datum_ohlaseni"] = st.date_input("Datum ohlášení na KOPIS",
            value=safe_date(ev.get("datum_ohlaseni")), key=ctx.key("ev_do")).isoformat()
    with c8:
        ev["cas_ohlaseni"] = st.time_input("Čas ohlášení na KOPIS",
            value=safe_time(ev.get("cas_ohlaseni")), step=60, key=ctx.key("ev_co")).strftime("%H:%M:%S")
    with c9:
        st.caption("")

    st.markdown("**Adresa**")
    ev["adresa"] = _addr_inputs(ctx, ev.get("adresa") or {})
    ctx.data["event"] = ev
