import requests
from typing import Dict, Any
from tools.registry import tool_registry

WEATHER_CODES = {
    0: "ciel dégagé",
    1: "principalement dégagé",
    2: "partiellement nuageux",
    3: "couvert",
    45: "brumeux",
    48: "brouillard givrant",
    51: "bruine légère",
    53: "bruine modérée",
    55: "bruine dense",
    61: "pluie légère",
    63: "pluie modérée",
    65: "forte pluie",
    71: "chute de neige légère",
    73: "chute de neige modérée",
    75: "forte chute de neige",
    80: "averses de pluie",
    95: "orage"
}

@tool_registry.register(
    name="get_weather",
    description="Obtient la météo en temps réel pour une ville",
    parameters={"city": "str (ex: Paris, Lyon, Marseille)"}
)
def get_weather(city: str = "Paris") -> Dict[str, Any]:
    try:
        # Géocodage de la ville via Open-Meteo
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=fr&format=json"
        geo_res = requests.get(geo_url, timeout=5).json()

        if not geo_res.get("results"):
            return {
                "speech": f"Désolé, je n'ai pas trouvé la localisation pour {city}.",
                "data": {"error": "Ville non trouvée"}
            }

        place = geo_res["results"][0]
        lat = place["latitude"]
        lon = place["longitude"]
        city_name = place.get("name", city)

        # Données météo
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_res = requests.get(weather_url, timeout=5).json()

        current = w_res.get("current_weather", {})
        temp = round(current.get("temperature", 20))
        code = current.get("weathercode", 0)
        desc = WEATHER_CODES.get(code, "temps variable")
        wind = round(current.get("windspeed", 0))

        speech = f"À {city_name}, il fait actuellement {temp} degrés avec un {desc}."
        return {
            "speech": speech,
            "data": {
                "city": city_name,
                "temperature": temp,
                "description": desc,
                "wind_kmh": wind
            }
        }
    except Exception as e:
        return {
            "speech": f"Impossible d'obtenir la météo pour {city}.",
            "data": {"error": str(e)}
        }
