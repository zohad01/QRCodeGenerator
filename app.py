import streamlit as st
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image
from io import BytesIO
import zipfile
import os

# ---------- QR generation ----------
def make_qr(data, fill_color="#000000", back_color="#FFFFFF", box_size=10):
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGB")


def add_logo_below(qr_img, logo_img, logo_scale=0.35, gap=24, margin=24):
    """Places a crisp logo underneath the QR code — never touches the scannable modules."""
    logo = logo_img.convert("RGBA")
    qr_w, qr_h = qr_img.size

    logo_w_target = int(qr_w * logo_scale)
    ratio = logo_w_target / logo.width
    logo = logo.resize((logo_w_target, int(logo.height * ratio)), Image.LANCZOS)

    canvas_w = qr_w
    canvas_h = qr_h + gap + logo.height + margin
    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    canvas.paste(qr_img, (0, 0))

    logo_x = (canvas_w - logo.width) // 2
    logo_y = qr_h + gap
    canvas.paste(logo, (logo_x, logo_y), mask=logo)

    return canvas


def embed_logo_center(qr_img, logo_img, white_backdrop=True):
    """Advanced: overlays the logo inside the QR itself (high error-correction keeps it scannable)."""
    img = qr_img.copy()
    logo = logo_img.convert("RGBA")
    qr_w, qr_h = img.size
    logo_size = int(qr_w * 0.22)
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
    pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)

    if white_backdrop:
        pad = 10
        white_bg = Image.new("RGB", (logo_size + pad * 2, logo_size + pad * 2), "white")
        img.paste(white_bg, (pos[0] - pad, pos[1] - pad))

    img.paste(logo, pos, mask=logo)
    return img


def img_to_bytes(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------- Main app ----------
st.set_page_config(page_title="CodeBettle QR Generator", page_icon="🔳")
st.title("🔳 CodeBettle QR Code Generator")

default_logo = None
if os.path.exists("logo.png"):
    default_logo = Image.open("logo.png")

tab1, tab2, tab3, tab4 = st.tabs(["🔗 Link / Text", "📶 WiFi", "👤 Contact Card", "📦 Batch"])

# --- Tab 1: Link/Text ---
with tab1:
    data = st.text_input("Text or URL", placeholder="https://drive.google.com/...")

    col1, col2, col3 = st.columns(3)
    with col1:
        fill_color = st.color_picker("QR Color", "#000000", key="t1_fill")
    with col2:
        back_color = st.color_picker("Background", "#FFFFFF", key="t1_back")
    with col3:
        box_size = st.slider("Size", 4, 20, 10, key="t1_size")

    logo_file = st.file_uploader("Logo (optional, defaults to logo.png if in repo)", type=["png", "jpg", "jpeg"])
    logo_img = Image.open(logo_file) if logo_file else default_logo

    placement = st.radio(
        "Logo placement",
        ["Below QR (recommended — never blocks scanning)", "Overlay in center (advanced)"],
        index=0,
    )
    white_backdrop = False
    if placement.startswith("Overlay"):
        white_backdrop = st.checkbox(
            "Add white backdrop behind logo",
            value=False,
            help="Turn on only if your logo file does NOT already have a transparent background.",
        )

    if st.button("Generate QR", type="primary", key="t1_btn"):
        if not data.strip():
            st.warning("Enter a link or text first.")
        else:
            qr_img = make_qr(data, fill_color, back_color, box_size)
            if logo_img is not None:
                if placement.startswith("Overlay"):
                    img = embed_logo_center(qr_img, logo_img, white_backdrop)
                else:
                    img = add_logo_below(qr_img, logo_img)
            else:
                img = qr_img

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
            qr_img = make_qr(wifi_str)
            img = add_logo_below(qr_img, default_logo) if default_logo is not None else qr_img
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
            qr_img = make_qr(vcard)
            img = add_logo_below(qr_img, default_logo) if default_logo is not None else qr_img
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
                    qr_img = make_qr(link)
                    img = add_logo_below(qr_img, default_logo) if default_logo is not None else qr_img
                    img_buf = img_to_bytes(img)
                    zf.writestr(f"qr_{i}.png", img_buf.read())
            zip_buf.seek(0)
            st.success(f"Generated {len(links)} QR codes.")
            st.download_button("Download ZIP", zip_buf, "qrcodes.zip", "application/zip")