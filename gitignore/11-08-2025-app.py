import os
import base64
import unicodedata
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html

# =========================
# Nastavení stránky
# =========================
st.set_page_config(page_title="Aplikace pro vyšetřovatele požárů", layout="wide")

# =========================
# Util / pomocné funkce
# =========================
def normalize_text(text: str) -> str:
    """Odstraní diakritiku a převede na malá písmena (pro robustní vyhledávání)."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(text))
        if unicodedata.category(c) != 'Mn'
    ).lower()

def filter_df(df: pd.DataFrame, q_all: str = "", q_col: str = "", col_name: str | None = None) -> pd.DataFrame:
    """Globální i sloupcový filtr (bez diakritiky)."""
    out = df.copy()
    if q_col and col_name and col_name in out.columns:
        qn = normalize_text(q_col)
        out = out[out[col_name].astype(str).map(lambda x: qn in normalize_text(x))]
    elif q_all:
        qn = normalize_text(q_all)
        mask = out.apply(lambda row: any(qn in normalize_text(v) for v in row.astype(str)), axis=1)
        out = out[mask]
    return out.reset_index(drop=True)

def navigate_to(modul=None, podmodul=None):
    # když opouštíme Požáry, smažeme přihlášení a zvolený podmodul
    if modul != "pozary":
        st.session_state.oec = None
        st.session_state.pozary_submodul = None
    st.session_state.zvolen_modul = modul
    st.session_state.aktivni_podmodul = podmodul
    st.rerun()

def back_button(area_key: str):
    if st.button("⬅️ Zpět", key=f"btn_back_{area_key}", use_container_width=True):
        navigate_to(None, None)

def open_pdf_new_tab(cesta: str):
    """Otevře PDF v nové kartě pomocí BLOB URL (spolehlivé na tabletech/Chrome)."""
    if not os.path.exists(cesta):
        st.error(f"Soubor {cesta} nebyl nalezen.")
        return
    size_b = os.path.getsize(cesta)
    if size_b == 0:
        st.error("Soubor je prázdný (0 B).")
        return
    with open(cesta, "rb") as f:
        data_b64 = base64.b64encode(f.read()).decode("utf-8")

    html(
        f"""
        <script>
        (function(){{
          const b64 = "{data_b64}";
          const bytes = atob(b64);
          const arr = new Uint8Array(bytes.length);
          for (let i=0; i<bytes.length; i++) arr[i] = bytes.charCodeAt(i);
          const blob = new Blob([arr], {{type: "application/pdf"}});
          const url = URL.createObjectURL(blob);
          window.open(url, "_blank");
        }})();
        </script>
        """,
        height=0,
    )

# =========================
# Inicializace stavu
# =========================
if "zvolen_modul" not in st.session_state:
    st.session_state.zvolen_modul = None
if "aktivni_podmodul" not in st.session_state:
    st.session_state.aktivni_podmodul = None
# Přihlášení pro modul Požáry
if "oec" not in st.session_state:
    st.session_state.oec = None  # 6místné osobní číslo
if "pozary_submodul" not in st.session_state:
    st.session_state.pozary_submodul = None  # "checklist" | "report" | None

# =========================
# CSS – velká tlačítka
# =========================
st.markdown("""
<style>
  h1.app-title {
    text-align:center;
    color: #111;
    padding: 8px 10px; border-radius: 12px;
    background: linear-gradient(to right, #ff512f, #dd2476);
    font-size: clamp(20px, 3.8vw, 34px);
    line-height: 1.25;
    margin-top: 6px; margin-bottom: 6px;
  }
  .big-btn > button {
    font-size: 20px !important;
    padding-top: 16px !important;
    padding-bottom: 16px !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
  }
</style>
""", unsafe_allow_html=True)

# =========================
# Horní lišta
# =========================
st.markdown("<h1 class='app-title'>🔎 Aplikace pro vyšetřovatele požárů 🔎</h1>", unsafe_allow_html=True)
tb1, tb2 = st.columns([1,1], gap="small")
with tb1:
    st.markdown('<div class="big-btn">', unsafe_allow_html=True)
    if st.button("⬅️ Zpět", key="top_back", use_container_width=True):
        if st.session_state.get("aktivni_podmodul"):
            navigate_to(st.session_state.zvolen_modul, None)
        else:
            navigate_to(None, None)
    st.markdown('</div>', unsafe_allow_html=True)
with tb2:
    st.markdown('<div class="big-btn">', unsafe_allow_html=True)
    if st.button("🏠 Domů", key="top_home", use_container_width=True):
        navigate_to(None, None)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# =========================
# Obsah – Moduly / Podmoduly
# =========================
if st.session_state.zvolen_modul is None:
    st.markdown("## 📂 Moduly")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        if st.button("🔥 Požáry", key="btn_pozary", use_container_width=True):
            navigate_to("pozary", None)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        if st.button("🧰 Podpora", key="btn_podpora", use_container_width=True):
            navigate_to("podpora", None)
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# Modul: Požáry (OEČ login)
# -------------------------
elif st.session_state.zvolen_modul == "pozary":
    st.markdown("## 🔥 Modul: Požáry")

    # 1) Přihlášení OEČ (6 číslic)
    if not st.session_state.oec:
        st.markdown("### Přihlášení")
        st.markdown("Zadej svůj **OEČ** (šestimístné osobní číslo).")
        with st.form("form_oec", clear_on_submit=False):
            oec_in = st.text_input("OEČ", value="", max_chars=6, help="Zadej 6 číslic bez mezer.", placeholder="např. 123456")
            col_l, col_r = st.columns([1,1])
            with col_l:
                submit = st.form_submit_button("Pokračovat", use_container_width=True)
            with col_r:
                back = st.form_submit_button("⬅️ Zpět", use_container_width=True)

        if back:
            navigate_to(None, None)

        if submit:
            if oec_in and oec_in.isdigit() and len(oec_in) == 6:
                st.session_state.oec = oec_in
                st.session_state.pozary_submodul = None
                st.rerun()
            else:
                st.error("OEČ musí být **6 číslic**. Zkus to prosím znovu.")
        st.stop()

    # 2) Po přihlášení – volba podmodulu
    st.info(f"Přihlášen OEČ: **{st.session_state.oec}**")
    if st.session_state.pozary_submodul is None:
        st.markdown("### Vyber podmodul")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="big-btn">', unsafe_allow_html=True)
            if st.button("✅ Checklist", key="pozary_checklist", use_container_width=True):
                st.session_state.pozary_submodul = "checklist"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="big-btn">', unsafe_allow_html=True)
            if st.button("📝 Report", key="pozary_report", use_container_width=True):
                st.session_state.pozary_submodul = "report"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        if st.button("🚪 Odhlásit OEČ", key="pozary_logout", use_container_width=True):
            st.session_state.oec = None
            st.session_state.pozary_submodul = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        if st.button("⬅️ Zpět na moduly", key="pozary_back_root", use_container_width=True):
            navigate_to(None, None)
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    # 3) Podmoduly Požáry
    if st.session_state.pozary_submodul == "checklist":
        st.subheader("✅ Checklist")
        st.write("Sem přijde obsah checklistu – formulářové položky, zaškrtávátka atd.")
        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        if st.button("⬅️ Zpět na výběr", key="pozary_back_from_checklist", use_container_width=True):
            st.session_state.pozary_submodul = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.pozary_submodul == "report":
        st.subheader("📝 Report")
        st.write("Sem přijde editor reportu – textová pole, přílohy, ukládání atd.")
        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        if st.button("⬅️ Zpět na výběr", key="pozary_back_from_report", use_container_width=True):
            st.session_state.pozary_submodul = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# Modul: Podpora
# -------------------------
elif st.session_state.zvolen_modul == "podpora":

    if st.session_state.aktivni_podmodul is None:
        st.markdown("## 🧰 Modul: Podpora")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="big-btn">', unsafe_allow_html=True)
            if st.button("📌 PTCH", key="btn_ptch", use_container_width=True):
                st.session_state.aktivni_podmodul = "PTCH"
                st.rerun()
            if st.button("💥 Iniciátory", key="btn_iniciatory", use_container_width=True):
                st.session_state.aktivni_podmodul = "INICIÁTORY"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="big-btn">', unsafe_allow_html=True)
            if st.button("📖 Normy", key="btn_normy", use_container_width=True):
                st.session_state.aktivni_podmodul = "NORMY"
                st.rerun()
            if st.button("📎 Jiné", key="btn_jine", use_container_width=True):
                st.warning("Tento podmodul zatím není implementován.")
                st.markdown('<div class="big-btn">', unsafe_allow_html=True)
                back_button("jine")
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.aktivni_podmodul == "PTCH":
        st.subheader("📌 PTCH")
        try:
            df = pd.read_excel("data ptch.xlsx", sheet_name="PTCH", engine="openpyxl")
            with st.expander("⚙️ Zobrazení sloupců", expanded=False):
                cols = st.multiselect("Vyber sloupce", list(df.columns), default=list(df.columns))
            st.markdown("#### 🔎 Vyhledávání")
            col1, col2 = st.columns(2)
            with col1:
                q_all = st.text_input("Hledat v celé tabulce", value="", placeholder="např. dřevo")
            with col2:
                q_nazev = st.text_input("Hledat jen ve sloupci „Název“", value="")
            view = filter_df(df[cols] if cols else df, q_all=q_all, q_col=q_nazev, col_name="Název")
            view = view.reset_index(drop=True)  # jistota
            st.dataframe(view, use_container_width=True, height=560, hide_index=True)
        except Exception as e:
            st.error(f"Chyba při načítání PTCH: {e}")
        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        back_button("ptch")
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.aktivni_podmodul == "INICIÁTORY":
        st.subheader("💥 Iniciátory")
        try:
            df = pd.read_excel("data ptch.xlsx", sheet_name="INICIÁTORY", engine="openpyxl")
            with st.expander("⚙️ Zobrazení sloupců", expanded=False):
                cols = st.multiselect("Vyber sloupce", list(df.columns), default=list(df.columns))
            st.markdown("#### 🔎 Vyhledávání")
            col1, col2 = st.columns(2)
            with col1:
                q_all = st.text_input("Hledat v celé tabulce", value="", placeholder="např. kabel")
            with col2:
                q_nazev = st.text_input("Hledat jen ve sloupci „Název“", value="")
            view = filter_df(df[cols] if cols else df, q_all=q_all, q_col=q_nazev, col_name="Název")
            view = view.reset_index(drop=True)  # jistota
            st.dataframe(view, use_container_width=True, height=560, hide_index=True)
        except Exception as e:
            st.error(f"Chyba při načítání Iniciátorů: {e}")
        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        back_button("iniciatory")
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.aktivni_podmodul == "NORMY":
        st.subheader("📖 Normy (otevře se vždy v nové kartě)")
        normy = {
            "ČSN 061008 – Požární bezpečnost tepelných zařízení": "pdf/ČSN 061008.pdf",
            "ČSN 730872 – Ochrana staveb proti šíření požáru vzduchotechnických zařízení": "pdf/ČSN 730872.pdf",
            "ČSN 734230 – Krby s otevřeným a uzavíratelným ohništěm": "pdf/ČSN 734230.pdf",
            "ČSN 734201 – Komíny a kouřovody": "pdf/ČSN 734201.pdf",
        }
        for nazev, cesta in normy.items():
            st.markdown('<div class="big-btn">', unsafe_allow_html=True)
            if st.button(nazev, key=f"btn_norm_{nazev}", use_container_width=True):
                open_pdf_new_tab(cesta)  # vždy nová karta
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="big-btn">', unsafe_allow_html=True)
        back_button("normy")
        st.markdown('</div>', unsafe_allow_html=True)
