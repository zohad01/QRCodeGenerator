import streamlit as st
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image
from io import BytesIO
import zipfile
import random
import string
import os

# ---------- Optional Supabase (for persistent short links) ----------
try:
    from supabase import create_client
except ImportError:
    create_client = None


@st.cache_resource
def get_supabase():
    """Returns a Supabase client if SUPABASE_URL / SUPABASE_KEY are configured, else None."""
    if create_client is None:
        return None
    url = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
    key = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))
    if url and key:
        return create_client(url, key)
    return None


def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def shorten_link(original_url):
    sb = get_supabase()
    if sb is None:
        return None  # shortener not configured
    code = generate_code()
    sb.table("links").insert({"code": code, "original_url": original_url}).execute()
    return code


def resolve_code(code):
    sb = get_supabase()
    if sb is None:
        return None
    res = sb.table("links").select("original_url").eq("code", code).execute()
    if res.data:
        return res.data[0]["original_url"]
    return None


# ---------- QR generation ----------
def make_qr(data, fill_color="#000000", back_color="#FFFFFF", box_size=10, logo_img=None, white_backdrop=True):
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_H,  # high correction so a logo doesn't break scanning
        box_size=box_size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGB")

    if logo_img is not None:
        logo = logo_img.convert("RGBA")
        qr_w, qr_h = img.size
        logo_size = int(qr_w * 0.25)
        logo = logo.resize((logo_size, logo_size))
        pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)

        if white_backdrop:
            pad = 10
            white_bg = Image.new("RGB", (logo_size + pad * 2, logo_size + pad * 2), "white")
            img.paste(white_bg, (pos[0] - pad, pos[1] - pad))

        # Paste using the logo's own alpha channel — transparent pixels let the QR show through,
        # opaque pixels show the logo. No backdrop box if white_backdrop is False.
        img.paste(logo, pos, mask=logo)

    return img


def img_to_bytes(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------- Redirect handling (for shortened links) ----------
params = st.query_params
if "s" in params:
    code = params["s"]
    target = resolve_code(code)
    if target:
        st.markdown(f'<meta http-equiv="refresh" content="0; url={target}">', unsafe_allow_html=True)
        st.write(f"Redirecting to {target} ...")
    else:
        st.error("This link doesn't exist or the shortener isn't configured.")
    st.stop()

# ---------- Main app ----------
st.set_page_config(page_title="CodeBettle QR Generator", page_icon="🔳")
st.title("🔳 CodeBettle QR Code Generator")

default_logo = None
if os.path.exists("logo.png"):
    default_logo = Image.open("logo.png")

tab1, tab2, tab3, tab4 = st.tabs(["🔗 Link / Text", "📶 WiFi", "👤 Contact Card", "📦 Batch"])

# --- Tab 1: Link/Text with optional shortening ---
with tab1:
    data = st.text_input("Text or URL", placeholder="https://drive.google.com/...")

    use_shortener = st.checkbox("Shorten this link with a CodeBettle short link", value=False)

    col1, col2, col3 = st.columns(3)
    with col1:
        fill_color = st.color_picker("QR Color", "#000000", key="t1_fill")
    with col2:
        back_color = st.color_picker("Background", "#FFFFFF", key="t1_back")
    with col3:
        box_size = st.slider("Size", 4, 20, 10, key="t1_size")

    logo_file = st.file_uploader("Logo to embed (optional, defaults to logo.png if in repo)", type=["png", "jpg", "jpeg"])
    logo_img = Image.open(logo_file) if logo_file else default_logo
    white_backdrop = st.checkbox(
        "Add white backdrop behind logo",
        value=False,
        help="Turn off if your logo PNG already has a transparent background — it'll sit directly on the QR with no white box.",
    )

    if st.button("Generate QR", type="primary", key="t1_btn"):
        if not data.strip():
            st.warning("Enter a link or text first.")
        else:
            final_data = data
            if use_shortener:
                code = shorten_link(data)
                if code is None:
                    st.error(
                        "Shortener isn't configured yet. Set up Supabase and add SUPABASE_URL / "
                        "SUPABASE_KEY to your app secrets (see README). Generating QR for the original link instead."
                    )
                else:
                    app_url = st.text_input(
                        "Your deployed app URL (e.g. https://codebettle-qr.streamlit.app)",
                        key="app_url_hint",
                    )
                    base = app_url.strip().rstrip("/") if app_url.strip() else "https://codebettle-qr.streamlit.app"
                    final_data = f"{base}/?s={code}"
                    st.success(f"Short link: {final_data}")

            img = make_qr(final_data, fill_color, back_color, box_size, logo_img, white_backdrop)
            buf = img_to_bytes(img)
            st.image(buf, width=300)
            st.download_button("Download PNG", buf, "qrcode.png", "image/png")

# --- Tab 2: WiFi ---
with tab2:
    ssid = st.text_input("Network name (SSID)")
    password = st.text_input("Password", type="password")
    enc = st.selectbox("Encryption", ["WPA", "WEP", "nopass"])
    if st.button("Generate WiFi QR", type="primary"):
        if not ssid.strip():
            st.warning("Enter the network name.")
        else:
            wifi_str = f"WIFI:T:{enc};S:{ssid};P:{password};;"
            img = make_qr(wifi_str, logo_img=default_logo)
            buf = img_to_bytes(img)
            st.image(buf, width=300)
            st.download_button("Download PNG", buf, "wifi_qr.png", "image/png")

# --- Tab 3: Contact card (vCard) ---
with tab3:
    name = st.text_input("Full name")
    phone = st.text_input("Phone")
    email = st.text_input("Email")
    org = st.text_input("Organization", value="CodeBettle")
    if st.button("Generate Contact QR", type="primary"):
        if not name.strip():
            st.warning("Enter a name.")
        else:
            vcard = f"BEGIN:VCARD\nVERSION:3.0\nN:{name}\nFN:{name}\nORG:{org}\nTEL:{phone}\nEMAIL:{email}\nEND:VCARD"
            img = make_qr(vcard, logo_img=default_logo)
            buf = img_to_bytes(img)
            st.image(buf, width=300)
            st.download_button("Download PNG", buf, "contact_qr.png", "image/png")

# --- Tab 4: Batch ---
with tab4:
    st.write("Paste one link per line to generate a ZIP of QR codes.")
    bulk_text = st.text_area("Links", height=150, placeholder="https://example.com/1\nhttps://example.com/2")
    if st.button("Generate ZIP", type="primary"):
        links = [l.strip() for l in bulk_text.splitlines() if l.strip()]
        if not links:
            st.warning("Enter at least one link.")
        else:
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for i, link in enumerate(links, start=1):
                    img = make_qr(link, logo_img=default_logo)
                    img_buf = img_to_bytes(img)
                    zf.writestr(f"qr_{i}.png", img_buf.read())
            zip_buf.seek(0)
            st.success(f"Generated {len(links)} QR codes.")
            st.download_button("Download ZIP", zip_buf, "qrcodes.zip", "application/zip")