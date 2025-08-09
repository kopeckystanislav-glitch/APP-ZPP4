import streamlit as st
import pandas as pd
import unicodedata
import os
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# ====== Funkce ======
def normalize_text(text: str) -> str:
    """Odstraní diakritiku a převede na malá písmena."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(text))
        if unicodedata.category(c) != 'Mn'
    ).lower()

def vyhledat(df: pd.DataFrame, term: str, sloupec: str = None) -> pd.DataFrame:
    """Vyhledávání bez diakritiky, volitelně jen ve vybraném sloupci."""
    if not term:
        return df
    term_norm = normalize_text(term)
    if sloupec and sloupec in df.columns:
        mask = df[sloupec].apply(lambda x: term_norm in normalize_text(x))
    else:
        mask = df.apply(
            lambda row: any(term_norm in normalize_text(cell) for cell in row),
            axis=1
        )
    return df[mask]

def zobraz_tabulku_okamzite(df: pd.DataFrame, placeholder="", sloupec_hledani=None):
    """Zobrazení tabulky s okamžitým filtrováním."""
    with st.expander("⚙️ Zobrazení sloupců"):
        sloupce = st.multiselect(
            "Vyber sloupce",
            options=list(df.columns),
            default=list(df.columns)
        )
    df_view = df[sloupce] if sloupce else df
    df_view = df_view.reset_index(drop=True)

    hledat = st.text_input("🔎 Hledat:", value="", placeholder=placeholder)
    df_view = vyhledat(df_view, hledat, sloupec=sloupec_hledani)

    gb = GridOptionsBuilder.from_dataframe(df_view)
    gb.configure_default_column(
        filter=False, sortable=True, resizable=True,
        wrapText=True, autoHeight=True
    )
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=25)
    grid_options = gb.build()

    AgGrid(
        df_view,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.NO_UPDATE,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        height=600,
        theme="balham"
    )

def tlacitko_zpet_horni(akce, key="zpet_top"):
    if st.button("⬅️ Zpět", key=key):
        akce()
        st.rerun()

def tlacitko_zpet_dolni(akce, key="zpet_bottom"):
    st.markdown("---")
    if st.button("⬅️ Zpět", key=key):
        akce()
        st.rerun()

# ====== Nastavení aplikace ======
st.set_page_config(page_title="Aplikace pro vyšetřovatele požárů", layout="wide")

if "zvolen_modul" not in st.session_state:
    st.session_state.zvolen_modul = None
if "aktivni_podmodul" not in st.session_state:
    st.session_state.aktivni_podmodul = None

# ====== Hlavní nadpis ======
st.title("🔎 Aplikace pro vyšetřovatele požárů 🔎")

# ====== Hlavní menu ======
if st.session_state.zvolen_modul is None:
    st.markdown("## 📂 Moduly")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔥 Požáry"):
            st.session_state.zvolen_modul = "pozary"
            st.rerun()
    with col2:
        if st.button("🧰 Podpora"):
            st.session_state.zvolen_modul = "podpora"
            st.rerun()

# ====== Modul Podpora ======
elif st.session_state.zvolen_modul == "podpora":
    if st.session_state.aktivni_podmodul is None:
        st.markdown("## 🧰 Modul: Podpora")
        tlacitko_zpet_horni(lambda: st.session_state.update({"zvolen_modul": None}))
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📌 PTCH"):
                st.session_state.aktivni_podmodul = "PTCH"
                st.rerun()
            if st.button("💥 Iniciátory"):
                st.session_state.aktivni_podmodul = "INICIÁTORY"
                st.rerun()
        with col2:
            if st.button("📖 Normy"):
                st.session_state.aktivni_podmodul = "NORMY"
                st.rerun()
            if st.button("📎 Jiné"):
                st.warning("Tento modul zatím není implementován.")
                tlacitko_zpet_dolni(lambda: st.session_state.update({"zvolen_modul": None}))

    # --- Podmodul PTCH ---
    elif st.session_state.aktivni_podmodul == "PTCH":
        st.subheader("📌 PTCH")
        tlacitko_zpet_horni(lambda: st.session_state.update({"aktivni_podmodul": None}))
        try:
            df = pd.read_excel("data ptch.xlsx", sheet_name="PTCH", engine="openpyxl")
            zobraz_tabulku_okamzite(df, placeholder="např. dřevo", sloupec_hledani="Název")
        except Exception as e:
            st.error(f"Chyba při načítání dat PTCH: {e}")
        tlacitko_zpet_dolni(lambda: st.session_state.update({"aktivni_podmodul": None}))

    # --- Podmodul Iniciátory ---
    elif st.session_state.aktivni_podmodul == "INICIÁTORY":
        st.subheader("💥 Iniciátory")
        tlacitko_zpet_horni(lambda: st.session_state.update({"aktivni_podmodul": None}))
        try:
            df = pd.read_excel("data ptch.xlsx", sheet_name="INICIÁTORY", engine="openpyxl")
            zobraz_tabulku_okamzite(df, placeholder="např. kabel", sloupec_hledani="Název")
        except Exception as e:
            st.error(f"Chyba při načítání dat Iniciátory: {e}")
        tlacitko_zpet_dolni(lambda: st.session_state.update({"aktivni_podmodul": None}))

    # --- Podmodul Normy ---
    elif st.session_state.aktivni_podmodul == "NORMY":
        st.subheader("📖 Normy")
        tlacitko_zpet_horni(lambda: st.session_state.update({"aktivni_podmodul": None}))
        normy = {
            "ČSN 061008 – Požární bezpečnost tepelných zařízení (prostupy komínů)": "pdf/ČSN 061008.pdf",
            "ČSN 730872 – Ochrana staveb proti šíření požáru vzduchotechnických zařízením": "pdf/ČSN 730872.pdf",
            "ČSN 734230 – Krby s otevřeným a uzavíratelným ohništěm": "pdf/ČSN 734230.pdf",
            "ČSN 734201 – Komíny a kouřovody – Navrhování, provádění a připojování spotřebičů paliv": "pdf/ČSN 734201.pdf"
        }
        for nazev, cesta in normy.items():
            if os.path.exists(cesta):
                with open(cesta, "rb") as f:
                    st.download_button(f"📥 {nazev}", f, file_name=os.path.basename(cesta))
            else:
                st.error(f"Soubor {cesta} nebyl nalezen.")
        tlacitko_zpet_dolni(lambda: st.session_state.update({"aktivni_podmodul": None}))

# ====== Modul Požáry ======
elif st.session_state.zvolen_modul == "pozary":
    st.markdown("## 🔥 Modul: Požáry")
    tlacitko_zpet_horni(lambda: st.session_state.update({"zvolen_modul": None}))
    st.info("Tento modul ještě není implementován.")
    tlacitko_zpet_dolni(lambda: st.session_state.update({"zvolen_modul": None}))
