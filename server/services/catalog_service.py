from typing import List, Dict, Any
from repositories.catalog_repository import fetch_all_active_cuisines
from exceptions.service import ServiceException

async def get_all_cuisines_service() -> Dict[str, Any]:
    """
    Service to get all active cuisines and format them for the API response.
    """
    try:
        cuisines = await fetch_all_active_cuisines()
        
        cuisine_data = []
        for c in cuisines:
            cuisine_data.append({
                "id": c.code,
                "name": c.name_en
            })
            
        return {
            "success": True,
            "message": "Cuisine list fetched successfully.",
            "data": cuisine_data
        }
    except Exception as ex:
        raise ServiceException(f"Error fetching cuisines: {str(ex)}") from ex
