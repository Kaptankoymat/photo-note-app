import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageOps
import io
import json
import os
import numpy as np

# Page Configuration
st.set_page_config(
    page_title="Photo Note",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Custom CSS for Modern "Apple-like" Design
st.markdown("""
<style>
    /* Global Font & cleanliness */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Inputs */
    .stTextArea textarea {
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.01);
        padding: 12px;
        transition: all 0.2s ease;
    }
    .stTextArea textarea:focus {
        border-color: #007AFF;
        box-shadow: 0 4px 12px rgba(0,122,255,0.15);
    }
    
    .stTextInput input {
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        padding: 10px;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 12px;
        font-weight: 500;
        border: none;
        background-color: #007AFF;
        color: white;
        transition: transform 0.1s;
    }
    .stButton button:hover {
        background-color: #0062cc;
        transform: scale(1.02);
    }
    .stButton button:active {
        transform: scale(0.98);
    }
    
    /* Canvas & Toolbar */
    iframe[title="streamlit_drawable_canvas.st_canvas"] {
        background-color: white; 
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); /* Subtle shadow for depth */
    }
    
    /* Dark Mode Adjustments */
    @media (prefers-color-scheme: dark) {
        .stTextArea textarea {
            background-color: #2c2c2e;
            border-color: #3a3a3c;
            color: white;
        }
        .stTextInput input {
            background-color: #2c2c2e;
            border-color: #3a3a3c;
            color: white;
        }
    }
</style>
""", unsafe_allow_html=True)

# Application Layout
col1, col2 = st.columns([65, 35])

# Sidebar
with st.sidebar:
    st.title("Settings")
    uploaded_file = st.file_uploader("Upload New Image", type=["png", "jpg", "jpeg"])
    
    st.divider()
    with st.expander("Shortcuts & Help"):
        st.markdown("""
        **Tools:**
        - **Free Draw**: Sketch freely.
        - **Selection**: Draw boxes to link nodes.
        - **Edit**: Select objects to move/resize.
        
        **Shortcuts:**
        - **Delete**: Remove selected object.
        - **Undo**: Ctrl+Z (in canvas context).
        """)
    
    st.divider()
    if st.button("Reset Project"):
        # Clear Session State
        st.session_state.clear()
        st.rerun()

with col1:
    st.subheader("Workspace")
    
    # --- Image Handling with Session State (RAM) ---
    # This prevents file conflicts on Cloud and handles blinking locally
    
    if "image_data" not in st.session_state:
        st.session_state.image_data = None
        
    if uploaded_file:
        # Check if this file is different from the one currently loaded
        # We compare file IDs or names/sizes as a proxy if id not available effectively
        # Streamlit's UploadedFile has a .file_id attribute usually, or we can use the object itself if it persists
        
        file_changed = True
        if "last_uploaded_file" in st.session_state:
            if st.session_state.last_uploaded_file == uploaded_file:
                 file_changed = False
        
        if file_changed:
            uploaded_file.seek(0)
            try:
                image = Image.open(uploaded_file)
                image = ImageOps.exif_transpose(image)
                # Ensure consistent mode (RGBA covers all bases)
                image = image.convert("RGBA") 
                st.session_state.image_data = image
                st.session_state.last_uploaded_file = uploaded_file
            except Exception as e:
                st.error(f"Error loading image: {e}")
                st.session_state.image_data = None

    # Use image from session state if available
    image = st.session_state.image_data

    # --- Debug: Verify Image Load ---
    if image:
        with st.expander("Debug: Check Image Loading", expanded=False):
            st.image(image, caption="If you see this, the image is loaded correctly in Python.", use_column_width=True)
            st.write(f"Image Mode: {image.mode}, Size: {image.size}")

    # --- Canvas Init Logic ---
    if "canvas_init" not in st.session_state:
        st.session_state.canvas_init = None
    
    if image:
        img_w, img_h = image.size
        
        # --- Toolbar ---
        t_col1, t_col2, t_col3, t_col4 = st.columns([2, 1, 2, 1])
        
        with t_col1:
            mode_options = {
                "Free Draw": "freedraw",
                "Highlighter": "freedraw",
                "Selection Box": "rect",
                "Edit / Delete": "transform"
            }
            selected_mode = st.radio("Tool", list(mode_options.keys()), horizontal=True, label_visibility="collapsed")
            drawing_mode = mode_options[selected_mode]

        default_color = "#007AFF" if selected_mode == "Selection Box" else "#FF0000"
        if selected_mode == "Highlighter": default_color = "#FFFF00"
        
        default_width = 3
        if selected_mode == "Highlighter": default_width = 20
        if selected_mode == "Selection Box": default_width = 2
        
        real_stroke_color = default_color
        real_fill_color = "rgba(0,0,0,0)"

        with t_col2:
            stroke_color = st.color_picker("Color", default_color, label_visibility="collapsed")
            real_stroke_color = stroke_color
            if selected_mode == "Highlighter":
                if len(stroke_color) == 7:
                     real_stroke_color = stroke_color + "50"
            if selected_mode == "Selection Box":
                real_fill_color = "rgba(0, 122, 255, 0.1)"
                
        with t_col3:
            stroke_width = st.slider("Width", 1, 30, default_width, label_visibility="collapsed")
        
        with t_col4:
            pass

        # --- Canvas ---
        canvas_result = st_canvas(
            fill_color=real_fill_color,
            stroke_width=stroke_width,
            stroke_color=real_stroke_color,
            background_image=image,
            update_streamlit=True,
            height=img_h,
            width=img_w,
            drawing_mode=drawing_mode,
            initial_drawing=None, # We rely on internal state persistence of st_canvas in simple run
            # PROPER PERSISTENCE TRICK:
            # If we pass initial_drawing=None, st_canvas keeps its state during simple reruns.
            # If we pass a value, it RESETS to that value.
            # We only want to set it on FIRST LOAD or RESET. 
            # Since we cleared file logic, we let st_canvas handle its own session state mostly,
            # BUT if we want to save data, we are stuck.
            # For Cloud: st_canvas usually persists active state as long as key is same.
            # Force re-render if image changes by updating the key
            canvas_key = "canvas"
            if "last_uploaded_file" in st.session_state and st.session_state.last_uploaded_file:
                f = st.session_state.last_uploaded_file
                # Create a unique key based on filename and size to ensure updates
                canvas_key = f"canvas_{f.name}_{f.size}"
                
            key=canvas_key,
            display_toolbar=True
        )
        
        # We don't save to JSON file anymore. 

    else:
        st.info("Please upload an image in the sidebar to start.")

with col2:
    st.subheader("Notes & Plan")
    
    default_notes = st.text_area("General Notes", height=150, placeholder="Start typing...")
    combined_notes = f"GENERAL NOTES:\n{default_notes}\n\n"
    
    # Linked Notes
    if 'canvas_result' in locals() and canvas_result.json_data is not None:
        objects = canvas_result.json_data["objects"]
        rect_objects = [obj for obj in objects if obj["type"] == "rect"]
        rect_objects.sort(key=lambda obj: (obj.get('top', 0), obj.get('left', 0)))
        
        if rect_objects:
            st.divider()
            st.write(f"**Selection Notes ({len(rect_objects)})**")
            
            for i, obj in enumerate(rect_objects):
                note_key = f"note_rect_{i}"
                rect_note = st.text_input(f"#{i+1} Selection Note", key=note_key)
                combined_notes += f"SELECTION #{i+1}:\n{rect_note}\n\n"

    st.divider()
    
    # --- Download Section ---
    if 'image' in locals() and image:
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            st.download_button(
                label="📄 Download Text",
                data=combined_notes,
                file_name="project_notes.txt",
                mime="text/plain",
                use_container_width=True
            )
            
        with col_dl2:
            # Composite Image Logic
            if canvas_result.image_data is not None:
                try:
                    canvas_img_data = canvas_result.image_data.astype('uint8')
                    canvas_img = Image.fromarray(canvas_img_data)
                    base_img = image.convert("RGBA")
                    
                    if canvas_img.size != base_img.size:
                        canvas_img = canvas_img.resize(base_img.size)
                        
                    final_img = Image.alpha_composite(base_img, canvas_img)
                    
                    buf = io.BytesIO()
                    final_img.convert("RGB").save(buf, format="JPEG", quality=90)
                    byte_im = buf.getvalue()
                    
                    st.download_button(
                        label="🖼️ Download Image",
                        data=byte_im,
                        file_name="annotated_image.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )
                except Exception as e:
                    pass
