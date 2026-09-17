import streamlit as st
import qrcode
from io import BytesIO

st.set_page_config(page_title="QR Code Generator", page_icon="🔳")

st.title("🔳 QR Code Generator")
st.write("Enter any text or URL below and generate a downloadable QR code.")

data = st.text_input("Text / URL", placeholder="https://example.com")

col1, col2 = st.columns(2)
with col1:
    fill_color = st.color_picker("QR Color", "#000000")
with col2:
    back_color = st.color_picker("Background Color", "#FFFFFF")

box_size = st.slider("QR Size (box size)", 4, 20, 10)

if st.button("Generate QR Code", type="primary"):
    if not data.strip():
        st.warning("Please enter some text or a URL first.")
    else:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=box_size,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fill_color, back_color=back_color)

        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        st.image(buf, caption="Your QR Code", width=300)

        st.download_button(
            label="Download QR Code",
            data=buf,
            file_name="qrcode.png",
            mime="image/png",
        )
