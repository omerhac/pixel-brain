from pixelbrain.data_loader import DataLoader
from pixelbrain.database import Database
from pixelbrain.modules.gpt4v import GPT4VPeopleDetectorModule
import pytest


@pytest.mark.skip(reason="gpt4v preview version, rate limits..")
def test_gpt4v_people_detector():
    database = Database(database_id="gpt4v")
    # test only one image to save cost
    data = DataLoader("assets/test_data//Users/nurithofesh/ws/pixel-brain/assets/test_data/00375_00.jpg", database, decode_images=False)
    module = GPT4VPeopleDetectorModule(data, database)
    module.process()
    
    metadata = database.get_all_images()
    for meta in metadata:
        assert "is_person" in meta
    database.delete_db()