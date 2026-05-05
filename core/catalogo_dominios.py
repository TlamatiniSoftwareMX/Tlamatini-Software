import re
import unicodedata
from typing import Dict, List


CATALOGO_DOMINIOS: Dict[str, Dict[str, object]] = {
    "medica": {
        "tipo": "existente",
        "aliases": ["medica", "medicina", "medico", "salud", "clinica"],
        "keywords": [
            "medicina", "salud", "paciente", "diagnostico", "tratamiento", "enfermedad",
            "padecimiento", "sintoma", "signo", "terapia", "medicamento", "farmaco",
            "dosis", "contraindicacion", "procedimiento", "curacion", "anatomia",
            "fisiologia", "patologia", "lesion", "herida", "hemorragia", "fractura",
            "infeccion", "choque", "reanimacion", "triage", "ecografia", "radiografia",
            "laboratorio", "cirugia", "quirurgico", "urgencias", "semiologia",
        ],
        "subdomains": {
            "urgencias": ["urgencia", "emergencia", "choque", "hemorragia", "trauma", "paro", "rcp", "resucitacion", "reanimacion"],
            "farmacologia": ["medicamento", "farmaco", "dosis", "posologia", "via", "frecuencia", "antibiotico", "insulina", "analgesico"],
            "anatomia": ["hueso", "arteria", "vena", "nervio", "musculo", "organo", "esqueleto", "ligamento", "tendon"],
            "fisiologia": ["funcion", "homeostasis", "metabolismo", "respiracion", "circulacion", "filtracion", "absorcion"],
            "ginecologia": ["embarazo", "utero", "ovario", "parto", "menstruacion", "puerperio", "lactancia"],
            "pediatria": ["lactante", "neonato", "nino", "pediatria", "vacunacion", "crecimiento"],
            "procedimientos": ["curacion", "asepsia", "antisepsia", "suturas", "canalizacion", "vendaje", "lavado"],
            "semiologia": ["anamnesis", "exploracion", "inspeccion", "palpacion", "percusion", "auscultacion"],
            "trauma": ["fractura", "luxacion", "esguince", "contusion", "politrauma", "inmovilizacion"],
        },
    },
    "proteccion_civil": {
        "tipo": "existente",
        "aliases": ["proteccion_civil", "proteccion civil", "proteccion", "emergencias", "respuesta"],
        "keywords": [
            "proteccion civil", "rescate", "evacuacion", "incendio", "riesgo", "epp",
            "extintor", "colapso", "hazmat", "brigada", "seguridad", "incidente",
            "emergencia", "desastre", "sismo", "inundacion", "derrame", "comando de incidentes",
        ],
        "subdomains": {
            "rescate": ["rescate", "extricacion", "busqueda", "localizacion", "rapido acceso"],
            "cuerdas": ["cuerda", "anclaje", "nudo", "rapel", "ascenso", "descenso", "linea de vida"],
            "evacuacion": ["evacuacion", "ruta de salida", "punto de reunion", "simulacro", "desalojo"],
            "incendios": ["incendio", "combustion", "extintor", "fuego", "humo", "triangulo del fuego"],
            "materiales_peligrosos": ["hazmat", "derrame", "quimico", "toxico", "reactivo", "contaminacion"],
            "seguridad_e_higiene": ["acto inseguro", "condicion insegura", "epp", "riesgo", "proteccion", "seguridad"],
            "gestion_de_riesgos": ["amenaza", "vulnerabilidad", "mitigacion", "prevencion", "riesgo", "atlas de riesgo"],
        },
    },
    "autosuficiencia": {
        "tipo": "existente",
        "aliases": ["autosuficiencia", "autonomia", "autonomia rural", "vida operativa"],
        "keywords": [
            "autosuficiencia", "huerto", "siembra", "semilla", "composta", "riego",
            "captacion de agua", "conservacion", "deshidratado", "estufa de lena",
            "corral", "cultivo", "germinacion", "fertilizante", "abono", "injerto",
            "almacenamiento", "fermentacion", "semillero", "bancal",
        ],
        "subdomains": {
            "siembra": ["siembra", "semilla", "germinacion", "trasplante", "surco", "almacigo", "semillero"],
            "cria_de_animales": ["cria", "gallina", "cabra", "conejo", "corral", "engorda", "forraje"],
            "captacion_de_agua": ["captacion", "cisterna", "tinaco", "filtro", "potabilizacion", "almacenamiento de agua"],
            "conservacion_de_alimentos": ["deshidratado", "conserva", "enlatado", "salmuera", "fermentado", "ahumado"],
            "estufas_de_lena": ["lena", "estufa", "chimenea", "combustion", "tiraje", "hornilla"],
            "huertos": ["huerto", "composta", "cultivo", "abonado", "riego", "mulch", "lombricomposta"],
        },
    },
    "instalacion_mantenimiento_reparacion": {
        "tipo": "existente",
        "aliases": ["instalacion_mantenimiento_reparacion", "instalacion", "mantenimiento", "reparacion", "tecnico"],
        "keywords": [
            "instalacion", "mantenimiento", "reparacion", "falla", "averia", "diagnostico",
            "cableado", "motor", "bateria", "alternador", "freno", "bomba", "voltaje",
            "corriente", "circuito", "breaker", "residencial", "automotriz", "mecanica",
            "panel solar", "fotovoltaico", "computadora", "herramienta", "lubricacion",
            "calibracion", "ajuste", "torque", "despiece",
        ],
        "subdomains": {
            "automovil": ["aceite", "motor", "bateria", "alternador", "frenos", "radiador", "suspension", "transmision"],
            "motocicleta": ["carburador", "cadena", "bujia", "embrague", "motosierra", "moto", "sprocket"],
            "residencial": ["enchufe", "apagador", "cableado", "voltaje", "centro de carga", "interruptor", "tuberia"],
            "herramientas": ["herramienta", "torque", "lubricacion", "afilado", "mantenimiento preventivo", "refaccion"],
            "equipos_medicos": ["monitor", "desfibrilador", "bomba de infusion", "sensor", "electrodo", "calibracion"],
            "electricidad": ["corriente", "voltaje", "resistencia", "conductor", "circuito", "breaker", "multimetro"],
            "electronica": ["transistor", "capacitor", "resistencia", "pcb", "microcontrolador", "soldadura", "fuente de poder"],
            "paneles_solares": ["panel solar", "fotovoltaico", "inversor", "controlador", "bateria", "regulador", "string"],
        },
    },
    "animales": {
        "tipo": "existente",
        "aliases": ["animales", "pecuario", "zootecnia"],
        "keywords": [
            "animal", "ganado", "vacuna animal", "desparasitacion", "sanidad animal",
            "corral", "forraje", "hidratacion", "engorda", "reproduccion", "veterinaria",
            "canino", "felino", "avicola", "bovino", "caprino", "porcino",
        ],
        "subdomains": {
            "perros": ["perro", "canino", "croqueta", "vacuna", "desparasitacion", "moquillo", "parvovirus"],
            "gallinas": ["gallina", "ponedora", "pollito", "alimento balanceado", "huevo", "incubacion"],
            "caprinos": ["cabra", "forraje", "rumiante", "caprino", "pezuña"],
            "bovinos": ["bovino", "ganado", "rumiante", "engorda", "leche", "mastitis"],
            "alimento": ["racion", "alimento", "consumo", "proteina", "minerales"],
            "agua": ["agua", "hidratacion", "consumo diario", "bebedero"],
            "sanidad": ["vacuna", "enfermedad", "patologia", "parasito", "desparasitar", "bioseguridad"],
            "reproduccion": ["celo", "gestacion", "reproduccion", "parto", "inseminacion"],
        },
    },
    "herbolaria": {
        "tipo": "posible",
        "aliases": ["herbolaria", "medicina tradicional", "plantas medicinales"],
        "keywords": [
            "herbolaria", "planta medicinal", "infusion", "decocto", "macerado", "cataplasma",
            "tintura", "extracto", "remedio natural", "hierba", "raiz", "hoja", "corteza",
            "dosis herbal", "preparacion tradicional", "fitoterapia",
        ],
        "subdomains": {
            "plantas_medicinales": ["manzanilla", "arnica", "romero", "gobernadora", "estafiate", "eucalipto"],
            "preparaciones": ["infusion", "decocto", "tintura", "pomada", "jarabe", "macerado"],
            "seguridad": ["toxicidad", "contraindicacion", "embarazo", "interaccion", "dosis"],
        },
    },
    "preparacionismo": {
        "tipo": "posible",
        "aliases": ["preparacionismo", "supervivencia", "supervivencialismo", "emergencia prolongada"],
        "keywords": [
            "preparacionismo", "supervivencia", "reserva", "kit", "mochila 72 horas",
            "bug out", "refugio", "racion", "agua de emergencia", "autonomia", "campamento",
            "filtrado", "purificacion", "fuego", "orientacion", "señalizacion",
        ],
        "subdomains": {
            "agua": ["filtro", "purificacion", "potabilizacion", "tabletas potabilizadoras"],
            "alimentos": ["racion", "reserva", "calorias", "conserva", "deshidratado"],
            "refugio": ["lona", "refugio", "aislamiento", "abrigo", "vivac"],
            "fuego": ["encendido", "yesca", "estufa", "hornillo", "combustible"],
        },
    },
    "campismo": {
        "tipo": "posible",
        "aliases": ["campismo", "camping", "excursionismo", "senderismo"],
        "keywords": [
            "campismo", "camping", "tienda", "mochila", "vivac", "hornillo", "linterna",
            "sleeping", "senderismo", "trekking", "brujula", "mapa", "nudos", "fogata",
            "equipo de campamento", "aislante", "botiquin de campo",
        ],
        "subdomains": {
            "equipo": ["tienda", "sleeping", "aislante", "linterna", "mochila", "hornillo"],
            "orientacion": ["brujula", "mapa", "coordenadas", "ruta", "sendero"],
            "seguridad": ["hipotermia", "lluvia", "tormenta", "animales", "seguridad en campo"],
        },
    },
    "veterinaria": {
        "tipo": "posible",
        "aliases": ["veterinaria", "medicina veterinaria", "veterinario"],
        "keywords": [
            "veterinaria", "animal enfermo", "dosis veterinaria", "parasitos", "zoonosis",
            "vacunacion animal", "ganado enfermo", "mastitis", "distocia", "desparasitante",
        ],
        "subdomains": {
            "pequenas_especies": ["perro", "gato", "canino", "felino"],
            "grandes_especies": ["bovino", "equino", "caprino", "ovino", "porcino"],
            "avicultura": ["gallina", "pollo", "ponedora", "parvada"],
        },
    },
    "siembra": {
        "tipo": "posible",
        "aliases": ["siembra", "agricultura", "agro"],
        "keywords": [
            "siembra", "cultivo", "semilla", "germinacion", "trasplante", "fertilizacion",
            "riego", "plaga", "suelo", "abonado", "composta", "insecticida", "fungicida",
            "caldo bordeles", "mulch", "bancal", "hidroponia",
        ],
        "subdomains": {
            "hortalizas": ["jitomate", "chile", "lechuga", "cebolla", "zanahoria"],
            "frutales": ["injerto", "poda", "frutal", "citricos", "manzano", "durazno"],
            "suelo_y_nutricion": ["ph", "composta", "lombricomposta", "abonado", "fertilizante"],
            "plagas_y_enfermedades": ["plaga", "hongo", "roya", "mildiu", "insecto", "control biologico"],
        },
    },
    "vehiculos": {
        "tipo": "posible",
        "aliases": ["vehiculos", "vehiculo", "automotriz", "transporte"],
        "keywords": [
            "vehiculo", "motor", "transmision", "suspension", "frenos", "alternador",
            "radiador", "bateria", "llanta", "sensor", "scanner", "carburador",
            "inyeccion", "sistema electrico", "codigo de falla", "motosierra",
        ],
        "subdomains": {
            "automovil": ["automovil", "coche", "camioneta", "alternador", "radiador"],
            "motocicleta": ["motocicleta", "bujia", "cadena", "embrague", "carburador"],
            "maquinaria_ligera": ["desbrozadora", "motosierra", "generador", "bomba de agua"],
        },
    },
    "construccion": {
        "tipo": "posible",
        "aliases": ["construccion", "obra", "albanileria", "albañileria"],
        "keywords": [
            "construccion", "obra", "cemento", "mortero", "concreto", "varilla", "cimbra",
            "nivel", "muro", "columna", "castillo", "losa", "plomo", "arena", "grava",
            "tabique", "block", "cimientos", "impermeabilizacion",
        ],
        "subdomains": {
            "albanileria": ["cemento", "mortero", "tabique", "block", "aplanado", "emboquillado"],
            "estructuras": ["cadena", "castillo", "columna", "viga", "losa", "cimentacion"],
            "acabados": ["yeso", "pintura", "impermeabilizante", "sellador", "loseta"],
            "instalaciones": ["hidraulica", "sanitaria", "electrica", "tuberia", "registro"],
        },
    },
    "agua_saneamiento": {
        "tipo": "posible",
        "aliases": ["agua_saneamiento", "agua", "saneamiento"],
        "keywords": [
            "agua", "potabilizacion", "filtro", "cloracion", "desinfeccion", "cisterna",
            "tinaco", "bomba", "tuberia", "drenaje", "fosa septica", "saneamiento",
            "captacion pluvial", "lavado de tanque",
        ],
        "subdomains": {
            "potabilizacion": ["cloro", "ebullicion", "filtro", "potabilizar", "sedimentos"],
            "almacenamiento": ["cisterna", "tinaco", "bidon", "almacenamiento"],
            "distribucion": ["bomba", "presion", "tuberia", "valvula", "llave"],
        },
    },
}


