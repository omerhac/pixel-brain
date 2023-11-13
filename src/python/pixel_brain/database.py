from pymongo import MongoClient
import chromadb
import numpy as np
from typing import List, Tuple


class Database:
    """
    This class is used to interact with the MongoDB database.
    """
    def __init__(self, mongo_key: str = None, database_id: str = 'db'):
        """
        Initialize the Database class.
        
        :param mongo_key: The MongoDB connection string.
        :param database_id: The ID of the database to connect to.
        """
        if mongo_key:
            self._db = MongoClient(mongo_key)[database_id]
            self._vector_db = None
        else:
            self._db = MongoClient()[database_id]
            self._vector_db = chromadb.Client()
        self._db_id = database_id

    def add_image(self, image_id: str, image_path: str):
        """
        Add an image to the database
        :param image_id (str): image unique identifier
        :param image_path (str): image path (can be remote storage)
        """
        if self._db.images.find_one({'_id': image_id}):
            raise ValueError(f"Image ID {image_id} already exists in the database")

        self._db.images.update_one({'_id': image_id}, {'$set': {"image_path": image_path}}, upsert=True)

    def store_field(self, image_id: str, field_name: str, field_value: str or np.array):
        """
        Store a field in the database.
        
        :param image_id: The ID of the image.
        :param field_name: The name of the field to store.
        :param field_value: The value of the field to store.
        """
        if not self._db.images.find_one({'_id': image_id}):
            raise ValueError(f"Image ID {image_id} does not exist in the database")
        if isinstance(field_value, np.ndarray) and self._vector_db is not None:
            if self._vector_db is None:
                # TODO: support remote vector store using mongodb atlas
                raise RuntimeError("To store an embedding, vector store must be initialized")
            if field_name.find("-") != -1:
                raise ValueError("Field namd with vector values cannot have '-' in it")
            index_fqn = f"{self._db_id}-{field_name}"
            self._store_vector(index_fqn, image_id, field_value)
        else:
            self._db.images.update_one({'_id': image_id}, {'$set': {field_name: field_value}}, upsert=True)

    def _store_vector(self, index_fqn : str, image_id: str, embedding: np.array):
        assert self._vector_db is not None, "TODO: support remote vector store"
        index = self._vector_db.get_or_create_collection(index_fqn, embedding_function=None)
        index.upsert(image_id, embedding.tolist())
        
    def query_vector_field(self, field_name: str, query: np.array, n_results=1) -> Tuple[List[dict], List[float]]:
        """
        Query the relevant vector index for n_results closest images
        and return closest results metadata and distance metric
        
        :param field_name: The name of the field to query.
        :param query: The query vector.
        :param n_results: The number of results to return. Default is 1.
        :return: A tuple containing a list of the closest result metadata and a list of distance metrics.
        """
        if self._vector_db is None:
            # TODO: support remote vector store
            raise ValueError("Vector database is not initialized")
        index_fqn = f"{self._db_id}-{field_name}"
        return self._query_vector(index_fqn, query, n_results)

    def _query_vector(self, index_fqn: str, query: np.array, n_results):
        assert self._vector_db is not None, "TODO: support remote vector store"
        try:
            index = self._vector_db.get_collection(index_fqn)
        except ValueError as err:
            raise RuntimeError(f"Cant find {index_fqn} in vector database")
        results = index.query(
            query.tolist(),
            n_results=n_results
        )
        results_meta = [self.find_image(image_id) for image_id in results['ids'][0]]
        results_dists = results['distances'][0]
        return results_meta, results_dists

    def find_image(self, image_id: str) -> dict:
        """
        Find an image in the database.
        
        :param image_id: The ID of the image to find.
        :return: The image document.
        """
        return self._db.images.find_one({'_id': image_id})
    
    def get_all_images(self) -> list:
        """
        Retrieve all images from the database.
        
        :return: A list of all image documents.
        """
        return list(self._db.images.find())
    
    def delete_db(self):
        """Delete database (use with caution)"""
        self._db.client.drop_database(self._db_id)
        if self._vector_db is not None:
            # TODO support remote vector store
            for index in self._vector_db.list_collections():
                index_name = index.name
                if index_name.split("-")[0] == self._db_id:
                    self._vector_db.delete_collection(index_name)