import os
import streamlit as st
import time
import json
from pymongo import MongoClient
import base64
import forward_chaining
from dotenv import load_dotenv
from db import save_document
from agent import run_agent
from PIL import Image
import uuid
import io
import db as db_tools

load_dotenv()

# mondodb connection with sensible information
MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION")

# mapping for formality levels
FORMALITY_MAP = {"Formal": "formal", "Semi-Formal": "business_casual", "Informal/Casual": "casual"}


def to_thumbnail_base64(image_bytes, max_size=512):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")  # reads and converts to RGB
    image.thumbnail((max_size, max_size))  # resize maintaingn ratio (512 pixels max)
    buf = io.BytesIO()
    image.save(
        buf, format="JPEG", optimize=True, quality=85
    )  # asve to buffer instead of hard drive

    return base64.b64encode(buf.getvalue()).decode("utf-8")  # convert to text string


def get_image_data(filename, collection):
    # searches for the document with the specified filename
    doc = collection.find_one({"filename": filename}, {"image_base64": 1})

    # if the documents is found and contains image data
    if doc and "image_base64" in doc:
        image_text = doc["image_base64"]  # value from"image_base64" assigned to image_text

        try:
            return base64.b64decode(image_text)  # convert text into image bytes

        except Exception as e:
            print(f"Error decoding image: {e}")  # error handling
            return None

    return None


# USER INTERFACE IMPLEMENTATION - extractor: image upload
st.set_page_config(page_title="WearWise", layout="wide")

st.title("WearWise")
st.write("Upload one or more images of your garments to add them to your virtual wardrobe.")

uploaded_files = st.file_uploader(
    "Upload images", type=["jpg", "png", "jpeg"], accept_multiple_files=True
)

if uploaded_files:
    if st.button("Process Images"):
        for file in uploaded_files:
            image_bytes = file.read()

            with st.status(f"Processing {file.name}...", expanded=True) as status:
                status.write("Step 1: running vision extraction / validation / normalization...")
                result = run_agent(image_bytes)
                status.update(label=f"Completed {file.name}", state="complete")

                thumb_b64 = to_thumbnail_base64(image_bytes)
                raw_garments = result["raw"].get("garments", [])
                corrected_garments = result["corrected"].get("garments", [])
                normalized_garments = result["normalized"].get("garments", [])

                for idx, norm in enumerate(normalized_garments):
                    stored_doc = {
                        "_id": str(uuid.uuid4()),
                        "filename": file.name,
                        "garment_index": idx,
                        "normalized_attributes": norm,
                        "corrected_attributes": (
                            corrected_garments[idx] if idx < len(corrected_garments) else None
                        ),
                        "raw_attributes": raw_garments[idx] if idx < len(raw_garments) else None,
                        "image_base64": thumb_b64,
                    }
                    save_document(stored_doc)

            st.success(f"Stored garment documents for {file.name}")

            # Display uploaded image preview (smaller, fixed width)
            st.image(image_bytes, caption=file.name, width=360)

            # Show JSON at each stage
            st.subheader("Raw attributes")
            st.json(result["raw"])

            st.subheader("Corrected attributes")
            st.json(result["corrected"])

            st.subheader("Normalized attributes")
            st.json(result["normalized"])

# USER INTERFACE IMPLEMENTATION - parameter input
# inside title and headers
st.markdown("Fill in the details below to generate an outfit tailored to your needs:")

# creates main layout for parameter input:
with st.container(border=True):
    st.subheader("Context:")
    col1, col2 = st.columns(2)

    # first column
    with col1:
        season = st.selectbox(
            "Current Season", ["Spring", "Summer", "Autumn", "Winter"]
        )  # dropdown menu for season
        temp = st.number_input(
            "Temperature (Cº)", min_value=-30, max_value=50
        )  # temperature input box

    # second column
    with col2:
        formality = st.radio(
            "Formality Level", ["Formal", "Semi-Formal", "Informal/Casual"]
        )  # buttons for formality level
        occasion = st.selectbox(
            "What is the Occasion?", ["Travel", "Sport", "Work", "Party", "Date"]
        )  # dropdown menu for occasion


if st.button("Get My Recommendation"):
    with st.spinner('Consulting the knowledge base...'):
        time.sleep(1.5)  # added delay to simulate processing time

    # build user facts from input
    user_data = {
        "temperature": temp,
        "formality": FORMALITY_MAP[formality],
        "season": season.lower(),
        "occasion": occasion.lower(),
    }

    # load wardrobe rules from JSON file
    with open("normalization.json", "r") as f:
        full_data = json.load(f)

    db = db_tools.get_database(MONGO_URI, DB_NAME)
    collection = db_tools.get_collection(db, COLLECTION_NAME)

    garments = db_tools.load_garments(collection)

    # get recommendation using forward chaining
    result = forward_chaining.recommend_outfit_forward_chaining(user_data, garments, full_data)

    # DISPLAY IMPLEMENTATION
    st.divider()
    st.subheader("Recommended Outfit:")

    col_res1, col_res2, col_res3 = st.columns(3)

    # Main items: top, bottom, shoes
    with col_res1:
        st.caption("Top")
        if result["top"]:
            filename = result["top"]["filename"]

            image_bytes = get_image_data(filename, collection)

            if image_bytes:
                st.image(image_bytes)
            else:
                st.warning(f"Image data missing for: {filename}")
        else:
            st.warning("No Top found")

    with col_res2:
        st.caption("Bottom")
        if result["bottom"]:
            filename = result["bottom"]["filename"]
            image_bytes = get_image_data(filename, collection)

            if image_bytes:
                st.image(image_bytes)
            else:
                st.warning(f"Image data missing for: {filename}")
        else:
            st.warning("No Bottom found")

    with col_res3:
        st.caption("Shoes")
        if result["shoes"]:
            filename = result["shoes"]["filename"]
            image_bytes = get_image_data(filename, collection)

            if image_bytes:
                st.image(image_bytes)
            else:
                st.warning(f"Image data missing for: {filename}")
        else:
            st.warning("No Shoes found")

    # Extra items (coats and outerwear)
    if result["extra"]:
        st.divider()
        st.subheader("Outerwear & Accessories")
        st.write("Essential items based on your rules")

        # Display extra items in a grid
        cols = st.columns(4)
        for i, item in enumerate(result["extra"]):
            with cols[i % 4]:
                fname = item["filename"]
                st.image(get_image_data(fname, collection))
