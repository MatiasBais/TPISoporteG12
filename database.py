from pymongo import MongoClient

MONGO_URI = 'mongodb+srv://matias:daotb0GNJneIML0x@melicompara.oxatgfh.mongodb.net/?retryWrites=true&w=majority'

def dbConnection():
    client = MongoClient(MONGO_URI)
    db = client["melicompara"]
    return db

