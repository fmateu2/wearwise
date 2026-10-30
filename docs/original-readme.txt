WearWise - Rule based expert fashion system

Features
- AI Garment Extraction: uses GPT to detect clothing and footwear from images and clean it.
- Virtual Wardrobe: provided images are uploaded to a MongoDB database
- Simple normalization is applied using specified files

- Context recommendations: A rule based system generates outfits based on:
    - Weather: Automatically forbids unsafe items (using hardcoded rules)
    - Occasion: Enforces strict dress codes for different situations
    - Formality: Narrows decisions using provided formality parameters
    - Season: Discriminated wardrobe depending on specified season
 
- Outfit Scoring: Ranks available items based on color compatibility, user preference, and specific occasion matches.

Specifications

Frontend: Streamlit
Database: MongoDB
Logic: Python (Rule-Based Expert System / Forward Chaining)
Image Processing: Pillow (PIL)

Project Structure

UserInterface.py    - Main application (Streamlit UI).
agent.py            - Contacts ChatGPT and queries image recognition.
forward_chaining.py - The inference engine that fires rules from user context.
normalizer.py       - Standardizes raw outputs into a standard format.
db.py               - Database connection string and helper functions for MongoDB.
normalization.json  - Configuration file containing all logic rules, color maps, and categories.

How to run

1.  Install Requirements
    pip install -r requirements.txt
    
2. For execution run:
    streamlit run UserInterface.py

    This will open the user interface from which images can be provided for thei extraction and upload to the database, 
    and from where the inference engine can be tested by providing parameters about the context.
