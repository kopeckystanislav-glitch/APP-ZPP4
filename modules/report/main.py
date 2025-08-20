
from __future__ import annotations
import streamlit as st
from . import storage
from .context import ReportCtx
from .utils import get_query_params, set_query_params
from .tabs import event as tab_event
from .tabs import conditions as tab_conditions
from .tabs import participants as tab_participants
from .tabs import witnesses as tab_witnesses
from .tabs import sketch as tab_sketch

def _force_wide_layout_css():
    st.markdown("""
    <style>
      .stAppViewContainer .main .block-container{max-width:100%!important;padding:1rem;}
      .element-container:has(> iframe){width:100%!important;}
    </style>
    """, unsafe_allow_html=True)

def render_report():
    _force_wide_layout_css()
    st.markdown("## 📝 Report")

    oec = st.session_state.get("oec")
    if not oec:
        q = get_query_params(st)
        oec = q.get("oec")
        if isinstance(oec, list): oec = oec[0]
        if oec: st.session_state["oec"] = str(oec)
    if not oec:
        st.error("Chybí OEČ v relaci. Vrať se prosím o krok zpět a přihlaš se.")
        st.stop()

    with st.sidebar:
        st.markdown("### 📄 Reporty")
        if st.button("➕ Založit nový report", use_container_width=True):
            rid = storage.gen_report_id(oec)
            storage.write_json(storage.report_path(rid), storage.ensure_skeleton(rid, oec))
            st.session_state.current_report_id = rid
            st.rerun()

        my_reports = storage.list_reports_for(oec)
        if my_reports:
            labels = [f"{r['title']} ({r['id']})" for r in my_reports]
            ids = [r["id"] for r in my_reports]
            idx = st.selectbox("Vyber report", list(range(len(labels))), format_func=lambda i: labels[i] if labels else "", key="sb_select_any")
            if st.button("Otevřít", use_container_width=True):
                st.session_state.current_report_id = ids[idx]
                st.rerun()
        else:
            st.info("Zatím nemáš žádný report.")

    rid = st.session_state.get("current_report_id")
    if not rid:
        st.info("Vyber existující report vlevo, nebo založ nový v levém panelu."); st.stop()

    path = storage.report_path(rid)
    data = storage.read_json(path) or storage.ensure_skeleton(rid, oec)
    ctx = ReportCtx(rid=rid, data=data, oec=oec)

    c1,c2,c3 = st.columns([3,1,1])
    with c1:
        use_custom = st.checkbox("Použít vlastní název", value=(data.get("meta",{}).get("title") != rid), key=f"use_custom_{rid}")
        if use_custom:
            title = st.text_input("Název reportu", value=data.get("meta",{}).get("title") or rid, key=f"title_{rid}")
            data.setdefault("meta",{})["title"] = (title or rid).strip()
        else:
            st.text_input("Název reportu (ID)", value=rid, key=f"title_ro_{rid}", disabled=True)
            data.setdefault("meta",{})["title"] = rid
    with c2:
        if st.button("💾 Uložit průběh", use_container_width=True):
            ctx.save(); st.success("Uloženo.")
    with c3:
        if st.button("💾✅ Uložit a zavřít", use_container_width=True):
            ctx.save(); st.session_state.current_report_id = None; st.rerun()

    if st.button("🚪 Zavřít bez uložení", use_container_width=True):
        st.session_state.current_report_id = None; st.rerun()

    st.markdown("---")

    t_event, t_cond, t_part, t_wit, t_sk = st.tabs(["Událost","Podmínky","Účastníci","Svědectví","Náčrtek"])
    with t_event: tab_event.render_tab(ctx)
    with t_cond:  tab_conditions.render_tab(ctx)
    with t_part:  tab_participants.render_tab(ctx)
    with t_wit:   tab_witnesses.render_tab(ctx)
    with t_sk:    tab_sketch.render_tab(ctx)

    st.markdown("---")
    ctx.data["notes"] = st.text_area("🗒️ Poznámky (společné)", value=ctx.data.get("notes",""), height=140, key=f"notes_{rid}")

    b1,b2,b3 = st.columns(3)
    with b1:
        if st.button("💾 Uložit (dole)", use_container_width=True): ctx.save(); st.success("Uloženo.")
    with b2:
        if st.button("💾✅ Uložit a zavřít (dole)", use_container_width=True): ctx.save(); st.session_state.current_report_id=None; st.rerun()
    with b3:
        if st.button("🚪 Zavřít bez uložení (dole)", use_container_width=True): st.session_state.current_report_id=None; st.rerun()
