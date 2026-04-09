"""
app.py
------
Streamlit WebRTC deployment for Guess-the-Song filter.
"""

import queue
import cv2
import av
import streamlit as st
import mediapipe as mp
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration

from spinner import SongSpinner

# Set page characteristics
st.set_page_config(page_title="Guess the Song", layout="centered", page_icon="🎵")

# Initialize shared resources in session state
if "spinner" not in st.session_state:
    st.session_state.spinner = SongSpinner("assets/name.csv", "assets/cover")

if "spin_queue" not in st.session_state:
    st.session_state.spin_queue = queue.Queue()

# Ensure we maintain a single, thread-safe (per user) MediaPipe FaceMesh instance
if "face_mesh" not in st.session_state:
    st.session_state.face_mesh = mp.solutions.face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

st.title("🎵 Guess the Song Filter")
st.write("Enable your webcam and click the button to spin!")

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🎰 Spin Wheel!", use_container_width=True):
        st.session_state.spin_queue.put(True)

# Free public STUN server for stream relaying through Streamlit Cloud limits
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
    # Context is automatically propagated by streamlit-webrtc >= 0.45.0
    spinner = st.session_state.spinner
    spin_queue = st.session_state.spin_queue
    face_mesh = st.session_state.face_mesh

    try:
        # Check if the UI has emitted a spin trigger signal
        # We drain the queue in case of fast multiple clicks
        while True:
            if spin_queue.get_nowait():
                spinner.trigger_spin()
    except queue.Empty:
        pass

    img = frame.to_ndarray(format="bgr24")
    img = cv2.flip(img, 1)  # selfie monitor mirror effect
    
    h, w = img.shape[:2]

    # Converting to RGB for MediaPipe processing
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False
    
    results = face_mesh.process(rgb)
    
    face_found = False
    if results.multi_face_landmarks:
        for face_lms in results.multi_face_landmarks:
            face_found = True
            lm = face_lms.landmark[10]
            fx = int(lm.x * w)
            fy = int(lm.y * h)

            img = spinner.render_overlay(img, fx, fy)
            break  # target exactly the first face processed

    if not face_found:
        # Default positioning if no face enters frame
        img = spinner.render_overlay(img, w // 2, h // 3)

    return av.VideoFrame.from_ndarray(img, format="bgr24")

webrtc_streamer(
    key="guess-the-song",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIGURATION,
    media_stream_constraints={"video": True, "audio": False},
    video_frame_callback=video_frame_callback,
    async_processing=True,
)

st.caption("Works best if your face is visibly lit. The AR card will stick above your forehead!")
