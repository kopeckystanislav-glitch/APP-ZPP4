from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Optional

import streamlit as st
import bcrypt

USERS_DB_PATH = Path("data") / "users" / "users.json"
USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DEFAULT_ADMIN_OEC = "123456"
DEFAULT_ADMIN_PASS = "admin123"

def _load_db() -> Dict[str, Any]:
    try:
        data = json.loads(USERS_DB_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            data = {"meta": {"version": 1}, "users": data}
        if "users" not in data:
            data["users"] = []
        if "meta" not in data:
            data["meta"] = {"version": 1}
        return data
    except FileNotFoundError:
        return {"meta": {"version": 1}, "users": []}
    except Exception:
        return {"meta": {"version": 1}, "users": []}

def _save_db(db: Dict[str, Any]) -> None:
    USERS_DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _verify_password(pw: str, pw_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), pw_hash.encode("utf-8"))
    except Exception:
        return False

def _find_user(db: Dict[str, Any], oec: str) -> Optional[Dict[str, Any]]:
    for u in db.get("users", []):
        if u.get("oec") == oec:
            return u
    return None

def ensure_admin_password(default_oec: str = DEFAULT_ADMIN_OEC, default_password: str = DEFAULT_ADMIN_PASS) -> None:
    db = _load_db()
    users = db.get("users", [])
    admins = [u for u in users if u.get("role") == "admin"]
    changed = False

    if not users or not admins:
        admin = {
            "oec": default_oec,
            "role": "admin",
            "password_hash": _hash_password(default_password),
            "first_name": "Stanislav",
            "last_name": "Kopecký",
            "phone": "",
            "email": "stanislav@example.com",
            "region": "Plzeňský",
            "workplace": "HZS Rokycany",
            "active": True
        }
        if not _find_user(db, default_oec):
            users.append(admin)
            changed = True

    for u in users:
        if not u.get("password_hash"):
            u["password_hash"] = _hash_password("test123" if u.get("role") != "admin" else default_password)
            changed = True

    if changed:
        db["users"] = users
        _save_db(db)

def current_user() -> Optional[Dict[str, Any]]:
    return st.session_state.get("user")

def require_role(role: str) -> bool:
    u = current_user()
    if not u:
        st.error("Nepřihlášený uživatel.")
        return False
    if u.get("role") == "admin":
        return True
    return u.get("role") == role

