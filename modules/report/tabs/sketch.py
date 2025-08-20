# modules/report/tabs/sketch.py
from __future__ import annotations
import base64
import streamlit as st
import streamlit.components.v1 as components


def render_tab(ctx):
    st.subheader("📝 Náčrtek")
    ctx.data["sketch"] = st.text_area(
        "Poznámka k náčrtku (popis, orientace, měřítko apod.)",
        value=ctx.data.get("sketch", ""), height=120, key=ctx.key("sketch_note")
    )

    st.markdown("#### 1) ✏️ Kreslení zde")
    bg_file = st.file_uploader(
        "Podkladový obrázek (PNG/JPG) — volitelné",
        type=["png", "jpg", "jpeg"], key=ctx.key("sk_bg")
    )
    bg_dataurl = ""
    if bg_file is not None:
        raw = bg_file.getvalue()
        mime = bg_file.type or "image/png"
        bg_dataurl = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

    grid_on = st.checkbox("Zapnout rastr", value=False, key=ctx.key("sk_grid_on"))
    grid_step = st.slider("Hustota rastru [px]", 20, 120, 40, key=ctx.key("sk_grid_step"))

    # === 3) FOTO – uložená poslední fotka pro tlačítko "Poklad" ===
    # Uchováváme poslední pořízenou fotku v ctx.data, aby šla vložit jako podklad později.
    last_photo_dataurl = ctx.data.get("last_photo_dataurl", "")

    html = _build_sketch_html(
        rid=ctx.rid,
        bg_dataurl=bg_dataurl,               # Podklad z uploaderu (1)
        grid_on=bool(grid_on),
        grid_step=int(grid_step),
        photo_dataurl=last_photo_dataurl     # Fotka z bodu 3) pro tlačítko Poklad
    )
    # vyšší iframe pro pohodlné kreslení
    components.html(html, height=1400, scrolling=False)

    st.markdown(
        "> 💡 Tip: **Celá obrazovka** zvětší plátno přes celé zařízení. Toolbar zůstane nahoře."
    )

    st.markdown("#### 2) 📤 Nahrát náčrtek (PNG/JPG/PDF)")
    up = st.file_uploader(
        "Nahraj soubor s náčrtkem",
        type=["png", "jpg", "jpeg", "pdf"],
        key=ctx.key("sketch_upload"),
    )
    if up is not None:
        save_dir = ctx.attachments_dir()
        dest = save_dir / f"sketch_{up.name}"
        with dest.open("wb") as f:
            f.write(up.getbuffer())
        atts = ctx.data.get("attachments") or []
        from datetime import datetime

        atts.append(
            {
                "type": "sketch",
                "name": up.name,
                "file": str(dest),
                "uploaded": datetime.now().isoformat(timespec="seconds"),
            }
        )
        ctx.data["attachments"] = atts
        ctx.save()
        st.success("Soubor uložen k reportu.")

    st.markdown("#### 3) 📸 Vyfotit tabletem/zařízením")
    cam_flag_key = ctx.key("camera_open")
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("📸 Otevřít fotoaparát", key=ctx.key("camera_btn"), use_container_width=True):
            st.session_state[cam_flag_key] = True
    with c2:
        photo = (
            st.camera_input(
                "Pořídit fotografii náčrtku", key=ctx.key("camera")
            )
            if st.session_state.get(cam_flag_key)
            else None
        )

    if photo is not None:
        # Uložit fotografii k reportu
        save_dir = ctx.attachments_dir()
        ext = ".jpg" if getattr(photo, "type", "") != "image/png" else ".png"
        dest = save_dir / f"sketch_cam_{ext}"
        with dest.open("wb") as f:
            f.write(photo.getbuffer())
        atts = ctx.data.get("attachments") or []
        from datetime import datetime

        atts.append(
            {
                "type": "sketch",
                "name": dest.name,
                "file": str(dest),
                "uploaded": datetime.now().isoformat(timespec="seconds"),
            }
        )
        ctx.data["attachments"] = atts

        # ZÁROVEŇ si uložíme base64 fotky, aby šla kdykoli vložit jako podklad (tlačítko Poklad)
        raw = photo.getbuffer()
        mime = photo.type or "image/jpeg"
        last_photo_dataurl = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
        ctx.data["last_photo_dataurl"] = last_photo_dataurl

        ctx.save()
        st.success("Fotografie uložena k reportu.")

    # Přehled uložených náčrtů
    atts = [a for a in ctx.data.get("attachments", []) if a.get("type") == "sketch"]
    if atts:
        st.markdown("**Uložené náčrty**")
        for a in atts:
            st.write(f"• {a.get('name')} ({a.get('file')}) – {a.get('uploaded')}")
    else:
        st.info("Zatím nejsou uloženy žádné náčrtky.")


