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

    def get_task_name_by_id(self, task_id: str):
        try:
            task = self.read_item_by_id(os.getenv("TASK"), task_id)
            task_name = task.get("properties", {}).get("name", {}).get("title", [{}])[0].get("plain_text", "")
            return task_name
        except Exception as e:
            raise HTTPException

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

    def update_item(self, item_id, properties):
        try:
            updated_item = self.notion.pages.update(page_id=item_id, properties=properties)
            return updated_item
        except Exception as e:
            print(f"Error al actualizar el item con ID {item_id}: {e}")
            return None

    def create_item(self, database_id, properties):
        try:
            new_item = self.notion.pages.create(parent={"database_id": database_id}, properties=properties)
            return new_item
        except Exception as e:
            print(f"Error al crear el item: {e}")
            return None

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

@app.get("/subcontractors/{subcontractor_id}/items/", response_model=List[Dict[str, Union[str, int, None]]])
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
                    task_name = notion_manager.get_task_name_by_id(task_id)

                # Obtiene la fecha
                date_info = item.get("properties", {}).get("date", {}).get("date")
                date_value = None
                if date_info:
                    date_value = date_info.get("start", "")

                # Manejo de errores para propiedades vacías
                if not (code_num and status_name and task_id):
                    raise HTTPException(status_code=404, detail="Propiedad vacía en el item")

                subcontractor_items.append({"id": item["id"], "code_num": code_num, "status": status_name, "task_id": task_id, "task_name": task_name, "date": date_value})
                break
    return subcontractor_items

@app.put("/itinerary/{item_id}/{status}/")
def update_itinerary_item_status(item_id: str, status: str):
    # Llamamos a la función para actualizar el item en el itinerario
    properties = {'status': {'multi_select': [{'name': status}]}}
    updated_item = notion_manager.update_item(item_id, properties)
    
    # Verificamos si la actualización fue exitosa
    if updated_item:
        return {"message": f"Estado del item con ID {item_id} actualizado correctamente a '{status}'"}
    else:
        raise HTTPException(status_code=500, detail=f"No se pudo actualizar el estado del item con ID {item_id}")

@app.post("/sub-itinerary/{subcontractor_id}/{task_id}/{status}/")
def create_sub_itinerary_item(subcontractor_id: str, task_id: str, status: str):
    try:
        properties = {
            "task": {
                "relation": [{"id": task_id}]
            },
            "status": {
                "multi_select": [{"name": status}]
            },
            "subcontractor": {
                "relation": [{"id": subcontractor_id}]
            }
        }

        
        # Llama a la función para crear el nuevo item en la base de datos "sub itinerary"
        new_item = notion_manager.create_item(database_id=os.getenv("SUB_ITINERARY"), properties=properties)
        
        if new_item:
            return {"message": "Nuevo elemento creado en sub-itinerary"}
        else:
            raise HTTPException(status_code=500, detail="No se pudo crear el nuevo elemento en sub-itinerary")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear el nuevo elemento en sub-itinerary: {e}")