def render_login(sidebar: bool = True) -> None:
    container = st.sidebar if sidebar else st
    db = _load_db()

    container.header("🔐 Přihlášení")
    oec = container.text_input("OEČ", max_chars=6)
    pwd = container.text_input("Heslo", type="password")
    if container.button("Přihlásit se", use_container_width=True):
        u = _find_user(db, oec)
        if not u or not u.get("active", True):
            container.error("Uživatel nenalezen nebo je deaktivován.")
        elif not _verify_password(pwd, u.get("password_hash", "")):
            container.error("Špatné heslo.")
        else:
            st.session_state["user"] = {
                "oec": u.get("oec"),
                "role": u.get("role", "user"),
                "first_name": u.get("first_name", ""),
                "last_name": u.get("last_name", ""),
                "phone": u.get("phone", ""),
                "email": u.get("email", ""),
                "region": u.get("region", ""),
                "workplace": u.get("workplace", ""),
                "active": u.get("active", True)
            }
            st.success(f"Přihlášen: {u.get('first_name','')} {u.get('last_name','')} ({u.get('oec')})")
            st.rerun()

    if st.session_state.get("user"):
        u = st.session_state["user"]
        container.success(f"Přihlášen {u.get('first_name','')} {u.get('last_name','')} – OEČ {u['oec']}")
        if container.button("Odhlásit se", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()

def render_admin_panel() -> None:
    if not require_role("admin"):
        return

    st.header("🛠️ Admin panel – uživatelé")
    db = _load_db()

    from collections import Counter
    counts = Counter([x.get("oec") for x in db.get("users", []) if x.get("oec")])
    dups = [o for o, c in counts.items() if c > 1]
    if dups:
        st.warning("Zjištěny duplicitní OEČ: " + ", ".join(dups))
        if st.button("🧹 Sloučit duplicity OEČ (ponechat poslední záznam)", key="dedup_users"):
            new_users = {}
            for rec in db.get("users", []):
                o = rec.get("oec")
                if o:
                    new_users[o] = rec
            db["users"] = list(new_users.values())
            _save_db(db)
            st.success("Duplicity odstraněny.")
            st.rerun()

    st.subheader("Seznam")
    for idx, u in enumerate(db.get("users", [])):
        user_oec = u.get('oec', '')
        key_suffix = f"{idx}_{user_oec}"

        with st.expander(f"{user_oec} – {u.get('first_name','')} {u.get('last_name','')} ({u.get('role','user')})"):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write(f"Email: {u.get('email','')}")
                st.write(f"Telefon: {u.get('phone','')}")
            with c2:
                st.write(f"Kraj: {u.get('region','')}")
                st.write(f"Pracoviště: {u.get('workplace','')}")
            with c3:
                st.write(f"Aktivní: {'Ano' if u.get('active', True) else 'Ne'}")

            colA, colB, colC = st.columns(3)

            # Dynamický popisek tlačítka
            status_label = "Deaktivovat" if u.get("active", True) else "Aktivovat"
            if colA.button(f"{status_label} {user_oec}", key=f"toggle_{key_suffix}"):
                if user_oec != DEFAULT_ADMIN_OEC:
                    for rec in db["users"]:
                        if rec.get("oec") == user_oec:
                            rec["active"] = not rec.get("active", True)
                            if st.session_state.get("user", {}).get("oec") == user_oec:
                                st.session_state["user"]["active"] = rec["active"]
                            break
                    _save_db(db)
                    db = _load_db()
                    st.rerun()
                else:
                    st.warning("Základního admina nelze deaktivovat.")

            if colB.button(f"Resetovat heslo {user_oec}", key=f"reset_{key_suffix}"):
                for rec in db["users"]:
                    if rec.get("oec") == user_oec:
                        rec["password_hash"] = _hash_password("test123")
                        break
                _save_db(db)
                db = _load_db()
                st.success(f"Heslo uživatele {user_oec} bylo resetováno na 'test123'.")
                st.rerun()

            if colC.button(f"Smazat {user_oec}", key=f"del_{key_suffix}"):
                if user_oec != DEFAULT_ADMIN_OEC:
                    db["users"] = [rec for rec in db["users"] if rec.get("oec") != user_oec]
                    _save_db(db)
                    db = _load_db()
                    st.success(f"Uživatel {user_oec} smazán.")
                    st.rerun()
                else:
                    st.warning("Základního admina nelze smazat.")

    st.subheader("➕ Přidat / upravit uživatele")
    form_key = "user_form_main"
    with st.form(form_key):
        oec = st.text_input("OEČ (6 číslic)*", max_chars=6)
        role = st.selectbox("Role", ["user", "admin"], index=0)
        first = st.text_input("Jméno")
        last = st.text_input("Příjmení")
        phone = st.text_input("Telefon")
        email = st.text_input("E-mail")
        region = st.text_input("Kraj")
        workplace = st.text_input("Pracoviště")
        new_pwd = st.text_input("Heslo (volitelné)", type="password")
        submitted = st.form_submit_button("Uložit")

        if submitted:
            if not (oec.isdigit() and len(oec) == 6):
                st.error("OEČ musí mít 6 číslic.")
            else:
                user = _find_user(db, oec)
                if not user:
                    user = {"oec": oec}
                    db["users"].append(user)

                user.update({
                    "role": role,
                    "first_name": first,
                    "last_name": last,
                    "phone": phone,
                    "email": email,
                    "region": region,
                    "workplace": workplace,
                    "active": True
                })

                if new_pwd:
                    user["password_hash"] = _hash_password(new_pwd)
                elif not user.get("password_hash"):
                    user["password_hash"] = _hash_password("test123")

                _save_db(db)
                db = _load_db()
                st.success(f"Uživatel {oec} uložen.")
                st.rerun()

def render_account_panel() -> None:
    u = current_user()
    if not u:
        st.error("Nejsi přihlášen.")
        return

    st.header("👤 Můj účet")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.write(f"**OEČ:** {u.get('oec','')}")
        st.write(f"**Jméno:** {u.get('first_name','')} {u.get('last_name','')}")
    with c2:
        st.write(f"**E-mail:** {u.get('email','')}")
        st.write(f"**Telefon:** {u.get('phone','')}")
    with c3:
        st.write(f"**Kraj:** {u.get('region','')}")
        st.write(f"**Pracoviště:** {u.get('workplace','')}")

    st.subheader("Změna hesla")
    with st.form("change_pw"):
        old = st.text_input("Aktuální heslo", type="password")
        new1 = st.text_input("Nové heslo", type="password")
        new2 = st.text_input("Nové heslo znovu", type="password")
        if st.form_submit_button("Změnit heslo"):
            if not new1 or new1 != new2:
                st.error("Nová hesla se neshodují.")
            else:
                db = _load_db()
                rec = _find_user(db, u.get("oec"))
                if not rec:
                    st.error("Uživatel v databázi nenalezen.")
                elif not _verify_password(old, rec.get("password_hash","")):
                    st.error("Aktuální heslo nesouhlasí.")
                else:
                    rec["password_hash"] = _hash_password(new1)
                    _save_db(db)
                    st.success("Heslo změněno.")
                    st.rerun()