def _build_sketch_html(
    rid: str, bg_dataurl: str, grid_on: bool, grid_step: int, photo_dataurl: str = ""
) -> str:
    """HTML/JS komponenta – plná šířka, overlay rastr, stabilní fullscreen s viditelným toolbarem.

    Novinky:
      • Tlačítko "Poklad" – vloží jako podklad poslední fotku z bodu 3).
    """
    fname = f"sketch_{rid}.png"
    html = r"""
    <style>
      :root { --sk-gap: .75rem; --sk-pad: 10px; }
      html, body { margin:0; padding:0; }
      .sk-root { width: 100%; }
      /* Toolbar na celou šířku + sticky v režimu fullscreen */
      .sk-toolbar {
        width: 100%;
        display: grid;
        grid-template-columns: 1fr auto;
        gap: var(--sk-gap);
        align-items: center;
        margin-bottom: var(--sk-pad);
        background: #fff;
      }
      .sk-toolbar button, .sk-toolbar label, .sk-toolbar input[type=color]{ font-size:1rem; }
      .sk-toolbar button{
        padding:.65rem 1rem; border-radius:10px; border:1px solid #666; background:#f5f5f5;
      }
      .sk-toolbar input[type=range]{ width:220px; }
      .sk-toolbar input[type=color]{ height:44px; width:44px; padding:0; border:none; }
      .sk-toolbar input[type=checkbox]{ transform:scale(1.4); margin-right:.35rem; }

      /* Plátno – stage vždy 100 % šířka rodiče */
      .sk-stage {
        position: relative; width: 100%;
        border:1px solid #444; border-radius:8px; background:#fff; overflow:hidden;
        touch-action:none;
      }
      canvas.sk-draw, canvas.sk-grid { position:absolute; inset:0; display:block; width:100%; height:100%; }
      canvas.sk-grid { pointer-events:none; }

      /* Širší rozhraní pro prsty */
      @media (pointer:coarse){
        .sk-toolbar button{ padding:.8rem 1.2rem; }
      }

      /* Vynucení širokého kontejneru Streamlitu */
      .stAppViewContainer .main .block-container{max-width:100%!important;padding:1rem;}
      .element-container:has(> iframe){width:100%!important;}

      /* Fullscreen: toolbar sticky nahoře, stage pod ním */
      .sk-root:fullscreen .sk-toolbar{
        position: sticky; top: 0; z-index: 10; box-shadow: 0 1px 6px rgba(0,0,0,.08);
      }
    </style>

    <div id="skRoot" class="sk-root">
      <div id="skToolbar" class="sk-toolbar">
        <div style="display:flex;gap:var(--sk-gap);align-items:center;flex-wrap:wrap;">
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
        <div style="display:flex;gap:var(--sk-gap);flex-wrap:wrap;align-items:center;">
          <button id='skUndo'>↶ Zpět</button>
          <button id='skRedo'>↷ Znovu</button>
          <button id='skClear'>🧹 Vyčistit</button>
          <button id='skDownload'>💾 Uložit PNG</button>
          <button id='skInsertPhoto'>🖼️ Poklad</button>
          <button id='skFS'>🖥️ Celá obrazovka</button>
        </div>
      </div>

      <div id="skStage" class="sk-stage">
        <canvas id="skCanvas" class="sk-draw"></canvas>
        <canvas id="skGrid" class="sk-grid"></canvas>
      </div>
      <div id='skHint' style='color:#888;margin-top:6px'>
        Kresli myší/stylusem. Změna nástrojů nemá vliv na již nakreslené.
      </div>
    </div>

    <script>
    (function(){
      const RID = '[[RID]]';
      const storageKey = 'sketch_'+RID;
      const BG_DATA  = '[[BG]]';
      const SHOW_GRID = [[GRID_ON]];
      const GRID_STEP = [[GRID_STEP]];
      const DOWNLOAD_NAME = '[[FILENAME]]';
      const PHOTO_DATA = '[[PHOTO]]';

      const root = document.getElementById('skRoot');
      const toolbar = document.getElementById('skToolbar');
      const stage = document.getElementById('skStage');
      const canvas = document.getElementById('skCanvas');
      const gridCv = document.getElementById('skGrid');
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
      const elPhoto = document.getElementById('skInsertPhoto');

      let drawing=false, lastX=0, lastY=0;
      let undoStack=[], redoStack=[];
      let bgImg = null;

      function dpr(){ return window.devicePixelRatio || 1; }
      function isFullscreen(){ return document.fullscreenElement && (document.fullscreenElement===root || root.contains(document.fullscreenElement)); }

      function containerWidth(){
        const r = root.getBoundingClientRect();
        return Math.max(300, r.width || stage.clientWidth || 800);
      }

      function targetSizes(){
        const w = isFullscreen() ? window.innerWidth : containerWidth();
        let h;
        if (isFullscreen()){
          const toolH = (toolbar?.offsetHeight || 0);
          h = Math.max(320, window.innerHeight - toolH - 8);
        } else {
          h = Math.max(480, Math.min(window.innerHeight - 220, 1600));
        }
        return {w, h};
      }

      function clearCanvas(){
        const {w,h} = targetSizes();
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0,0,w,h);
      }
      function drawBG(){
        const {w,h} = targetSizes();
        if (bgImg){ try { ctx.drawImage(bgImg, 0,0, w,h); } catch(e){} }
      }
      function drawGrid(){
        const {w,h} = targetSizes();
        gtx.clearRect(0,0,w,h);
        if (!SHOW_GRID) return;
        gtx.save(); gtx.strokeStyle = '#e0e0e0'; gtx.lineWidth = 1; gtx.beginPath();
        for(let x=GRID_STEP; x<w; x+=GRID_STEP){ gtx.moveTo(x,0); gtx.lineTo(x,h); }
        for(let y=GRID_STEP; y<h; y+=GRID_STEP){ gtx.moveTo(0,y); gtx.lineTo(w,y); }
        gtx.stroke(); gtx.restore();
      }

      function saveLocal(){ try { localStorage.setItem(storageKey, canvas.toDataURL('image/png')); } catch(e){} }
      function snapshot(){ try { return canvas.toDataURL('image/png'); } catch(e){ return null; } }
      function restoreFrom(dataUrl, cb){
        if (!dataUrl) { if (cb) cb(); return; }
        const img = new Image();
        img.onload = ()=>{ 
          const {w,h} = targetSizes();
          ctx.drawImage(img, 0,0, w,h);
          if (cb) cb();
        };
        img.src = dataUrl;
      }

      function setCanvasSize(preserve=true){
        const keep = preserve ? snapshot() : null;
        const {w, h} = targetSizes();
        const r = dpr();

        stage.style.width = w + 'px';
        stage.style.height = h + 'px';

        [canvas, gridCv].forEach(cv=>{
          cv.style.width = w + 'px';
          cv.style.height = h + 'px';
          cv.width  = Math.floor(w * r);
          cv.height = Math.floor(h * r);
        });

        ctx.setTransform(r,0,0,r,0,0);
        gtx.setTransform(r,0,0,r,0,0);

        clearCanvas();
        drawBG();
        restoreFrom(keep, ()=>{ drawGrid(); });
      }

      function styleFromUI(){
        const width = parseInt(elT.value||'4');
        const eraser = !!elE.checked;
        ctx.lineCap='round'; ctx.lineJoin='round'; ctx.lineWidth=width;
        ctx.strokeStyle = eraser ? '#FFFFFF' : (elC.value||'#000000');
      }
      function pos(e){
        const rect = canvas.getBoundingClientRect();
        const p = (e.pointerType) ? e : (e.touches && e.touches[0] ? e.touches[0] : e);
        return [p.clientX - rect.left, p.clientY - rect.top];
      }

      function start(e){ drawing=true; styleFromUI(); const p=pos(e); lastX=p[0]; lastY=p[1]; ctx.beginPath(); ctx.moveTo(lastX,lastY); e.preventDefault(); }
      function move(e){ if(!drawing) return; const p=pos(e); ctx.lineTo(p[0],p[1]); ctx.stroke(); lastX=p[0]; lastY=p[1]; e.preventDefault(); }
      function end(){ if(!drawing) return; drawing=false; ctx.closePath(); pushUndo(); saveLocal(); }

      function pushUndo(){ try { undoStack.push(canvas.toDataURL('image/png')); if (undoStack.length>50) undoStack.shift(); } catch(e){}; redoStack=[]; }

      // Ovládací prvky
      elClear.onclick = ()=>{ pushUndo(); clearCanvas(); drawBG(); drawGrid(); saveLocal(); };
      elUndo.onclick = ()=>{ if(undoStack.length){ const d=undoStack.pop(); redoStack.push(canvas.toDataURL('image/png')); clearCanvas(); drawBG(); restoreFrom(d, ()=>{ drawGrid(); saveLocal(); }); } };
      elRedo.onclick = ()=>{ if(redoStack.length){ const d=redoStack.pop(); undoStack.push(canvas.toDataURL('image/png')); clearCanvas(); drawBG(); restoreFrom(d, ()=>{ drawGrid(); saveLocal(); }); } };
      elDL.onclick   = ()=>{ const a=document.createElement('a'); a.download=DOWNLOAD_NAME; a.href=canvas.toDataURL('image/png'); a.click(); };
      elFS.onclick   = ()=>{ if (root.requestFullscreen) root.requestFullscreen(); };
      elPhoto.onclick = ()=>{
        if (!PHOTO_DATA){ alert('Žádná fotografie z bodu 3) zatím není k dispozici.'); return; }
        const img = new Image();
        img.onload = ()=>{ bgImg = img; setCanvasSize(false); saveLocal(); };
        img.src = PHOTO_DATA;
      };

      // Resize & fullscreen změny – vždy zachovat kresbu
      window.addEventListener('resize', ()=>setCanvasSize(true));
      document.addEventListener('fullscreenchange', ()=>setCanvasSize(true));

      // Jednotné pointer události (myš/pero/dotyk)
      canvas.addEventListener('pointerdown', (e)=>{ start(e); if (canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId); });
      canvas.addEventListener('pointermove', (e)=>{ move(e); });
      window.addEventListener('pointerup', ()=>end());
      window.addEventListener('pointercancel', ()=>end());
      canvas.addEventListener('pointerleave', ()=>end());

      // Načti podklad z uploaderu (1)
      if (BG_DATA){
        const img = new Image();
        img.onload = ()=>{ bgImg = img; setCanvasSize(false); };
        img.src = BG_DATA;
      } else {
        setCanvasSize(false);
      }

      // Obnov z localStorage
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
    html = html.replace("[[BG]]", bg_dataurl or "")
    html = html.replace("[[GRID_ON]]", "true" if grid_on else "false")
    html = html.replace("[[GRID_STEP]]", str(int(grid_step)))
    html = html.replace("[[FILENAME]]", fname)
    html = html.replace("[[PHOTO]]", photo_dataurl or "")
    return html
