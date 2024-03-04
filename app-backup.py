import os
from notion_client import Client
from dotenv import load_dotenv

class NotionManager:
    def __init__(self):
        load_dotenv()
        self.notion_token = os.getenv("TOKEN")
        self.notion = Client(auth=self.notion_token)

    def get_task_name_by_id(self, task_id: str):
        try:
            task = self.read_item_by_id(os.getenv("TASK"), task_id)
            task_name = task.get("properties", {}).get("name", {}).get("title", [{}])[0].get("plain_text", "")
            return task_name
        except Exception as e:
            raise (f"Error al obtener el nombre de la tarea con ID {task_id}: {e}")

    def create_item(self, database_id, properties):
        try:
            new_item = self.notion.pages.create(parent={"database_id": database_id}, properties=properties)
            return new_item
        except Exception as e:
            print(f"Error al crear el item: {e}")
            return None
    
    def update_item(self, item_id, properties):
        try:
            updated_item = self.notion.pages.update(page_id=item_id, properties=properties)
            return updated_item
        except Exception as e:
            print(f"Error al actualizar el item con ID {item_id}: {e}")
            return None
    
    def delete_item(self, item_id):
        try:
            self.notion.pages.update(page_id=item_id, archived=True)
            print(f"Item con ID {item_id} eliminado correctamente.")
        except Exception as e:
            print(f"Error al eliminar el item con ID {item_id}: {e}")

    def query_database(self, database_id):
        try:
            return self.notion.databases.query(database_id=database_id)["results"]
        except Exception as e:
            print("Ocurrió un error al consultar la base de datos de Notion:", e)
            return []
        
    def search_item_by_name(self, database_id, target_name):
        database_items = self.query_database(database_id)
        for item in database_items:
            name_property = item.get("properties", {}).get("Name", {})
            title_list = name_property.get("title", [])
            if title_list:
                item_name = title_list[0].get("plain_text", "")
                if item_name.lower() == target_name.lower():
                    return item
        return None
    
    def read_item_by_id(self, database_id, item_id):
        try:
            item = self.notion.pages.retrieve(database_id=database_id, page_id=item_id)
            return item
        except Exception as e:
            print(f"Error al leer el item con ID {item_id}: {e}")
            return None

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

class App:
    def __init__(self):
        self.notion_manager = NotionManager()

    def get_database_items(self, database_id):
        return self.notion_manager.query_database(database_id)

    def convert_to_json(self, items):
        return DataConverter.convert_to_json(items)

    def process_data(self, database_id):
        items = self.get_database_items(database_id)
        return self.convert_to_json(items)

if __name__ == "__main__":
    app = App()
    var = app.notion_manager.query_database(os.getenv("SUB_ITINERARY"))
    print(var[0])

    




    #ejemplos de uso
    """
    # Crear un nuevo item
    new_item_properties = {"Name": {"title": [{"text": {"content": "Nuevo Item"}}]}}
    new_item = app.notion_manager.create_item(os.getenv("SUBCONTRACTORS"), new_item_properties)
    if new_item:
        print("Nuevo item creado:", new_item)
    """
    
    """
    # Actualizar un item existente
    item_id_to_update = "e175996c-bb82-4007-841b-64af35851c1f"
    updated_item_properties = {"Name": {"title": [{"text": {"content": "Nombre Actualizado"}}]}}
    updated_item = app.notion_manager.update_item(item_id_to_update, updated_item_properties)
    if updated_item:
        print("Item actualizado:", updated_item)  
    """