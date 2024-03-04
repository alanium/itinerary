from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from notion_client import Client
from dotenv import load_dotenv
from typing import List, Dict, Union


app = FastAPI()

load_dotenv()

class NotionManager:
    def __init__(self):
        self.notion_token = os.getenv("TOKEN")
        self.notion = Client(auth=self.notion_token)
        self.data_converter = DataConverter()


    def query_database(self, database_id):
        try:
            return self.notion.databases.query(database_id=database_id)["results"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al consultar la base de datos de Notion: {e}")
        
    def search_item_by_name(self, database_id, target_name):
        database_items = self.query_database(database_id)
        for item in database_items:
            name_property = item.get("properties", {}).get("Name", {})
            title_list = name_property.get("title", [])
            if title_list:
                item_name = title_list[0].get("plain_text", "")
                if item_name.lower() == target_name.lower():
                    return {"id": item["id"], "name": item_name}
        return None
    
    def read_item_by_id(self, database_id, item_id):
        try:
            item = self.notion.pages.retrieve(database_id=database_id, page_id=item_id)
            return item
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al leer el item con ID {item_id}: {e}")

    def update_item_status(self, database_id, item_id, new_status):
        try:
            updated_item = self.notion.pages.update(page_id=item_id, properties={"Status": {"select": {"name": new_status}}})
            return updated_item
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al actualizar el item con ID {item_id}: {e}")

    def convert_to_json(self, items):
        return self.data_converter.convert_to_json(items)

class DataConverter:
    @staticmethod
    def convert_to_json(items):
        json_data = []
        for item in items:
            item_id = item.get("id")
            name_property = item.get("properties", {}).get("Name", {})
            title_list = name_property.get("title", [])
            item_name = title_list[0].get("plain_text", "") if title_list else ""
            json_data.append({"id": item_id, "name": item_name})
        return json_data

class SubcontractorRequest(BaseModel):
    id: str
    name: str

class UpdateItemStatusRequest(BaseModel):
    new_status: str

notion_manager = NotionManager()
subcontractors_db = os.getenv("SUBCONTRACTORS")
sub_itinerary_db = os.getenv("SUB_ITINERARY")

@app.get("/subcontractors/", response_model=List[Dict[str, Union[str, int]]])
def get_subcontractors():
    subcontractors = notion_manager.query_database(subcontractors_db)
    formatted_data = notion_manager.convert_to_json(subcontractors)
    return formatted_data

@app.get("/subcontractors/{subcontractor_id}/items/", response_model=List[Dict[str, Union[str, int]]])
def get_items_by_subcontractor(subcontractor_id: str):
    items = notion_manager.query_database(sub_itinerary_db)
    subcontractor_items = []
    for item in items:
        subcontractor_relations = item.get("properties", {}).get("subcontractor", {}).get("relation", [])
        for relation in subcontractor_relations:
            if relation.get("id") == subcontractor_id:
                # Obtiene el código "code_num"
                code_num = item.get("properties", {}).get("code_num", {}).get("title", [{}])[0].get("plain_text", "")

                # Obtiene el status
                status = item.get("properties", {}).get("status", {}).get("multi_select", [])
                status_name = None
                if status:
                    status_name = status[0].get("name", "")

                # Obtiene el id de la task
                task_id = None
                task_relation = item.get("properties", {}).get("task", {}).get("relation", [])
                if task_relation:
                    task_id = task_relation[0].get("id", "")

                # Manejo de errores para propiedades vacías
                if not (code_num and status_name and task_id):
                    raise HTTPException(status_code=404, detail="Propiedad vacía en el item")

                subcontractor_items.append({"id": item["id"], "code_num": code_num, "status": status_name, "task_id": task_id})
                break
    return subcontractor_items


