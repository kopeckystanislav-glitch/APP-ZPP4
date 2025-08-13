# modules/report.py
# >>> FILE_MARKERS_ENABLED
from __future__ import annotations
import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime, time as dtime, timedelta
from typing import Dict, Any, List, Optional

import streamlit as st
from streamlit.components.v1 import html
# <<< FILE_MARKERS_ENABLED

# ========= Cesty a init =========
REPORTS_BASE = Path("data") / "reports"
REPORTS_BASE.mkdir(parents=True, exist_ok=True)

# >>> HELPERS_START
# ========= Pomocné =========
def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_report_id(oec: str) -> str:
    """ID: YYYYMMDD-HHMMSS-OEC-rand4"""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    rnd = uuid.uuid4().hex[:4]
    return f"{ts}-{oec}-{rnd}"


def _report_dir(report_id: str) -> Path:
    d = REPORTS_BASE / report_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _report_json_path(report_id: str) -> Path:
    return _report_dir(report_id) / "report.json"


def _default_title(oec: str, created_iso: Optional[str] = None) -> str:
    """Výchozí název: datum + čas založení + OEČ (např. 11.08.2025 14:05 — OEČ 123456)."""
    try:
        dt = datetime.fromisoformat(created_iso) if created_iso else datetime.now()
    except Exception:
        dt = datetime.now()
    return f"{dt.strftime('%d.%m.%Y %H:%M')} — OEČ {oec}"


def _fmt_addr(loc: Dict[str, Any]) -> str:
    """Sestaví čitelnou adresu z detailních polí, pokud není 'address'."""
    if not isinstance(loc, dict):
        return ""
    if loc.get("address"):
        return loc.get("address", "")
    parts1 = []
    if loc.get("street"):
        num = " ".join(
            p for p in [
                str(loc.get("house_number") or "").strip(),
                ("/" + str(loc.get("orientation_number")).strip()) if loc.get("orientation_number") else ""
            ] if p
        )
        parts1.append(f"{loc['street']}{(' ' + num) if num else ''}")
    city = loc.get("city")
    if city:
        parts1.append(city)
    kraj = loc.get("region")
    if kraj:
        parts1.append(kraj)
    if loc.get("parcel_number"):
        parts1.append(f"parc. č. {loc['parcel_number']}")
    return ", ".join([p for p in parts1 if p])
# >>> HELPERS_END

# >>> STORAGE_START
# ========= Uložení / načtení =========
def save_report(data: Dict[str, Any]) -> None:
    """Uloží JSON do složky reportu. Zajistí vyplněné 'oec' a 'report_id'."""
    rid = data.get("report_id")
    if not rid:
        raise ValueError("report data missing 'report_id'")
    if not data.get("oec"):
        raise ValueError("report data missing 'oec'")
    p = _report_json_path(rid)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_report(report_id: str) -> Optional[Dict[str, Any]]:
    p = _report_json_path(report_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _collect_reports() -> List[Dict[str, Any]]:
    """Načte metadata všech reportů (bez filtru)."""
    out: List[Dict[str, Any]] = []
    if not REPORTS_BASE.exists():
        return out
    for d in REPORTS_BASE.iterdir():
        if d.is_dir():
            rj = d / "report.json"
            if rj.exists():
                try:
                    rec = json.loads(rj.read_text(encoding="utf-8"))
                    loc = ((rec.get("event", {}) or {}).get("location", {}) or {})
                    location_str = loc.get("address") or _fmt_addr(loc)
                    out.append({
                        "report_id": rec.get("report_id"),
                        "created_at": rec.get("created_at"),
                        "updated_at": rec.get("updated_at"),
                        "oec": rec.get("oec"),
                        "event_date": (rec.get("event", {}) or {}).get("date_occurrence") or (rec.get("event", {}) or {}).get("date"),
                        "location": location_str,
                        "object_type": (rec.get("event", {}) or {}).get("object_type", ""),
                        "title": (rec.get("event", {}) or {}).get("title", ""),
                    })
                except Exception:
                    pass
    out.sort(key=lambda x: (x.get("updated_at") or "", x.get("created_at") or ""), reverse=True)
    return out


def list_reports_for_oec(oec: str) -> List[Dict[str, Any]]:
    """Seznam metadat reportů pro dané OEČ."""
    all_items = _collect_reports()
    return [r for r in all_items if r.get("oec") == oec]


def _empty_report(oec: str, report_id: str) -> Dict[str, Any]:
    now = _now_iso()
    return {
        "schema_version": 2,
        "report_id": report_id,
        "created_at": now,
        "updated_at": now,
        "oec": oec,
        "event": {
            "title": _default_title(oec, now),

            # detailní časová pole
            "date_occurrence": datetime.now().strftime("%Y-%m-%d"),
            "time_occurrence": datetime.now().strftime("%H:%M"),
            "date_observed": datetime.now().strftime("%Y-%m-%d"),
            "time_observed": datetime.now().strftime("%H:%M"),
            "date_kopis": datetime.now().strftime("%Y-%m-%d"),
            "time_kopis": datetime.now().strftime("%H:%M"),

            # zpětná kompatibilita
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),

            "event_number": "",
            "object_type": "",
            "description": "",
            "location": {
                "region": "",
                "city": "",
                "street": "",
                "house_number": "",
                "orientation_number": "",
                "parcel_number": "",
                "address": "",
                "gps_lat": None,
                "gps_lon": None,
            },
        },
        "participants": {
            "investigators": [oec],
            "commander": "",
            "units": "",
            "assist": "",
        },
        "conditions": {
            "weather": "",
            "temperature_c": None,
            "visibility": "",
        },
        "findings": {
            "origin": "",
            "cause": "",
            "damage_estimate_czk": None,
        },
        "notes": "",
        "photos": [],
        "drawings": [],
    }
