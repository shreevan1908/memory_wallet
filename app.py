import streamlit as st
import requests
from datetime import datetime
import json
from streamlit_webrtc import webrtc_streamer

API_URL = "http://localhost:8000"

if "token" not in st.session_state:
    st.session_state["token"] = None

st.title("Memory Wallet : A Digital Capsule ")

def login_form():
    st.subheader("Login")
    email = st.text_input("Email", key = "login_email")
    password = st.text_input("Password", type="password", key = "login_password")
    if st.button("Login"):
        res = requests.post(f"{API_URL}/login", data={"username": email, "password": password})
        if res.status_code == 200:
            st.session_state["token"] = res.json()["access_token"]
            st.success("Logged in!")
            st.rerun()
        else:
            st.error("Login failed")

def signup_form():
    st.subheader("Sign Up")
    email = st.text_input("New Email", key = "signup_email")
    password = st.text_input("New Password", type="password", key = "signup_password")
    if st.button("Register"):
        res = requests.post(f"{API_URL}/signup", json={"email": email, "password": password})
        if res.status_code == 200:
            st.success("Signup success!")

def dashboard():
    if st.button("Logout"):
        st.session_state["token"] = None
        st.rerun()

    st.markdown("### Upload Memory Capsule")
    title = st.text_input("Title")
    text = st.text_area("Story")
    date = st.date_input("Date", value=datetime.today())
    tags = st.text_input("Tags (comma-separated)")
    files = st.file_uploader("Add Images/Videos/Audio", accept_multiple_files=True)
    time_capsule = st.text_input("Unlock on (YYYY-MM-DD HH:MM, optional)")
    if st.button("Upload Capsule"):
        m_files = []
        for f in files:
            m_files.append(("files", (f.name, f.read(), f.type)))
        data = {
            "title": title,
            "text": text,
            "date": str(date),
            "tags": tags,
            "time_capsule": time_capsule or None
        }
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        response = requests.post(f"{API_URL}/capsules", data=data, files=m_files, headers=headers)
        if response.status_code == 200:
            st.success("Uploaded successfully!")
            st.session_state['file_uploader'] = None
            st.rerun()
        else:
            st.error(f"Upload failed : {response.text}")

    st.markdown("### Capsules Timeline")
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    res = requests.get(f"{API_URL}/capsules", headers=headers)
    if res.status_code == 200:
        for capsule in res.json():
            st.markdown(f"**{capsule['title']}**")
            st.write(f"Date: {capsule['date']}, Tags: {capsule['tags']}")
            st.write(capsule['text'])
            #mlist = capsule['media']
            mlist = []
            try:
                mlist = json.loads(capsule['media']) if capsule['media'] else []
            except Exception as e:
                st.write("Error parsing media JSON:", e)

            st.write("Media list for debugging:", mlist)
            for m in (mlist or []):
                if m.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                    full_url = f"http://localhost:8000{m}" if not m.startswith("http") else m
                    st.image(full_url)
                elif m.lower().endswith(".mp3"):
                    full_url = f"http://localhost:8000{m}" if not m.startswith("http") else m
                    st.audio(full_url)
                elif m.lower().endswith(".mp4"):
                    full_url = f"http://localhost:8000{m}" if not m.startswith("http") else m
                    st.video(full_url)
            st.divider()

    else:
        st.error("Failed to fetch capsules")

    for capsule in res.json():
        st.markdown(f"**{capsule['title']}**")
        st.write(f"Date: {capsule['date']}, Tags: {capsule['tags']}")
        st.write(capsule['text'])

        # Show media...
        # (your existing image/audio/video code here)

        # Delete button
        if st.button(f"Delete Capsule {capsule['id']}", key=f"delete_{capsule['id']}"):
            del_res = requests.delete(
                f"{API_URL}/capsules/{capsule['id']}",
                headers=headers
            )
            if del_res.status_code == 200:
                st.success("Capsule deleted!")
                st.rerun()
            else:
                st.error(f"Delete failed: {del_res.text}")

        st.divider()


    st.markdown("### Speech Recognition")
    audio_file = st.file_uploader("Upload Audio", type=['mp3', 'wav'])
    if st.button("Convert to Text"):
        files = {"file": audio_file}
        response = requests.post(f"{API_URL}/audio-to-text", files=files, headers=headers)
        st.write(response.json().get("text", ""))

    st.markdown("### Text to Audio")
    note_text = st.text_area("Text to Narrate")
    if st.button("Convert to Audio"):
        response = requests.post(
            f"{API_URL}/text-to-audio", json={"text": note_text}, headers=headers
        )
        url = response.json().get("audio_url", None)
        if url:
            st.audio(url)


if not st.session_state["token"]:
    login_form()
    signup_form()
else:
    dashboard()


