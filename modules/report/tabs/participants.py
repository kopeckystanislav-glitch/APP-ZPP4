
from __future__ import annotations
import streamlit as st
from typing import List, Dict

def _addr_inputs(ctx, base_key: str, data: Dict[str, str]) -> Dict[str, str]:
    c1, c2 = st.columns(2)
    with c1:
        obec  = st.text_input("Obec",  value=(data or {}).get("obec",""),  key=f"{base_key}_obec_{ctx.rid}")
        ulice = st.text_input("Ulice", value=(data or {}).get("ulice",""), key=f"{base_key}_ulice_{ctx.rid}")
    with c2:
        cp_co = st.text_input("Číslo popisné/orientační", value=(data or {}).get("cp_co",""), key=f"{base_key}_cpco_{ctx.rid}")
        psc   = st.text_input("PSČ", value=(data or {}).get("psc",""), key=f"{base_key}_psc_{ctx.rid}")
    return {"obec": obec, "ulice": ulice, "cp_co": cp_co, "psc": psc}

def _render_party_list(ctx, kind_label: str, key_prefix: str, items: List[Dict]) -> List[Dict]:
    st.markdown(f"### {kind_label}")
    if items is None:
        items = []
    if st.button(f"➕ Přidat {kind_label[:-1].lower()}", key=f"add_{key_prefix}_{ctx.rid}", use_container_width=True):
        items.append({"typ": "Fyzická osoba"})
    if not items:
        st.info(f"Žádný {kind_label[:-1].lower()} zatím není přidán.")
        return items

    for i, item in enumerate(list(items)):
        with st.expander(f"{kind_label[:-1]} #{i+1}", expanded=True):
            typ = st.selectbox(
                "Typ", options=["Fyzická osoba","Právnická osoba","OSVČ"],
                index=["Fyzická osoba","Právnická osoba","OSVČ"].index(item.get("typ","Fyzická osoba")),
                key=f"{key_prefix}_{i}_typ_{ctx.rid}"
            )

            if typ == "Fyzická osoba":
                c1,c2,c3 = st.columns([1,1,1])
                with c1:
                    jmeno = st.text_input("Jméno", value=item.get("jmeno",""), key=f"{key_prefix}_{i}_fo_jmeno_{ctx.rid}")
                with c2:
                    prijmeni = st.text_input("Příjmení", value=item.get("prijmeni",""), key=f"{key_prefix}_{i}_fo_prijmeni_{ctx.rid}")
                with c3:
                    narozeni = st.date_input("Datum narození", value=item.get("narozeni"), key=f"{key_prefix}_{i}_fo_narozeni_{ctx.rid}")
                addr = _addr_inputs(ctx, f"{key_prefix}_{i}_fo_addr", item.get("bydliste", {}))
                op = st.text_input("Číslo OP", value=item.get("op",""), key=f"{key_prefix}_{i}_fo_op_{ctx.rid}")
                upd = {"typ": typ, "jmeno": jmeno, "prijmeni": prijmeni, "narozeni": narozeni, "bydliste": addr, "op": op}

            elif typ == "Právnická osoba":
                obchodni_nazev = st.text_input("Obchodní název", value=item.get("obchodni_nazev",""), key=f"{key_prefix}_{i}_po_nazev_{ctx.rid}")
                ico = st.text_input("IČO", value=item.get("ico",""), key=f"{key_prefix}_{i}_po_ico_{ctx.rid}")
                st.markdown("**Sídlo**")
                sidlo = _addr_inputs(ctx, f"{key_prefix}_{i}_po_sidlo", item.get("sidlo", {}))
                st.markdown("**Odpovědný zástupce**")
                c1,c2,c3 = st.columns([1,1,1])
                with c1:
                    z_jmeno = st.text_input("Jméno", value=item.get("zastupce", {}).get("jmeno",""), key=f"{key_prefix}_{i}_po_zjm_{ctx.rid}")
                with c2:
                    z_prijmeni = st.text_input("Příjmení", value=item.get("zastupce", {}).get("prijmeni",""), key=f"{key_prefix}_{i}_po_zpr_{ctx.rid}")
                with c3:
                    z_narozeni = st.date_input("Datum narození", value=item.get("zastupce", {}).get("narozeni"), key=f"{key_prefix}_{i}_po_znar_{ctx.rid}")
                z_addr = _addr_inputs(ctx, f"{key_prefix}_{i}_po_zaddr", item.get("zastupce", {}).get("bydliste", {}))
                z_op = st.text_input("Číslo OP", value=item.get("zastupce", {}).get("op",""), key=f"{key_prefix}_{i}_po_zop_{ctx.rid}")
                upd = {"typ": typ, "obchodni_nazev": obchodni_nazev, "ico": ico, "sidlo": sidlo,
                       "zastupce": {"jmeno": z_jmeno, "prijmeni": z_prijmeni, "narozeni": z_narozeni, "bydliste": z_addr, "op": z_op}}

            else:  # OSVČ
                c1,c2,c3 = st.columns([1,1,1])
                with c1:
                    jmeno = st.text_input("Jméno", value=item.get("jmeno",""), key=f"{key_prefix}_{i}_osvc_jmeno_{ctx.rid}")
                with c2:
                    prijmeni = st.text_input("Příjmení", value=item.get("prijmeni",""), key=f"{key_prefix}_{i}_osvc_prijmeni_{ctx.rid}")
                with c3:
                    narozeni = st.date_input("Datum narození", value=item.get("narozeni"), key=f"{key_prefix}_{i}_osvc_narozeni_{ctx.rid}")
                ico = st.text_input("IČ", value=item.get("ico",""), key=f"{key_prefix}_{i}_osvc_ico_{ctx.rid}")
                addr = _addr_inputs(ctx, f"{key_prefix}_{i}_osvc_addr", item.get("bydliste", {}))
                op = st.text_input("Číslo OP", value=item.get("op",""), key=f"{key_prefix}_{i}_osvc_op_{ctx.rid}")
                upd = {"typ": typ, "jmeno": jmeno, "prijmeni": prijmeni, "narozeni": narozeni, "ico": ico, "bydliste": addr, "op": op}

            cL, cR = st.columns([1,1])
            with cL:
                if st.button("🗑️ Smazat", key=f"del_{key_prefix}_{i}_{ctx.rid}", use_container_width=True):
                    items.pop(i); st.rerun()
            with cR: st.caption("")
            items[i] = upd
    return items

def render_tab(ctx):
    st.subheader("👥 Účastníci")
    participants = ctx.data.get("participants") or {"owners": [], "users": []}
    participants["owners"] = _render_party_list(ctx, "Majitelé", "owners", participants.get("owners", []))
    st.markdown("---")
    participants["users"] = _render_party_list(ctx, "Uživatelé", "users", participants.get("users", []))
    ctx.data["participants"] = participants
