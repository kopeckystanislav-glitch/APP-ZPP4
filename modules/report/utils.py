
from __future__ import annotations
import datetime as dt
import re

def safe_date(v) -> dt.date:
    if isinstance(v, dt.date): return v
    try: return dt.date.fromisoformat(str(v))
    except Exception: return dt.date.today()

def safe_time(v) -> dt.time:
    if isinstance(v, dt.time): return v
    try:
        parts = [int(x) for x in str(v).split(":")]
        h = parts[0] if len(parts)>0 else 0
        m = parts[1] if len(parts)>1 else 0
        s = parts[2] if len(parts)>2 else 0
        return dt.time(h,m,s)
    except Exception:
        return dt.time(0,0,0)

def fs_safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '-', str(name))

def ui_key(prefix: str, rid: str) -> str:
    return f"{prefix}_{re.sub(r'[^0-9A-Za-z_]', '_', str(rid))}"

def get_query_params(st):
    try: return dict(st.query_params)
    except Exception:
        try: return dict(st.experimental_get_query_params())
        except Exception: return {}

def set_query_params(st, params: dict):
    try: st.query_params.update(params)
    except Exception:
        try: st.experimental_set_query_params(**params)
        except Exception: pass