# >>> STORAGE_END

# >>> UI_HELPERS_START
# ========= UI pomocné =========
def _inject_section_css() -> None:
    """Jemné vizuální oddělení sekcí (karty)."""
    if st.session_state.get("_report_css_injected"):
        return
    st.markdown(
        """
        <style>
          .section-card {
            border: 1px solid #e5e7eb;
            background: #ffffff;
            border-radius: 12px;
            padding: 14px 14px 6px 14px;
            margin-bottom: 12px;
          }
          .section-title {
            font-weight: 700;
            margin: 0 0 8px 0;
            display: flex;
            gap: 8px;
            align-items: center;
          }
          .section-title .tag {
            font-size: 12px;
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            padding: 2px 8px;
            border-radius: 9999px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_report_css_injected"] = True


def _card(title: str, tag: Optional[str] = None, icon: str = "🧩"):
    st.markdown(
        f"""
        <div class="section-card">
          <div class="section-title">{icon} {title}{' <span class="tag">'+tag+'</span>' if tag else ''}</div>
        """,
        unsafe_allow_html=True,
    )


def _card_end():
    st.markdown("</div>", unsafe_allow_html=True)
# >>> UI_HELPERS_END

# >>> RENDER_REPORT_START
# ========= Hlavní UI =========
def render_report() -> None:
    """Editor reportů: záložky, vizuální karty, ukládání do JSON + mazání (sidebar i editor)."""
    if "oec" not in st.session_state or not st.session_state.get("oec"):
        st.error("Nejprve se přihlas do modulu Požáry a zadej své OEČ.")
        st.stop()

    _inject_section_css()
    oec = st.session_state["oec"]
    st.session_state.setdefault("current_report_id", None)

    st.markdown("### 📝 Report – evidence zjištění na požářišti")

    # >>> SIDEBAR_START
    # ---- Sidebar ----
    with st.sidebar:
        st.markdown("#### 📂 Moje reporty")
        debug_show_all = st.checkbox("Zobrazit všechny reporty (debug)", value=False, key="report_debug_all")
        all_reports = _collect_reports()
        my_reports = all_reports if debug_show_all else list_reports_for_oec(oec)
        rid_options = [r["report_id"] for r in my_reports]

        st.caption(f"Nalezeno: **{len(my_reports)}** | Úložiště: `{REPORTS_BASE.resolve()}`")

        chosen = None
        open_btn = False
        if rid_options:
            current_label = st.session_state.current_report_id or "—"
            st.caption(f"Aktuální: **{current_label}**")
            labels = [
                f"{(r.get('title') or _default_title(r.get('oec',''), r.get('created_at')))}"
                f"{(' — ' + r.get('location')) if r.get('location') else ''} | {r['report_id']}"
                for r in my_reports
            ]
            idx_map = {labels[i]: rid_options[i] for i in range(len(labels))}
            chosen_label = st.selectbox("Otevřít existující report", labels, index=0, key="report_sel_open")
            open_btn = st.button("Otevřít vybraný", use_container_width=True, key="report_btn_open")
            chosen = idx_map.get(chosen_label)

            st.markdown("##### Akce s vybraným")
            col_del1, col_del2 = st.columns([1, 1])
            del_confirm = col_del1.checkbox("Potvrdit smazání", key="report_sidebar_del_confirm")
            del_btn = col_del2.button("🗑️ Smazat vybraný", key="report_sidebar_del_btn", use_container_width=True, disabled=not del_confirm)
            if del_btn and chosen:
                try:
                    shutil.rmtree(_report_dir(chosen))
                    if st.session_state.current_report_id == chosen:
                        st.session_state.current_report_id = None
                    st.success(f"Report {chosen} smazán.")
                    st.session_state["_suppress_auto_open"] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Chyba při mazání: {e}")
        else:
            st.info("Zatím nemáš žádné uložené reporty.")

        st.markdown("---")
        new_btn_sidebar = st.button("➕ Nový report", use_container_width=True, key="report_btn_new_sidebar")
    # <<< SIDEBAR_END

    # >>> NEW_OPEN_ACTIONS_START
    # Akce: nový (sidebar)
    if new_btn_sidebar:
        new_id = _new_report_id(oec)
        data = _empty_report(oec, new_id)
        try:
            save_report(data)
        except Exception as e:
            st.error(f"Ukládání selhalo: {e}")
            st.stop()
        st.session_state["_open_on_next_run"] = new_id
        st.rerun()

    # Akce: otevřít
    if open_btn and chosen:
        st.session_state.current_report_id = chosen
        st.rerun()

    # One-shot: otevři report po založení
    if st.session_state.get("_open_on_next_run"):
        st.session_state.current_report_id = st.session_state.pop("_open_on_next_run")
        st.rerun()
    # <<< NEW_OPEN_ACTIONS_END

    # >>> CTA_NO_SELECTED_START
    # ---- Pokud není vybrán report, ukážeme CTA (bez auto-open) ----
    if not st.session_state.current_report_id:
        st.info("Vyber existující report v levém panelu nebo založ nový.")
        if st.button("➕ Založit nový report", key="report_btn_new_main", use_container_width=True):
            new_id = _new_report_id(oec)
            data = _empty_report(oec, new_id)
            try:
                save_report(data)
            except Exception as e:
                st.error(f"Ukládání selhalo: {e}")
                st.stop()
            st.session_state["_open_on_next_run"] = new_id
            st.rerun()
        # reset potlačení po jednom běhu
        if st.session_state.get("_suppress_auto_open"):
            st.session_state["_suppress_auto_open"] = False
        st.stop()
    # <<< CTA_NO_SELECTED_END

    # >>> EDITOR_PREP_START
    # ---- Editor vybraného reportu ----
    report_id = st.session_state.current_report_id
    data = load_report(report_id) or _empty_report(oec, report_id)

    # Migrace starších polí
    ev = data.setdefault("event", {})
    ev.setdefault("date_occurrence", ev.get("date") or datetime.now().strftime("%Y-%m-%d"))
    ev.setdefault("time_occurrence", ev.get("time") or datetime.now().strftime("%H:%M"))
    ev.setdefault("date_observed", ev.get("date_occurrence"))
    ev.setdefault("time_observed", ev.get("time_occurrence"))
    ev.setdefault("date_kopis", ev.get("date_occurrence"))
    ev.setdefault("time_kopis", ev.get("time_occurrence"))
    loc = ev.setdefault("location", {})
    for k in ["region", "city", "street", "house_number", "orientation_number", "parcel_number", "address"]:
        loc.setdefault(k, "")
    for k in ["gps_lat", "gps_lon"]:
        if k not in loc:
            loc[k] = None

    if not data.get("oec"):
        data["oec"] = oec
        try:
            save_report(data)
        except Exception as e:
            st.warning(f"Autoopravné uložení selhalo: {e}")

    st.markdown(f"**Report ID:** `{report_id}`")
    # <<< EDITOR_PREP_END

    # >>> TOPBAR_CLOSE_START
    if st.button("⬅️ Zavřít report", key=f"report_close_btn_top_{report_id}", use_container_width=True):
        st.session_state.current_report_id = None
        st.session_state["_suppress_auto_open"] = True
        st.rerun()
    # <<< TOPBAR_CLOSE_END

    # >>> GEO_FROM_URL_START
    # Geolokace z URL (HTTPS only)
    params = st.query_params
    geo_lat = params.get("geo_lat")
    geo_lon = params.get("geo_lon")
    if geo_lat and geo_lon:
        try:
            st.session_state[f"gps_lat_{report_id}"] = float(geo_lat)
            st.session_state[f"gps_lon_{report_id}"] = float(geo_lon)
            try:
                if "geo_lat" in params: del params["geo_lat"]
                if "geo_lon" in params: del params["geo_lon"]
                if "geo_ts" in params: del params["geo_ts"]
            except Exception:
                pass
        except (TypeError, ValueError):
            pass
    # <<< GEO_FROM_URL_END

    # >>> FORM_START
    # ====== FORM + TABS ======
    with st.form(f"report_form_{report_id}"):
        tab_event, tab_people, tab_cond, tab_find, tab_notes = st.tabs(
            ["Událost", "Účastníci", "Podmínky", "Zjištění", "Poznámky"]
        )

        # --- Událost ---
        with tab_event:
            # >>> EVENT_SECTION_START
            _card("Identifikace události", icon="📌", tag="Sekce 1")

            # 1) Datum/čas
            c_dt1, c_dt2, c_dt3 = st.columns(3)
            with c_dt1:
                try:
                    d_occ = datetime.strptime(ev["date_occurrence"], "%Y-%m-%d").date()
                except Exception:
                    d_occ = datetime.now().date()
                t_occ = ev.get("time_occurrence", "00:00")
                try:
                    hh, mm = map(int, t_occ.split(":")[:2])
                    t_occ_val = dtime(hour=hh, minute=mm)
                except Exception:
                    t_occ_val = dtime(hour=0, minute=0)
                date_occurrence = st.date_input("Datum vzniku", value=d_occ, key=f"date_occ_{report_id}")
                time_occurrence = st.time_input(
                    "Čas vzniku", value=t_occ_val, step=timedelta(minutes=1), key=f"time_occ_{report_id}"
                )

            with c_dt2:
                try:
                    d_obs = datetime.strptime(ev["date_observed"], "%Y-%m-%d").date()
                except Exception:
                    d_obs = datetime.now().date()
                t_obs = ev.get("time_observed", "00:00")
                try:
                    hh, mm = map(int, t_obs.split(":")[:2])
                    t_obs_val = dtime(hour=hh, minute=mm)
                except Exception:
                    t_obs_val = dtime(hour=0, minute=0)
                date_observed = st.date_input("Datum zpozorování", value=d_obs, key=f"date_obs_{report_id}")
                time_observed = st.time_input(
                    "Čas zpozorování", value=t_obs_val, step=timedelta(minutes=1), key=f"time_obs_{report_id}"
                )

            with c_dt3:
                try:
                    d_kp = datetime.strptime(ev["date_kopis"], "%Y-%m-%d").date()
                except Exception:
                    d_kp = datetime.now().date()
                t_kp = ev.get("time_kopis", "00:00")
                try:
                    hh, mm = map(int, t_kp.split(":")[:2])
                    t_kp_val = dtime(hour=hh, minute=mm)
                except Exception:
                    t_kp_val = dtime(hour=0, minute=0)
                date_kopis = st.date_input("Datum ohlášení na KOPIS", value=d_kp, key=f"date_kp_{report_id}")
                time_kopis = st.time_input(
                    "Čas ohlášení na KOPIS", value=t_kp_val, step=timedelta(minutes=1), key=f"time_kp_{report_id}"
                )

            # 2) Základní info
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                event_number = st.text_input("Číslo jednací / spisová značka", value=ev.get("event_number", ""))
            with c2:
                obj_opts = ["", "Rodinný dům", "Byt", "Průmyslový objekt", "Vozidlo", "Volné prostranství", "Jiné"]
                obj_val = ev.get("object_type", "")
                object_type = st.selectbox("Typ objektu", obj_opts, index=obj_opts.index(obj_val) if obj_val in obj_opts else 0)
            with c3:
                title = st.text_input("Název / Stručný popis události", value=ev.get("title", ""))

            # 3) Adresa – rozpad
            _card("Adresa", icon="📍")
            l1, l2, l3 = st.columns([1, 1, 1])
            with l1:
                region = st.text_input("Kraj", value=loc.get("region", ""))
                city = st.text_input("Město/Obec", value=loc.get("city", ""))
            with l2:
                street = st.text_input("Ulice", value=loc.get("street", ""))
                house_number = st.text_input("Číslo popisné", value=str(loc.get("house_number", "")))
            with l3:
                orientation_number = st.text_input("Číslo orientační", value=str(loc.get("orientation_number", "")))
                parcel_number = st.text_input("Číslo parcelní", value=str(loc.get("parcel_number", "")))
            _card_end()

            # 4) GPS + zaměření
            _card("GPS souřadnice", icon="🗺️")
            key_lat = f"gps_lat_{report_id}"
            key_lon = f"gps_lon_{report_id}"
            if key_lat not in st.session_state:
                st.session_state[key_lat] = float(loc.get("gps_lat") or 0.0)
            if key_lon not in st.session_state:
                st.session_state[key_lon] = float(loc.get("gps_lon") or 0.0)

            c4, c5, c6 = st.columns([1, 1, 1])
            with c4:
                gps_lat_val = st.number_input("GPS – šířka (lat)", value=st.session_state[key_lat], step=0.0001, format="%.6f", key=key_lat)
            with c5:
                gps_lon_val = st.number_input("GPS – délka (lon)", value=st.session_state[key_lon], step=0.0001, format="%.6f", key=key_lon)
            with c6:
                geo_submit = st.form_submit_button("📍 Zaměřit polohu (mobil)", use_container_width=True)
            _card_end()

            # 5) Popis
            st.text_area("Popis události", value=ev.get("description", ""), key=f"report_desc_{report_id}", height=120)
            _card_end()
            # <<< EVENT_SECTION_END

        # --- Účastníci ---
        with tab_people:
            # >>> PEOPLE_SECTION_START
            _card("Zúčastněné osoby a jednotky", icon="👥", tag="Sekce 2")
            c6, c7, c8 = st.columns(3)
            with c6:
                investigators_str = st.text_input("Vyšetřovatelé (OEČ, oddělené čárkou)", value=",".join(data["participants"].get("investigators", [])))
            with c7:
                commander = st.text_input("Velitel zásahu", value=data["participants"].get("commander", ""))
            with c8:
                units = st.text_input("Jednotky / složky", value=data["participants"].get("units", ""))
            assist = st.text_input("Asistující orgány (Policie ČR, znalci…)", value=data["participants"].get("assist", ""))
            _card_end()
            # <<< PEOPLE_SECTION_END

        # --- Podmínky ---
        with tab_cond:
            # >>> CONDITIONS_SECTION_START
            _card("Podmínky prostředí", icon="🌦️", tag="Sekce 3")
            c9, c10, c11 = st.columns(3)
            with c9:
                weather = st.text_input("Počasí", value=data["conditions"].get("weather", ""))
            with c10:
                temperature_c = st.number_input("Teplota [°C]", value=float(data["conditions"].get("temperature_c") or 0.0), step=0.5, format="%.1f")
            with c11:
                visibility = st.text_input("Viditelnost", value=data["conditions"].get("visibility", ""))
            _card_end()
            # <<< CONDITIONS_SECTION_END

        # --- Zjištění ---
        with tab_find:
            # >>> FINDINGS_SECTION_START
            _card("Technická zjištění", icon="🛠️", tag="Sekce 4")
            c12, c13, c14 = st.columns(3)
            with c12:
                origin = st.text_input("Místo vzniku", value=data["findings"].get("origin", ""))
            with c13:
                cause = st.text_input("Pravděpodobná příčina", value=data["findings"].get("cause", ""))
            with c14:
                damage_estimate_czk = st.number_input("Odhad škody [Kč]", value=float(data["findings"].get("damage_estimate_czk") or 0.0), step=1000.0, format="%.0f")
            _card_end()
            # <<< FINDINGS_SECTION_END

        # --- Poznámky ---
        with tab_notes:
            # >>> NOTES_SECTION_START
            _card("Volné poznámky", icon="📝", tag="Sekce 5")
            notes = st.text_area("Poznámky", value=data.get("notes", ""), height=160)
            _card_end()
            # <<< NOTES_SECTION_END

        # >>> GEOLOC_ACTION_START
        # === Akce bez uložení (geolokace) ===
        if 'geo_submit' in locals() and geo_submit:
            html(
                """
                <script>
                (function(){
                  if (!navigator.geolocation) {
                    alert("Geolokace není v tomto prohlížeči dostupná.");
                    return;
                  }
                  navigator.geolocation.getCurrentPosition(function(pos){
                      const lat = pos.coords.latitude.toFixed(6);
                      const lon = pos.coords.longitude.toFixed(6);
                      const url = new URL(window.location.href);
                      url.searchParams.set('geo_lat', lat);
                      url.searchParams.set('geo_lon', lon);
                      url.searchParams.set('geo_ts', Date.now().toString());
                      window.history.replaceState({}, '', url);
                      window.location.reload();
                  }, function(err){
                      alert("Nepodařilo se získat polohu: " + err.message);
                  }, {enableHighAccuracy:true, timeout:10000, maximumAge:0});
                })();
                </script>
                """,
                height=0,
            )
            st.stop()
        # <<< GEOLOC_ACTION_END

        # >>> SAVE_BUTTONS_START
        # --- Uložení ---
        col_save, col_close = st.columns([1, 1])
        save_draft = col_save.form_submit_button("💾 Uložit průběh", use_container_width=True)
        save_and_close = col_close.form_submit_button("✅ Uložit a zavřít", use_container_width=True)
        # <<< SAVE_BUTTONS_END

        # >>> SAVE_HANDLER_START
        if save_draft or save_and_close:
            data["updated_at"] = _now_iso()
            data["oec"] = oec

            # Událost – časová pole
            ev["date_occurrence"] = date_occurrence.strftime("%Y-%m-%d")
            ev["time_occurrence"] = time_occurrence.strftime("%H:%M")
            ev["date_observed"] = date_observed.strftime("%Y-%m-%d")
            ev["time_observed"] = time_observed.strftime("%H:%M")
            ev["date_kopis"] = date_kopis.strftime("%Y-%m-%d")
            ev["time_kopis"] = time_kopis.strftime("%H:%M")
            ev["date"] = ev["date_occurrence"]
            ev["time"] = ev["time_occurrence"]

            # Událost – ostatní
            ev["event_number"] = event_number
            ev["object_type"] = object_type
            ev["title"] = title or _default_title(oec, data.get("created_at"))

            # Adresa
            loc["region"] = region
            loc["city"] = city
            loc["street"] = street
            loc["house_number"] = house_number
            loc["orientation_number"] = orientation_number
            loc["parcel_number"] = parcel_number
            loc["address"] = _fmt_addr(loc)

            # GPS
            ev["location"]["gps_lat"] = float(st.session_state.get(f"gps_lat_{report_id}", 0.0)) or None
            ev["location"]["gps_lon"] = float(st.session_state.get(f"gps_lon_{report_id}", 0.0)) or None

            # Popis
            ev["description"] = st.session_state.get(f"report_desc_{report_id}", "")

            # Účastníci
            inv_list = [x.strip() for x in (investigators_str or "").split(",") if x.strip()]
            data["participants"]["investigators"] = inv_list or [oec]
            data["participants"]["commander"] = commander
            data["participants"]["units"] = units
            data["participants"]["assist"] = assist

            # Podmínky
            data["conditions"]["weather"] = weather
            data["conditions"]["temperature_c"] = float(temperature_c) if temperature_c is not None else None
            data["conditions"]["visibility"] = visibility

            # Zjištění
            data["findings"]["origin"] = origin
            data["findings"]["cause"] = cause
            data["findings"]["damage_estimate_czk"] = float(damage_estimate_czk) if damage_estimate_czk is not None else None

            try:
                save_report(data)
            except Exception as e:
                st.error(f"Uložení selhalo: {e}")
            else:
                st.success("Report uložen.")
                if save_and_close:
                    st.session_state.current_report_id = None
                    st.session_state["_suppress_auto_open"] = True
                st.rerun()
        # <<< SAVE_HANDLER_END
    # <<< FORM_END

    st.markdown("---")

    # >>> DELETE_SECTION_START
    # Bezpečné mazání reportu uvnitř editoru
    with st.expander("🗑️ Smazat tento report", expanded=False):
        col1, col2 = st.columns([1, 1])
        confirm = col1.checkbox("Rozumím, chci smazat", key=f"del_confirm_{report_id}")
        if col2.button("🗑️ Smazat report", key=f"del_btn_{report_id}", use_container_width=True, disabled=not confirm):
            try:
                shutil.rmtree(_report_dir(report_id))
                st.success("Report smazán.")
                st.session_state.current_report_id = None
                st.session_state["_suppress_auto_open"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Chyba při mazání: {e}")
    # <<< DELETE_SECTION_END

    # >>> BACK_BUTTON_START
    if st.button("⬅️ Zpět na výběr reportu", key=f"report_back_bottom_{report_id}", use_container_width=True):
        st.session_state.current_report_id = None
        st.session_state["_suppress_auto_open"] = True
        st.rerun()
    # <<< BACK_BUTTON_END
# >>> RENDER_REPORT_END
