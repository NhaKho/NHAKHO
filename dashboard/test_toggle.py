import streamlit as st

st.set_page_config(layout="wide")

if "menu_open" not in st.session_state:
    st.session_state.menu_open = True

def _toggle():
    st.session_state.menu_open = not st.session_state.menu_open

st.button(
    "☰ Menu" if not st.session_state.menu_open else "✕ Đóng menu",
    on_click=_toggle,
)

st.write("Trạng thái hiện tại menu_open =", st.session_state.menu_open)

if st.session_state.menu_open:
    col1, col2 = st.columns([1, 3])
    with col1:
        st.info("Đây là menu bên trái")
else:
    col2 = st.container()

with col2:
    st.write("Đây là nội dung chính")