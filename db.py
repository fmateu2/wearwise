from pymongo import MongoClient
from dotenv import load_dotenv  # Load environment variables.
import os

load_dotenv()

# initialize the MongoDB client
client = MongoClient(os.getenv("MONGODB_URI"))

# specific database and colleciton
db = client[os.getenv("MONGODB_DB")]
collection = db[os.getenv("MONGODB_COLLECTION")]


# Inserts a single document into the configured MongoDB collection:
def save_document(doc):
    collection.insert_one(doc)


def get_database(url, db_name):
    client = MongoClient(url)
    return client[db_name]


def get_collection(db, collection_name):
    return db[collection_name]


def load_garments(collection):
    # Retrieve full documents to access _id and specific attributes
    cursor = collection.find({})
    return list(cursor)
