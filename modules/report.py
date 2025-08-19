# modules/report.py
from __future__ import annotations

import json
import uuid
import datetime as dt
from pathlib import Path
import re
from typing import Dict, List, Any, Optional
import base64

import streamlit as st

# volitelné moduly pro kreslení a obrázky
try:
    from streamlit_drawable_canvas import st_canvas  # ponecháno do budoucna
    HAS_CANVAS = True
except Exception:
    HAS_CANVAS = False

try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    HAS_PIL = False

# ============ Konstanty a pomocné věci ============
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> dt.datetime:
    return dt.datetime.now()


def _safe_date(val) -> dt.date:
    if isinstance(val, dt.date):
        return val
    if isinstance(val, str) and val:
        try:
            return dt.date.fromisoformat(val)
        except Exception:
            pass
    return dt.date.today()


def _safe_time(val) -> dt.time:
    if isinstance(val, dt.time):
        return val
    if isinstance(val, str) and val:
        try:
            parts = val.split(":")
            if len(parts) >= 2:
                h, m = int(parts[0]), int(parts[1])
                s = int(parts[2]) if len(parts) > 2 else 0
                return dt.time(hour=h, minute=m, second=s)
        except Exception:
            pass
    return dt.time(0, 0, 0)


def _read_json(p: Path) -> Dict[str, Any]:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_json(p: Path, data: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    tmp.replace(p)


def _current_oec() -> Optional[str]:
    return st.session_state.get("oec")


def _get_query_params() -> Dict[str, Any]:
    try:
        return dict(st.query_params)
    except Exception:
        return dict(st.experimental_get_query_params())


def _set_query_params(params: Dict[str, Any]) -> None:
    try:
        st.query_params.update(params)
    except Exception:
        st.experimental_set_query_params(**params)


def _gen_report_id(oec: str) -> str:
    now = _now()
    t = now.strftime("%H:%M")
    d = now.strftime("%d.%m.%Y")
    return f"{t}_{d}_{oec}"


def _fs_safe(name: str) -> str:
    return re.sub(r'[<>:"/\|?*]', '-', name)


def _report_path(report_id: str) -> Path:
    safe = _fs_safe(report_id)
    return REPORTS_DIR / f"{safe}.json"


def _ui_key(prefix: str, rid: str) -> str:
    """Vytvoř UI-safe klíč (bez speciálních znaků)."""
    safe = re.sub(r"[^0-9A-Za-z_]", "_", str(rid))
    return f"{prefix}_{safe}"


def _attachments_dir(report_id: str) -> Path:
    d = REPORTS_DIR / _fs_safe(report_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _list_reports_for(oec: Optional[str]) -> List[Dict[str, Any]]:
    out = []
    for p in sorted(REPORTS_DIR.glob("*.json")):
        data = _read_json(p)
        rid = data.get("meta", {}).get("id") or p.stem
        title = data.get("meta", {}).get("title") or rid
        owner_oec = data.get("meta", {}).get("oec")
        created = data.get("meta", {}).get("created") or ""
        out.append(
            {"id": rid, "title": title, "oec": owner_oec, "created": created, "path": str(p)}
        )
    if oec:
        out = [r for r in out if r.get("oec") == oec]
    out.sort(key=lambda r: r.get("created", ""), reverse=True)
    return out


def _ensure_report_skeleton(report_id: str, oec: str) -> Dict[str, Any]:
    data = {
        "meta": {
            "id": report_id,
            "oec": oec,
            "created": _now().isoformat(timespec="seconds"),
            "title": report_id,
            "version": 3,
        },
        "event": {
            "datum_vzniku": _safe_date(None).isoformat(),
            "cas_vzniku": _safe_time(None).strftime("%H:%M:%S"),
            "datum_zpozorovani": _safe_date(None).isoformat(),
            "cas_zpozorovani": _safe_time(None).strftime("%H:%M:%S"),
            "datum_ohlaseni": _safe_date(None).isoformat(),
            "cas_ohlaseni": _safe_time(None).strftime("%H:%M:%S"),
            "adresa": {"kraj": "", "obec": "", "ulice": "", "cp": "", "co": "", "parcelni": "", "psc": ""},
            "gps": {"lat": None, "lon": None, "pozn": ""},
        },
        "conditions": {"weather": "", "temperature_c": 0, "visibility": ""},
        "participants": {"owners": [], "users": []},
        "witnesses": "",
        "sketch": "",
        "attachments": [],
        "notes": "",
    }
    return data


def _force_wide_layout_css():
    """Zruší implicitní max-width kontejneru Streamlitu, aby canvas a toolbar nebyly 'useknuté' vpravo."""
    st.markdown(
        """
        <style>
        /* hlavní blok na plnou šířku */
        .stAppViewContainer .main .block-container{
            max-width: 100% !important;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        /* komponenta s iframe = taky roztáhnout */
        .element-container:has(> iframe){
            width: 100% !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============ Pomocné vstupy ============
def _addr_inputs(base_key: str, data: Dict[str, str]) -> Dict[str, str]:
    c1, c2 = st.columns(2)
    with c1:
        obec = st.text_input("Obec", value=(data or {}).get("obec", ""), key=f"{base_key}_obec")
        ulice = st.text_input("Ulice", value=(data or {}).get("ulice", ""), key=f"{base_key}_ulice")
    with c2:
        cp_co = st.text_input("Číslo popisné/orientační", value=(data or {}).get("cp_co", ""), key=f"{base_key}_cpco")
        psc = st.text_input("PSČ", value=(data or {}).get("psc", ""), key=f"{base_key}_psc")
    return {"obec": obec, "ulice": ulice, "cp_co": cp_co, "psc": psc}


def _render_party_list(kind_label: str, key_prefix: str, items: List[Dict], report_id: str) -> List[Dict]:
    st.markdown(f"### {kind_label}")
    if items is None:
        items = []

    if st.button(
        f"➕ Přidat {kind_label[:-1].lower()}",
        key=f"add_{key_prefix}_{report_id}",
        use_container_width=True,
    ):
        items.append({"typ": "Fyzická osoba"})

    if not items:
        st.info(f"Žádný {kind_label[:-1].lower()} zatím není přidán.")
        return items

    for i, item in enumerate(list(items)):
        with st.expander(f"{kind_label[:-1]} #{i+1}", expanded=True):
            typ = st.selectbox(
                "Typ",
                options=["Fyzická osoba", "Právnická osoba", "OSVČ"],
                index=["Fyzická osoba", "Právnická osoba", "OSVČ"].index(item.get("typ", "Fyzická osoba")),
                key=f"{key_prefix}_{i}_typ_{report_id}",
            )

            if typ == "Fyzická osoba":
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    jmeno = st.text_input("Jméno", value=item.get("jmeno", ""), key=f"{key_prefix}_{i}_fo_jmeno_{report_id}")
                with c2:
                    prijmeni = st.text_input("Příjmení", value=item.get("prijmeni", ""), key=f"{key_prefix}_{i}_fo_prijmeni_{report_id}")
                with c3:
                    narozeni = st.date_input("Datum narození", value=_safe_date(item.get("narozeni")), key=f"{key_prefix}_{i}_fo_narozeni_{report_id}")
                addr = _addr_inputs(f"{key_prefix}_{i}_fo_addr_{report_id}", item.get("bydliste", {}))
                op = st.text_input("Číslo OP", value=item.get("op", ""), key=f"{key_prefix}_{i}_fo_op_{report_id}")
                upd = {"typ": typ, "jmeno": jmeno, "prijmeni": prijmeni, "narozeni": narozeni, "bydliste": addr, "op": op}

            elif typ == "Právnická osoba":
                obchodni_nazev = st.text_input("Obchodní název", value=item.get("obchodni_nazev", ""), key=f"{key_prefix}_{i}_po_nazev_{report_id}")
                ico = st.text_input("IČO", value=item.get("ico", ""), key=f"{key_prefix}_{i}_po_ico_{report_id}")
                st.markdown("**Sídlo**")
                sidlo = _addr_inputs(f"{key_prefix}_{i}_po_sidlo_{report_id}", item.get("sidlo", {}))
                st.markdown("**Odpovědný zástupce**")
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    z_jmeno = st.text_input("Jméno", value=item.get("zastupce", {}).get("jmeno", ""), key=f"{key_prefix}_{i}_po_zjm_{report_id}")
                with c2:
                    z_prijmeni = st.text_input("Příjmení", value=item.get("zastupce", {}).get("prijmeni", ""), key=f"{key_prefix}_{i}_po_zpr_{report_id}")
                with c3:
                    z_narozeni = st.date_input("Datum narození", value=_safe_date(item.get("zastupce", {}).get("narozeni")), key=f"{key_prefix}_{i}_po_znar_{report_id}")
                z_addr = _addr_inputs(f"{key_prefix}_{i}_po_zaddr_{report_id}", item.get("zastupce", {}).get("bydliste", {}))
                z_op = st.text_input("Číslo OP", value=item.get("zastupce", {}).get("op", ""), key=f"{key_prefix}_{i}_po_zop_{report_id}")
                upd = {"typ": typ, "obchodni_nazev": obchodni_nazev, "ico": ico, "sidlo": sidlo,
                       "zastupce": {"jmeno": z_jmeno, "prijmeni": z_prijmeni, "narozeni": z_narozeni, "bydliste": z_addr, "op": z_op}}

            else:  # OSVČ
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    jmeno = st.text_input("Jméno", value=item.get("jmeno", ""), key=f"{key_prefix}_{i}_osvc_jmeno_{report_id}")
                with c2:
                    prijmeni = st.text_input("Příjmení", value=item.get("prijmeni", ""), key=f"{key_prefix}_{i}_osvc_prijmeni_{report_id}")
                with c3:
                    narozeni = st.date_input("Datum narození", value=_safe_date(item.get("narozeni")), key=f"{key_prefix}_{i}_osvc_narozeni_{report_id}")
                ico = st.text_input("IČ", value=item.get("ico", ""), key=f"{key_prefix}_{i}_osvc_ico_{report_id}")
                addr = _addr_inputs(f"{key_prefix}_{i}_osvc_addr_{report_id}", item.get("bydliste", {}))
                op = st.text_input("Číslo OP", value=item.get("op", ""), key=f"{key_prefix}_{i}_osvc_op_{report_id}")
                upd = {"typ": typ, "jmeno": jmeno, "prijmeni": prijmeni, "narozeni": narozeni, "ico": ico, "bydliste": addr, "op": op}

            cL, cR = st.columns([1, 1])
            with cL:
                if st.button("🗑️ Smazat", key=f"del_{key_prefix}_{i}_{report_id}", use_container_width=True):
                    items.pop(i)
                    st.rerun()
            with cR:
                st.caption("")

            items[i] = upd

    return items


def render_sketch_window(rid: str):
    st.warning("Tento režim už není nutný. Použij plátno v listu Náčrtek (má i režim celé obrazovky).")


# ============ Hlavní render ============
def render_report():
    _force_wide_layout_css()
    st.markdown("## 📝 Report")

    oec = _current_oec()
    if not oec:
        q = _get_query_params()
        oec_q = q.get("oec")
        if isinstance(oec_q, list):
            oec_q = oec_q[0]
        if oec_q:
            st.session_state["oec"] = str(oec_q)
            oec = str(oec_q)
    if not oec:
        st.error("Chybí OEČ v relaci. Vrať se prosím o krok zpět a přihlaš se.")
        st.stop()

    q_all = _get_query_params()
    if q_all.get("oec") != oec:
        q_all["oec"] = oec
        _set_query_params(q_all)

    # ===== Sidebar =====
    with st.sidebar:
        st.markdown("### 📄 Reporty")
        if st.button("➕ Založit nový report", use_container_width=True, key="sb_btn_new_report"):
            rid = _gen_report_id(oec)
            data = _ensure_report_skeleton(rid, oec)
            _write_json(_report_path(rid), data)
            st.session_state.current_report_id = rid
            st.session_state[f"report_data_{rid}"] = data
            st.rerun()

        my_reports_all = _list_reports_for(oec)
        recent = my_reports_all[:5]

        if recent:
            st.caption("Posledních 5")
            for r in recent:
                c1, c2, c3 = st.columns([4.5, 1, 1])
                with c1:
                    if st.button(f"📄 {r['title']}", key=f"sb_open_{r['id']}", use_container_width=True):
                        st.session_state.current_report_id = r["id"]
                        p_open = _report_path(r["id"])
                        st.session_state[f"report_data_{r['id']}"] = _read_json(p_open)
                        st.rerun()
                with c2:
                    if st.button("✏️", key=f"sb_rename_{r['id']}", help="Přejmenovat", use_container_width=True):
                        st.session_state["rename_target"] = r["id"]
                        st.session_state["rename_value"] = r["title"]
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"sb_del_{r['id']}", help="Smazat report", use_container_width=True):
                        st.session_state["confirm_del"] = r["id"]
                        st.rerun()

                if st.session_state.get("rename_target") == r["id"]:
                    newname = st.text_input("Nový název", value=st.session_state.get("rename_value", r["title"]), key=f"sb_rename_input_{r['id']}")
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        if st.button("Uložit název", key=f"sb_rename_save_{r['id']}", use_container_width=True):
                            pth = _report_path(r["id"])
                            d = _read_json(pth)
                            d.setdefault("meta", {})["title"] = (newname or r["id"]).strip()
                            _write_json(pth, d)
                            st.session_state.pop(f"report_data_{r['id']}", None)
                            st.session_state.pop("rename_target", None)
                            st.session_state.pop("rename_value", None)
                            st.rerun()
                    with rc2:
                        if st.button("Zrušit", key=f"sb_rename_cancel_{r['id']}", use_container_width=True):
                            st.session_state.pop("rename_target", None)
                            st.session_state.pop("rename_value", None)
                            st.rerun()

        conf = st.session_state.get("confirm_del")
        if conf:
            st.warning(f"Opravdu smazat report: {conf}?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Ano, smazat", key="sb_del_yes", use_container_width=True):
                    try:
                        _report_path(conf).unlink(missing_ok=True)
                        attach_dir = _attachments_dir(conf)
                        if attach_dir.exists() and attach_dir.is_dir():
                            for x in attach_dir.glob("*"):
                                try:
                                    x.unlink(missing_ok=True)
                                except Exception:
                                    pass
                            try:
                                attach_dir.rmdir()
                            except Exception:
                                pass
                        st.session_state.pop(f"report_data_{conf}", None)
                        if st.session_state.get("current_report_id") == conf:
                            st.session_state.current_report_id = None
                    except Exception:
                        pass
                    st.session_state.pop("confirm_del", None)
                    st.rerun()
            with cc2:
                if st.button("Ne, ponechat", key="sb_del_no", use_container_width=True):
                    st.session_state.pop("confirm_del", None)
                    st.rerun()

        st.markdown("---")
        st.caption("Všechny moje reporty")
        if my_reports_all:
            options = {f"{r['title']} ({r['id']})": r['id'] for r in my_reports_all}
            sel_label = st.selectbox("Vyber report", list(options.keys()), key="sb_select_any")
            sel_id = options.get(sel_label)
            if st.button("Otevřít", key="sb_open_selected", use_container_width=True):
                st.session_state.current_report_id = sel_id
                p_open2 = _report_path(sel_id)
                st.session_state[f"report_data_{sel_id}"] = _read_json(p_open2)
                st.rerun()
        else:
            st.info("Zatím nemáš žádný report.")

    # ===== Hlavní plátno =====
    rid = st.session_state.get("current_report_id")
    if not rid:
        st.info("Vyber existující report vlevo, nebo klikni **Založit nový report** v levém panelu.")
        st.stop()

    p = _report_path(rid)
    if not p.exists():
        st.error("Soubor reportu nenalezen. Vyber jiný nebo založ nový.")
        st.stop()

    session_key = f"report_data_{rid}"
    if session_key not in st.session_state:
        st.session_state[session_key] = _read_json(p)
    data = st.session_state[session_key]

    # Titulek + akce
    tcol1, tcol2, tcol3 = st.columns([3, 1, 1])
    with tcol1:
        use_custom = st.checkbox("Použít vlastní název", value=(data.get("meta", {}).get("title") != rid), key=f"use_custom_{rid}")
        if use_custom:
            new_title = st.text_input("Název reportu", value=data.get("meta", {}).get("title") or rid, key=f"title_{rid}")
            data.setdefault("meta", {})["title"] = (new_title.strip() or rid)
        else:
            st.text_input("Název reportu (ID)", value=rid, key=f"title_readonly_{rid}", disabled=True)
            if data.get("meta", {}).get("title") != rid:
                data["meta"]["title"] = rid
    with tcol2:
        if st.button("💾 Uložit průběh", key=f"save_{rid}", use_container_width=True):
            _write_json(p, data)
            st.success("Uloženo.")
    with tcol3:
        if st.button("💾✅ Uložit a zavřít", key=f"save_close_{rid}", use_container_width=True):
            _write_json(p, data)
            st.session_state.pop(session_key, None)
            st.session_state.current_report_id = None
            st.rerun()

    if st.button("🚪 Zavřít bez uložení", key=f"close_{rid}", use_container_width=True):
        st.session_state.pop(session_key, None)
        st.session_state.current_report_id = None
        st.rerun()

    st.markdown("---")

    # =================== LISTY ===================
    tab_event, tab_cond, tab_part, tab_witness, tab_sketch = st.tabs(["Událost", "Podmínky", "Účastníci", "Svědectví", "Náčrtek"])

    # ========== Událost ==========
    with tab_event:
        st.subheader("📆 Událost")
        ev = data.get("event") or {}
        step_min = dt.timedelta(minutes=1)

        c1, c2, c3 = st.columns(3)
        with c1:
            ev["datum_vzniku"] = st.date_input("Datum vzniku", value=_safe_date(ev.get("datum_vzniku")), key=f"ev_dv_{rid}").isoformat()
        with c2:
            ev["cas_vzniku"] = st.time_input("Čas vzniku", value=_safe_time(ev.get("cas_vzniku")), step=step_min, key=f"ev_cv_{rid}").strftime("%H:%M:%S")
        with c3:
            st.caption("")

        c4, c5, c6 = st.columns(3)
        with c4:
            ev["datum_zpozorovani"] = st.date_input("Datum zpozorování", value=_safe_date(ev.get("datum_zpozorovani")), key=f"ev_dz_{rid}").isoformat()
        with c5:
            ev["cas_zpozorovani"] = st.time_input("Čas zpozorování", value=_safe_time(ev.get("cas_zpozorovani")), step=step_min, key=f"ev_cz_{rid}").strftime("%H:%M:%S")
        with c6:
            st.caption("")

        c7, c8, c9 = st.columns(3)
        with c7:
            ev["datum_ohlaseni"] = st.date_input("Datum ohlášení na KOPIS", value=_safe_date(ev.get("datum_ohlaseni")), key=f"ev_do_{rid}").isoformat()
        with c8:
            ev["cas_ohlaseni"] = st.time_input("Čas ohlášení na KOPIS", value=_safe_time(ev.get("cas_ohlaseni")), step=step_min, key=f"ev_co_{rid}").strftime("%H:%M:%S")
        with c9:
            st.caption("")

        st.markdown("**Adresa**")
        addr = ev.get("adresa") or {}
        a1, a2, a3 = st.columns([1, 1, 1])
        with a1:
            addr["kraj"] = st.text_input("Kraj", value=addr.get("kraj", ""), key=f"addr_kraj_{rid}")
            addr["obec"] = st.text_input("Obec / Město", value=addr.get("obec", ""), key=f"addr_obec_{rid}")
        with a2:
            addr["ulice"] = st.text_input("Ulice", value=addr.get("ulice", ""), key=f"addr_ulice_{rid}")
            addr["cp"] = st.text_input("Číslo popisné", value=addr.get("cp", ""), key=f"addr_cp_{rid}")
        with a3:
            addr["co"] = st.text_input("Číslo orientační", value=addr.get("co", ""), key=f"addr_co_{rid}")
            addr["parcelni"] = st.text_input("Číslo parcelní", value=addr.get("parcelni", ""), key=f"addr_parc_{rid}")
            addr["psc"] = st.text_input("PSČ", value=addr.get("psc", ""), key=f"addr_psc_{rid}")
        ev["adresa"] = addr
        data["event"] = ev

    # ========== Podmínky ==========
    with tab_cond:
        st.subheader("🌦️ Podmínky prostředí")
        cond = data.get("conditions") or {}
        c9, c10, c11 = st.columns(3)
        with c9:
            cond["weather"] = st.text_input("Počasí", value=cond.get("weather", ""), key=f"cond_w_{rid}")
        with c10:
            prev_temp = cond.get("temperature_c", 0)
            try:
                prev_temp = float(prev_temp)
            except Exception:
                prev_temp = 0.0
            temperature_c = st.number_input("Teplota [°C]", value=float(round(prev_temp)), step=1.0, format="%.0f", key=f"cond_t_{rid}")
            cond["temperature_c"] = int(temperature_c)
        with c11:
            cond["visibility"] = st.text_input("Viditelnost", value=cond.get("visibility", ""), key=f"cond_vis_{rid}")
        data["conditions"] = cond

    # ========== Účastníci ==========
    with tab_part:
        st.subheader("👥 Účastníci")
        participants = data.get("participants") or {"owners": [], "users": []}
        owners = participants.get("owners", [])
        users = participants.get("users", [])

        owners = _render_party_list("Majitelé", "owners", owners, rid)
        st.markdown("---")
        users = _render_party_list("Uživatelé", "users", users, rid)

        participants["owners"] = owners
        participants["users"] = users
        data["participants"] = participants

    # ========== Svědectví ==========
    with tab_witness:
        st.subheader("🗣️ Svědectví")
        data["witnesses"] = st.text_area("Záznam svědectví / výpovědí", value=data.get("witnesses", ""), height=220, key=f"wit_{rid}")

    # ========== Náčrtek ==========
    with tab_sketch:
        st.subheader("📝 Náčrtek")
        data["sketch"] = st.text_area(
            "Poznámka k náčrtku (popis, orientace, měřítko apod.)",
            value=data.get("sketch", ""),
            height=120,
            key=f"sketch_note_{rid}",
        )

        # ---------------- HTML5 canvas — FIX: plná šířka, stabilní fullscreen, grid jako overlay ----------------
        st.markdown("#### 1) ✏️ Kreslení zde")

        import streamlit.components.v1 as components

        # Podklad a rastr
        st.markdown("**Podklad a rastr**")
        bg_file = st.file_uploader(
            "Podkladový obrázek (PNG/JPG) — volitelné",
            type=["png", "jpg", "jpeg"],
            key=_ui_key("sk_bg", rid),
        )
        bg_dataurl = ""
        if bg_file is not None:
            try:
                raw = bg_file.getvalue()
                mime = bg_file.type or "image/png"
                b64 = base64.b64encode(raw).decode("ascii")
                bg_dataurl = f"data:{mime};base64,{b64}"
            except Exception:
                bg_dataurl = ""
        grid_on = st.checkbox("Zapnout rastr", value=False, key=_ui_key("sk_grid_on", rid))
        grid_step = st.slider("Hustota rastru [px]", 20, 120, 40, key=_ui_key("sk_grid_step", rid))

        fname = f"sketch_{uuid.uuid4().hex}.png"

        html = """
        <style>
          .sk-root { width: 100%; }
          .sk-toolbar {
            width: 100%; display:flex; flex-wrap:wrap; gap:.75rem;
            align-items:center; justify-content:space-between; margin-bottom:10px;
          }
          .sk-toolbar button, .sk-toolbar label, .sk-toolbar input[type=color]{ font-size:1rem; }
          .sk-toolbar button{ padding:.65rem 1rem; border-radius:10px; border:1px solid #666; background:#f5f5f5; }
          .sk-toolbar input[type=range]{ width:220px; }
          .sk-toolbar input[type=color]{ height:44px; width:44px; padding:0; border:none; }
          .sk-toolbar input[type=checkbox]{ transform:scale(1.4); margin-right:.35rem; }
          .sk-stage {
            position:relative; width:100%;
            border:1px solid #444; border-radius:8px; background:#fff; overflow:hidden;
            touch-action:none; /* pro pero/tyč */
          }
          canvas.sk-draw, canvas.sk-grid {
            position:absolute; inset:0; display:block; width:100%; height:100%;
          }
          canvas.sk-grid { pointer-events:none; } /* grid nebrání kreslení */
          @media (pointer:coarse){
            .sk-toolbar button{ padding:.8rem 1.2rem; }
          }
        </style>

        <div id="skRoot" class="sk-root">
          <div class="sk-toolbar">
            <div style="display:flex;gap:.75rem;align-items:center;flex-wrap:wrap;">
              <label> Tloušťka
                <input id='skThickness' type='range' min='1' max='40' value='4'>
              </label>
              <label style="display:flex;align-items:center;gap:.5rem;">
                <input id='skEraser' type='checkbox'> Guma
              </label>
              <label style="display:flex;align-items:center;gap:.5rem;">
                Barva <input id='skColor' type='color' value='#000000'>
              </label>
            </div>
            <div style="display:flex;gap:.75rem;flex-wrap:wrap;align-items:center;">
              <button id='skUndo'>↶ Zpět</button>
              <button id='skRedo'>↷ Znovu</button>
              <button id='skClear'>🧹 Vyčistit</button>
              <button id='skDownload'>💾 Uložit PNG</button>
              <button id='skFS'>🖥️ Celá obrazovka</button>
            </div>
          </div>

          <div id="skStage" class="sk-stage">
            <canvas id="skCanvas" class="sk-draw"></canvas>
            <canvas id="skGrid" class="sk-grid"></canvas>
          </div>
          <div id='skHint' style='color:#888;margin-top:6px'>Kresli myší/stylusem. Změna nástrojů nemá vliv na již nakreslené.</div>
        </div>

        <script>
        (function(){
          const RID = '[[RID]]';
          const storageKey = 'sketch_'+RID;
          const BG_DATA  = '[[BG_DATAURL]]';
          const SHOW_GRID = [[GRID_ON]];
          const GRID_STEP = [[GRID_STEP]];
          const DOWNLOAD_NAME = '[[FILENAME]]';

          const root = document.getElementById('skRoot');
          const stage = document.getElementById('skStage');
          const canvas = document.getElementById('skCanvas');    // kreslení
          const gridCv = document.getElementById('skGrid');      // overlay grid
          const ctx = canvas.getContext('2d');
          const gtx = gridCv.getContext('2d');

          const elT = document.getElementById('skThickness');
          const elC = document.getElementById('skColor');
          const elE = document.getElementById('skEraser');
          const elUndo = document.getElementById('skUndo');
          const elRedo = document.getElementById('skRedo');
          const elClear = document.getElementById('skClear');
          const elDL = document.getElementById('skDownload');
          const elFS = document.getElementById('skFS');

          let drawing=false, lastX=0, lastY=0;
          let undoStack=[], redoStack=[];
          let bgImg = null;

          function dpr(){ return window.devicePixelRatio || 1; }

          function isFullscreen(){
            return document.fullscreenElement && (document.fullscreenElement===root || root.contains(document.fullscreenElement));
          }

          function stageCssSize(){
            // v normálním režimu šířka = kontejner, ve fullscreen = celé okno
            const w = isFullscreen() ? window.innerWidth  : Math.max(300, stage.clientWidth || root.clientWidth || 800);
            const h = isFullscreen() ? (window.innerHeight - 12) : Math.max(480, Math.min(window.innerHeight - 220, 1600));
            return {w, h};
          }

          function setCanvasSize(){
            const {w, h} = stageCssSize();
            const r = dpr();

            // nastav CSS rozměry stage – ať se roztáhne na plnou šířku
            stage.style.width = w + 'px';
            stage.style.height = h + 'px';

            // nastav fyzické bitmapy obou canvasů s ohledem na HiDPI
            [canvas, gridCv].forEach(cv=>{
              cv.style.width = w + 'px';
              cv.style.height = h + 'px';
              cv.width  = Math.floor(w * r);
              cv.height = Math.floor(h * r);
            });

            // kreslit v souřadnicích CSS px
            ctx.setTransform(r,0,0,r,0,0);
            gtx.setTransform(r,0,0,r,0,0);

            // překreslit pozadí + obsah + grid
            repaintAll();
          }

          function clearCanvas(){
            const {w,h} = stageCssSize();
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0,0,w,h);
          }

          function drawBG(){
            const {w,h} = stageCssSize();
            if (bgImg){
              try { ctx.drawImage(bgImg, 0,0, w,h); } catch(e){}
            }
          }

          function drawGrid(){
            const {w,h} = stageCssSize();
            gtx.clearRect(0,0,w,h);
            if (!SHOW_GRID) return;
            gtx.save();
            gtx.strokeStyle = '#e0e0e0';
            gtx.lineWidth = 1;
            gtx.beginPath();
            for(let x=GRID_STEP; x<w; x+=GRID_STEP){ gtx.moveTo(x,0); gtx.lineTo(x,h); }
            for(let y=GRID_STEP; y<h; y+=GRID_STEP){ gtx.moveTo(0,y); gtx.lineTo(w,y); }
            gtx.stroke();
            gtx.restore();
          }

          function snapshot(){
            try { return canvas.toDataURL('image/png'); } catch(e){ return null; }
          }

          function restoreFrom(dataUrl, cb){
            if (!dataUrl) { if (cb) cb(); return; }
            const img = new Image();
            img.onload = ()=>{ 
              const {w,h} = stageCssSize();
              ctx.drawImage(img, 0,0, w,h);
              if (cb) cb();
            };
            img.src = dataUrl;
          }

          function saveLocal(){ try { localStorage.setItem(storageKey, canvas.toDataURL('image/png')); } catch(e){} }

          function styleFromUI(){
            const width = parseInt(elT.value||'4');
            const eraser = !!elE.checked;
            ctx.lineCap='round'; ctx.lineJoin='round'; ctx.lineWidth=width;
            ctx.strokeStyle = eraser ? '#FFFFFF' : (elC.value||'#000000');
          }

          function pos(e){
            const rect = canvas.getBoundingClientRect();
            const p = (e.pointerType) ? e : (e.touches && e.touches[0] ? e.touches[0] : e);
            const x = p.clientX - rect.left;
            const y = p.clientY - rect.top;
            return [x,y];
          }

          function start(e){ drawing=true; styleFromUI(); const p=pos(e); lastX=p[0]; lastY=p[1]; ctx.beginPath(); ctx.moveTo(lastX,lastY); e.preventDefault(); }
          function move(e){ if(!drawing) return; const p=pos(e); ctx.lineTo(p[0],p[1]); ctx.stroke(); lastX=p[0]; lastY=p[1]; e.preventDefault(); }
          function end(){ if(!drawing) return; drawing=false; ctx.closePath(); pushUndo(); saveLocal(); }

          function pushUndo(){ try { undoStack.push(canvas.toDataURL('image/png')); if (undoStack.length>50) undoStack.shift(); } catch(e){}; redoStack=[]; }

          function repaintAll(){
            const keep = snapshot();      // obsah před změnou velikosti
            clearCanvas();
            drawBG();
            restoreFrom(keep, ()=>{ drawGrid(); }); // grid jako overlay po obnově
          }

          // Události
          window.addEventListener('resize', ()=>setCanvasSize());
          document.addEventListener('fullscreenchange', ()=>setCanvasSize());

          canvas.addEventListener('pointerdown', (e)=>{ start(e); if (canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId); });
          canvas.addEventListener('pointermove', (e)=>{ move(e); });
          window.addEventListener('pointerup', ()=>end());
          window.addEventListener('pointercancel', ()=>end());
          canvas.addEventListener('pointerleave', ()=>end());

          elClear.onclick = ()=>{ pushUndo(); clearCanvas(); drawBG(); drawGrid(); saveLocal(); };
          elUndo.onclick = ()=>{ if(undoStack.length){ const d=undoStack.pop(); redoStack.push(canvas.toDataURL('image/png')); clearCanvas(); drawBG(); restoreFrom(d, ()=>{ drawGrid(); saveLocal(); }); } };
          elRedo.onclick = ()=>{ if(redoStack.length){ const d=redoStack.pop(); undoStack.push(canvas.toDataURL('image/png')); clearCanvas(); drawBG(); restoreFrom(d, ()=>{ drawGrid(); saveLocal(); }); } };
          elDL.onclick   = ()=>{ const a=document.createElement('a'); a.download=DOWNLOAD_NAME; a.href=canvas.toDataURL('image/png'); a.click(); };
          elFS.onclick   = ()=>{ if (root.requestFullscreen) root.requestFullscreen(); };

          // Načtení podkladu (není-li, jen vymažeme a nakreslíme grid)
          if (BG_DATA){
            bgImg = new Image();
            bgImg.onload = ()=>{ setCanvasSize(); };
            bgImg.src = BG_DATA;
          } else {
            setCanvasSize();
          }

          // případná data z localStorage
          (function(){
            const d = localStorage.getItem(storageKey);
            if (d){
              restoreFrom(d, ()=>{ drawGrid(); });
              try { undoStack.push(d); } catch(e){}
            }
          })();
        })();
        </script>
        """

        html = html.replace("[[RID]]", rid)
        html = html.replace("[[BG_DATAURL]]", bg_dataurl or "")
        html = html.replace("[[GRID_ON]]", "true" if grid_on else "false")
        html = html.replace("[[GRID_STEP]]", str(int(grid_step)))
        html = html.replace("[[FILENAME]]", fname)

        # vysoký iframe kvůli pohodlnému kreslení
        components.html(html, height=1400, scrolling=False)

        st.markdown("> 💡 Tip: **Celá obrazovka** zvětší plátno přes celé zařízení. Po návratu zůstane kresba zachována.")

        # 2) Nahrát soubor
        st.markdown("#### 2) 📤 Nahrát náčrtek (PNG/JPG/PDF)")
        up = st.file_uploader(
            "Nahraj soubor s náčrtkem",
            type=["png", "jpg", "jpeg", "pdf"],
            key=_ui_key("sketch_upload", rid),
        )
        if up is not None:
            save_dir = _attachments_dir(rid)
            ext = Path(up.name).suffix
            fname2 = f"sketch_{uuid.uuid4().hex}{ext}"
            dest2 = save_dir / fname2
            with dest2.open("wb") as f:
                f.write(up.getbuffer())
            atts = data.get("attachments") or []
            atts.append({
                "type": "sketch",
                "name": up.name,
                "file": str(dest2),
                "uploaded": _now().isoformat(timespec="seconds"),
            })
            data["attachments"] = atts
            _write_json(p, data)
            st.success("Soubor uložen k reportu.")

        # 3) Fotoaparát – až na klik
        st.markdown("#### 3) 📸 Vyfotit tabletem/zařízením")
        cam_flag_key = _ui_key("camera_open", rid)
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("📸 Otevřít fotoaparát", key=_ui_key("camera_btn", rid), use_container_width=True):
                st.session_state[cam_flag_key] = True
        with c2:
            if st.session_state.get(cam_flag_key):
                photo = st.camera_input("Pořídit fotografii náčrtku", key=_ui_key("camera", rid))
            else:
                photo = None

        if photo is not None:
            save_dir = _attachments_dir(rid)
            ext3 = ".jpg"
            if getattr(photo, 'type', '') == 'image/png':
                ext3 = ".png"
            fname3 = f"sketch_cam_{uuid.uuid4().hex}{ext3}"
            dest3 = save_dir / fname3
            with dest3.open("wb") as f:
                f.write(photo.getbuffer())
            atts = data.get("attachments") or []
            atts.append({
                "type": "sketch",
                "name": fname3,
                "file": str(dest3),
                "uploaded": _now().isoformat(timespec="seconds"),
            })
            data["attachments"] = atts
            _write_json(p, data)
            st.success("Fotografie uložena k reportu.")

        # Uložené náčrtky
        atts = [a for a in data.get("attachments", []) if a.get("type") == "sketch"]
        if atts:
            st.markdown("**Uložené náčrty**")
            for a in atts:
                st.write(f"• {a.get('name')} ({a.get('file')}) – {a.get('uploaded')}")
        else:
            st.info("Zatím nejsou uloženy žádné náčrtky.")

    st.markdown("---")

    # Poznámky
    st.subheader("🗒️ Poznámky (společné)")
    data["notes"] = st.text_area("Poznámky", value=data.get("notes", ""), key=f"notes_{rid}", height=140)

    st.markdown("---")

    # Akční tlačítka dole
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("💾 Uložit průběh (dole)", key=f"save2_{rid}", use_container_width=True):
            _write_json(p, data)
            st.success("Uloženo.")
    with b2:
        if st.button("💾✅ Uložit a zavřít (dole)", key=f"save_close2_{rid}", use_container_width=True):
            _write_json(p, data)
            st.session_state.pop(session_key, None)
            st.session_state.current_report_id = None
            st.rerun()
    with b3:
        if st.button("🚪 Zavřít bez uložení (dole)", key=f"close2_{rid}", use_container_width=True):
            st.session_state.pop(session_key, None)
            st.session_state.current_report_id = None
            st.rerun()
