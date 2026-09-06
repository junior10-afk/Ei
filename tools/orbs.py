from typing import Dict, Any
from tools.registry import tool_registry
from core.bus import bus
from core.config import config

ORB_MAP = {
    "cyber_blue": "cyber_blue",
    "cyan": "cyber_blue",
    "bleu": "cyber_blue",
    "classique": "cyber_blue",
    
    "iron_man": "iron_man",
    "stark": "iron_man",
    "mark 7": "iron_man",
    "mark vii": "iron_man",
    
    "arc_reactor": "arc_reactor",
    "arc reactor": "arc_reactor",
    "reacteur": "arc_reactor",
    "réacteur": "arc_reactor",
    "reacteur arc": "arc_reactor",
    "réacteur arc": "arc_reactor",
    "mark 85": "arc_reactor",
    
    "hal_9000": "hal_9000",
    "hal": "hal_9000",
    "hal 9000": "hal_9000",
    
    "cortana": "cortana",
    "halo": "cortana",
    
    "aperture": "aperture",
    "portal": "aperture",
    "glados": "aperture",
    
    "tachikoma": "tachikoma",
    "ghost in the shell": "tachikoma",
    
    "gargantua": "gargantua",
    "trou noir": "gargantua",
    "interstellar": "gargantua",
    "singularite": "gargantua",
    "singularité": "gargantua",
    
    "pulsar": "pulsar",
    "neutron": "pulsar",
    
    "saturn_rings": "saturn_rings",
    "saturne": "saturn_rings",
    "saturn": "saturn_rings",
    "anneaux": "saturn_rings",
    
    "aurora": "aurora",
    "aurore": "aurora",
    "aurore boreale": "aurora",
    "aurore boréale": "aurora",
    
    "dark_matter": "dark_matter",
    "matiere noire": "dark_matter",
    "matière noire": "dark_matter",
    
    "solar_flare": "solar_flare",
    "soleil": "solar_flare",
    "solaire": "solar_flare",
    
    "tesla_coil": "tesla_coil",
    "tesla": "tesla_coil",
    "foudre": "tesla_coil",
    "eclair": "tesla_coil",
    "éclair": "tesla_coil",
    
    "abyssal": "abyssal",
    "abysse": "abyssal",
    "abysses": "abyssal",
    "ocean": "abyssal",
    "océan": "abyssal",
    
    "crystal": "crystal",
    "cristal": "crystal",
    "chronos": "crystal",
    "diamant": "crystal",
    
    "radioactive": "radioactive",
    "radioactif": "radioactive",
    "nucleaire": "radioactive",
    "nucléaire": "radioactive",
    "tchernobyl": "radioactive",
    "rad": "radioactive",
    
    "tesseract": "tesseract",
    "hypercube": "tesseract",
    "cube": "tesseract",
    
    "dna_helix": "dna_helix",
    "adn": "dna_helix",
    "dna": "dna_helix",
    "helice": "dna_helix",
    "hélice": "dna_helix",
    
    "neural_synapse": "neural_synapse",
    "synapse": "neural_synapse",
    "neurone": "neural_synapse",
    "cerveau": "neural_synapse",
    
    "synthwave": "synthwave",
    "retrowave": "synthwave",
    "outrun": "synthwave",
    "annees 80": "synthwave",
    "années 80": "synthwave",
    
    "matrix_code": "matrix_code",
    "matrix": "matrix_code",
    "matrice": "matrix_code"
}

ORB_DISPLAY_NAMES = {
    "cyber_blue": "Cyan Cyber",
    "iron_man": "Mark VII Stark",
    "arc_reactor": "Arc Reactor MK-85",
    "hal_9000": "HAL-9000",
    "cortana": "Cortana Hologram",
    "aperture": "Aperture Optical Core",
    "tachikoma": "Tachikoma Cyber-Net",
    "gargantua": "Gargantua Trou Noir",
    "pulsar": "Neutron Pulsar",
    "saturn_rings": "Saturn Rings",
    "aurora": "Aurora Borealis",
    "dark_matter": "Matière Noire",
    "solar_flare": "Solar Flare",
    "tesla_coil": "Tesla 100kV",
    "abyssal": "Abyssal Biolum",
    "crystal": "Crystal Chronos",
    "radioactive": "Rad-226 Isotope",
    "tesseract": "Tesseract 4D",
    "dna_helix": "Double Hélice ADN",
    "neural_synapse": "Neural Synapse",
    "synthwave": "Synthwave 84",
    "matrix_code": "Matrix Code"
}

@tool_registry.register(
    name="set_orb",
    description="Change l'orbe 3D holographique du HUD par son nom ou son preset",
    parameters={"preset_name": "str (ex: 'gargantua', 'arc reactor', 'hal', 'matrix', 'tesla', 'saturne')"}
)
def set_orb(preset_name: str) -> Dict[str, Any]:
    query = preset_name.lower().strip()
    preset_id = None
    
    # 1. Correspondance exacte ou partielle
    for alias, pid in ORB_MAP.items():
        if alias == query:
            preset_id = pid
            break
            
    if not preset_id:
        for alias, pid in ORB_MAP.items():
            if alias in query or query in alias:
                preset_id = pid
                break
                
    if not preset_id:
        preset_id = "cyber_blue"
        
    config.update({"orb_preset": preset_id, "orb_theme": preset_id})
    bus.broadcast_threadsafe({
        "type": "action",
        "action": "set_orb",
        "params": {"preset_id": preset_id}
    })
    
    display_name = ORB_DISPLAY_NAMES.get(preset_id, preset_id)
    return {
        "speech": f"Orbe {display_name} configuré.",
        "data": {"preset_id": preset_id, "name": display_name}
    }
