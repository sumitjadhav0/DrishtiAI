"""app.py - Mitra UI.   Run:  streamlit run app.py
Video + HUD stream.py madhun (smooth). Streamlit fakt controls/settings sathi - blocking loop nahi, mhanun lag nahi."""
import streamlit as st
import streamlit.components.v1 as components

import config
from navmap import KINDS
from pipeline import Pipeline
from stream import StreamServer

st.set_page_config(page_title="DrishtiAI Assist", page_icon="👁️", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
#MainMenu, header[data-testid="stHeader"], footer {visibility:hidden;height:0}
.block-container{padding-top:.8rem;padding-bottom:2rem;max-width:1180px}
div[data-testid="stExpander"]{border:1px solid #232830;border-radius:14px;background:#11151a}
.stButton>button{border-radius:12px;font-weight:600}
</style>""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="DrishtiAI tayar hot ahe (pahilyanda models download/load hotat)...")
def get_pipeline():
    return Pipeline()


@st.cache_resource(show_spinner=False)
def get_server():
    return StreamServer(get_pipeline()).start()


p = get_pipeline()
srv = get_server()

# ------------------------------------------------------------------ header + controls
h1, h2, h3, h4 = st.columns([5, 1.3, 1.3, 3])
h1.markdown("### 👁️ DrishtiAI &nbsp;<span style='font-size:14px;opacity:.55'>Blind Assist</span>", unsafe_allow_html=True)
if h2.button("▶ Start", width="stretch", type="primary"):
    try:
        p.start()
    except Exception as e:
        st.error(f"Camera start zala nahi: {e}")
if h3.button("⏹ Stop", width="stretch"):
    p.stop()
h4.caption(f"Profile **{config.PROFILE}** · {len(p.robin.runners)} models · fullscreen: {srv.url()}")
if p.robin.failed:
    st.warning("Load na zalele models: " + ", ".join(n for n, _ in p.robin.failed))
if p.voice is None:
    st.error("Voice input is unavailable because SpeechRecognition/PyAudio are missing. See DEPLOYMENT.md and restart the app after installing dependencies.")

# ------------------------------------------------------------------ LIVE VIDEO + HUD
H = 620
components.html(f'<iframe src="http://localhost:{srv.port}/" allow="autoplay" '
                f'style="width:100%;height:{H - 8}px;border:0;border-radius:16px;background:#000"></iframe>', height=H)

LANGS = {"en": "English", "hi": "हिन्दी (Hindi)", "mr": "मराठी (Marathi)"}

with st.expander("⚙️  Audio, teaching places, me & commands", expanded=False):
    tab_audio, tab_teach, tab_me = st.tabs(["🔊 Audio & Listening", "🏠 Teach places", "🙂 Me & Commands"])

    # -------------------------------------------------------------- Audio & Listening
    with tab_audio:
        lang = st.selectbox("Mitra speaks in", list(LANGS), format_func=LANGS.get, index=list(LANGS).index(p.lang))
        if lang != p.lang:
            p.set_language(lang)
            p.store.set("lang", lang)
        if p.voice:
            mics = p.voice.list_mics()
            opts = [None] + [i for i, _ in mics]
            names = dict(mics)
            cur = p.voice.device_index if p.voice.device_index in opts else None
            pick = st.selectbox("🎤 Microphone", opts, index=opts.index(cur),
                                format_func=lambda i: "(system default)" if i is None else names.get(i, str(i)))
            if pick != p.voice.device_index:
                p.voice.set_device(pick)
            echo_guard = st.checkbox(
                "Ignore microphone audio while Mitra speaks",
                value=p.voice.echo_guard,
                help="Keep on with speakers to prevent feedback. Turn it off to interrupt with a command, preferably using a headset.",
                key="echo_guard",
            )
            if echo_guard != p.voice.echo_guard:
                p.voice.echo_guard = echo_guard
            if bool(p.store.d.get("echo_guard", True)) != echo_guard:
                p.store.set("echo_guard", echo_guard)
            st.caption(f"Mic: {p.voice.device_name} · state: {p.voice.state} · last heard: {p.voice.heard}")
            st.caption("Echo protection: " + ("ON - speaker mode (Mitra ignores the mic while speaking)"
                                              if p.voice.echo_guard else "OFF - commands may interrupt Mitra"))
            st.caption(f"Voice listener: {p.voice.status}")
        else:
            st.error("Voice commands unavailable. Install the dependencies from requirements.txt and restart the app.")
        vol = st.slider("🔈 Volume", 0, 100, int(p.speaker.volume * 100))
        if vol != int(p.speaker.volume * 100):
            p.speaker.set_volume(vol / 100)
            p.store.set("volume", vol / 100)
        spd = st.slider("⏩ Speech speed (%)", -50, 50, int(p.speaker.rate))
        if spd != int(p.speaker.rate):
            p.speaker.set_rate(spd)
            p.store.set("rate", spd)
        if st.button("🔊 Test speaker"):
            p.speaker.speak_now({"en": "Hello, this is Mitra. Can you hear me?",
                                 "hi": "नमस्ते, मैं मित्र हूँ. क्या आप मुझे सुन सकते हैं?",
                                 "mr": "नमस्कार, मी मित्र आहे. तुम्हाला माझा आवाज ऐकू येतो का?"}[p.lang])
        st.caption(f"Speaker: {p.speaker.status}")

    # -------------------------------------------------------------- Teach places
    with tab_teach:
        st.markdown("Caregiver ne ghar/college shikvaycha: **1)** ▶ Start  **2)** jagevar ubhe rahun *Save this spot*  "
                    "**3)** jagan madhle raste lihā. Voice ne pan: *start teaching → remember this place*.")
        nm = p.navmap
        site = st.text_input("Site (home / college / ...)", value=st.session_state.get("site", "home"))
        st.session_state["site"] = site
        pname = st.text_input("Place name (e.g. Bedroom, Hall, Main door)")
        kind = st.selectbox("Type", ["(auto)"] + KINDS)
        aliases = st.text_input("Other names, comma separated (also Marathi/Hindi, e.g. बाहेर, दरवाजा)")
        if st.button("📸 Save this spot (3 photos)"):
            if not pname.strip():
                st.warning("Adhi place cha nav lihā.")
            elif not p.running:
                st.warning("Adhi ▶ Start daba (camera chalu havi).")
            else:
                try:
                    nid, k = p.capture_waypoint(pname, site, None if kind == "(auto)" else kind,
                                                [a for a in aliases.split(",")])
                    st.success(f"Saved '{pname}' ({k} photos). Ek jaga sathi 5+ photos changle - parat parat save kara.")
                except RuntimeError as e:
                    st.error("Picture model (CLIP) available nahi." if str(e) == "no_clip" else "Camera frame nahi.")
        st.markdown("---")
        ids = list(nm.nodes)
        if ids:
            st.subheader("Paths (rasta)")
            a = st.selectbox("From", ids, format_func=lambda i: nm.nodes[i]["name"])
            b = st.selectbox("To", ids, format_func=lambda i: nm.nodes[i]["name"], index=min(1, len(ids) - 1))
            text = st.text_area("How to walk from 'From' to 'To' (your own words, step count, turns)")
            elang = st.selectbox("Language of this text", list(LANGS), format_func=LANGS.get, index=list(LANGS).index(p.lang))
            if st.button("💾 Save path"):
                if a == b or not text.strip():
                    st.warning("From ani To vegle pahijet, ani rasta lihāycha.")
                else:
                    nm.set_edge(a, b, text, elang)
                    st.success("Path saved.")
            st.subheader("Saved places")
            for i in ids:
                n = nm.nodes[i]
                st.write(f"• **{n['name']}** ({n['kind']}, {n['site']}) - {nm.count_photos(i)} photos")
            for e in nm.edges.values():
                st.write(f"→ {nm.nodes[e['from']]['name']} ➜ {nm.nodes[e['to']]['name']}: {e['text']}")
            dsel = st.selectbox("Delete a place", ids, format_func=lambda i: nm.nodes[i]["name"])
            if st.button("🗑 Delete"):
                nm.remove_node(dsel)
                st.success("Deleted.")
        else:
            st.info("Ajun kontihi jaga shikvli nahi.")

    # -------------------------------------------------------------- Me & Commands
    with tab_me:
        name = st.text_input("Your name", value=p.store.d.get("name", ""))
        if name != p.store.d.get("name", ""):
            p.store.set("name", name.strip())
        notes = p.store.d.get("notes", [])
        st.write("📝 Notes: " + ("; ".join(n["text"] for n in notes) if notes else "none"))
        cmd = st.text_input("Type a command (same as speaking)",
                            placeholder="e.g. where am I / take me outside / मला बाहेर जायचं आहे")
        if st.button("Send") and cmd.strip():
            st.write("Mitra:", " ".join(t for t, _ in p.dialog.handle(cmd, from_voice=False)) or "(done)")
        st.markdown("""
**Voice commands** (English / हिंदी / मराठी)
- *Where am I* / मैं कहाँ हूँ / मी कुठे आहे — *What is in front* / सामने क्या है / समोर काय आहे — around me, how many people, is it safe
- *Take me outside* / मुझे बाहर जाना है / मला बाहेर जायचं आहे → step-by-step; say *next*, *repeat*, *stop guiding*
- *I am in the hall* · *My name is …* · *Remember that …* · *What time is it* · *Stop talking / Start guiding* · *Hindi / Marathi / English* · *Help*
- Teaching: *Start teaching → Remember this place → (name) → (how to walk) → Done teaching*
""")