def catalogo_patrones_inferencia(include_possible: bool = True) -> Dict[str, List[str]]:
    patrones: Dict[str, List[str]] = {}
    for dominio, data in CATALOGO_DOMINIOS.items():
        if not include_possible and str(data.get("tipo", "")) != "existente":
            continue
        lista: List[str] = []
        lista.extend([str(x).strip() for x in data.get("aliases", []) if str(x).strip()])
        lista.extend([str(x).strip() for x in data.get("keywords", []) if str(x).strip()])
        for palabras in data.get("subdomains", {}).values():
            lista.extend([str(x).strip() for x in palabras if str(x).strip()])
        unicas: List[str] = []
        vistos = set()
        for item in lista:
            clave = item.lower()
            if clave in vistos:
                continue
            vistos.add(clave)
            unicas.append(item)
        patrones[dominio] = unicas
    return patrones


def catalogo_subdominios_existentes() -> Dict[str, Dict[str, List[str]]]:
    salida: Dict[str, Dict[str, List[str]]] = {}
    for dominio, data in CATALOGO_DOMINIOS.items():
        if str(data.get("tipo", "")) != "existente":
            continue
        salida[dominio] = {
            str(subdominio): [str(p).strip() for p in palabras if str(p).strip()]
            for subdominio, palabras in data.get("subdomains", {}).items()
        }
    return salida


DOMINIOS_OPERATIVOS = {
    "medica",
    "proteccion_civil",
    "autosuficiencia",
    "instalacion_mantenimiento_reparacion",
    "animales",
}


MAPEO_DOMINIO_OPERATIVO = {
    "medica": "medica",
    "proteccion_civil": "proteccion_civil",
    "autosuficiencia": "autosuficiencia",
    "instalacion_mantenimiento_reparacion": "instalacion_mantenimiento_reparacion",
    "animales": "animales",
    "herbolaria": "medica",
    "preparacionismo": "autosuficiencia",
    "campismo": "autosuficiencia",
    "veterinaria": "animales",
    "siembra": "autosuficiencia",
    "vehiculos": "instalacion_mantenimiento_reparacion",
    "construccion": "instalacion_mantenimiento_reparacion",
    "agua_saneamiento": "instalacion_mantenimiento_reparacion",
}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto or ""))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower().replace("_", " ")
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def inferir_dominio_desde_texto(texto: str, include_possible: bool = True) -> Dict[str, object]:
    consulta = _normalizar(texto)
    if not consulta:
        return {"domain": "", "operational_domain": "", "score": 0.0, "matched_terms": [], "type": ""}

    mejor_dominio = ""
    mejor_score = 0.0
    mejores_terminos: List[str] = []
    mejor_tipo = ""

    for dominio, data in CATALOGO_DOMINIOS.items():
        if not include_possible and str(data.get("tipo", "")) != "existente":
            continue

        score = 0.0
        terminos: List[str] = []
        for alias in data.get("aliases", []):
            alias_n = _normalizar(str(alias))
            if alias_n and alias_n in consulta:
                score += 4.0
                terminos.append(str(alias))

        for keyword in data.get("keywords", []):
            keyword_n = _normalizar(str(keyword))
            if keyword_n and keyword_n in consulta:
                score += 2.0
                terminos.append(str(keyword))

        for palabras in data.get("subdomains", {}).values():
            for termino in palabras:
                termino_n = _normalizar(str(termino))
                if termino_n and termino_n in consulta:
                    score += 2.5
                    terminos.append(str(termino))

        if score > mejor_score:
            mejor_dominio = dominio
            mejor_score = score
            mejores_terminos = terminos[:8]
            mejor_tipo = str(data.get("tipo", ""))

    if not mejor_dominio or mejor_score <= 0:
        return {"domain": "", "operational_domain": "", "score": 0.0, "matched_terms": [], "type": ""}

    return {
        "domain": mejor_dominio,
        "operational_domain": MAPEO_DOMINIO_OPERATIVO.get(mejor_dominio, mejor_dominio),
        "score": round(mejor_score, 2),
        "matched_terms": mejores_terminos,
        "type": mejor_tipo,
    }
