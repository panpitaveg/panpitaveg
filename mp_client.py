"""
mp_client.py - Backend Radar MP para Compra Agil (api2.mercadopublico.cl)

Para cambiar las palabras clave: edita keywords.txt (una por linea), no este archivo.
El ticket se lee de la variable de entorno MP_TICKET (configurada como Secret en GitHub).
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta

TICKET = os.environ.get("MP_TICKET", "").strip()
DIAS_ATRAS = 7
BASE_URL = "https://api2.mercadopublico.cl"


def cargar_keywords():
    with open("keywords.txt", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _get(path, params, intentos=3):
    """La API de Compra Agil esta en beta y a veces tira 500 sin motivo.
    Reintenta con espera antes de rendirse."""
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"ticket": TICKET, "User-Agent": "RadarMP/1.0"})
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code >= 500 and intento < intentos:
                print(f"  ! HTTP {e.code} (intento {intento}/{intentos}), reintentando...")
                time.sleep(3 * intento)
                continue
            raise


def buscar_por_keyword(keyword, desde, hasta, max_paginas=5):
    """Busca hasta max_paginas por keyword (50 resultados x pagina = 250 max).
    Si falla despues de reintentar, avisa y sigue con la siguiente keyword
    en vez de tirar abajo todo el reporte."""
    items, pagina = [], 1
    while pagina <= max_paginas:
        try:
            data = _get("/v2/compra-agil", {
                "q": keyword, "estado": "publicada",
                "publicado_desde": desde, "publicado_hasta": hasta,
                "tamano_pagina": 50, "numero_pagina": pagina,
            })
        except Exception as e:
            print(f"  ! No se pudo buscar '{keyword}' (pagina {pagina}): {e}")
            break
        if data.get("success") != "OK":
            err = (data.get("errors") or [{}])[0]
            print(f"  ! Error buscando '{keyword}': {err.get('mensaje')}")
            break
        payload = data["payload"]
        for item in payload["items"]:
            item["_keyword"] = keyword
            items.append(item)
        pag = payload["paginacion"]
        if pag["numero_pagina"] >= pag["total_paginas"]:
            break
        pagina += 1
    return items


def buscar_licitaciones(momento, keywords):
    ahora = datetime.now(timezone.utc)
    desde = (ahora - timedelta(days=DIAS_ATRAS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hasta = ahora.strftime("%Y-%m-%dT%H:%M:%SZ")

    vistos = {}
    for kw in keywords:
        for item in buscar_por_keyword(kw, desde, hasta):
            nombre = item.get("nombre", "")
            if kw.lower() not in nombre.lower():
                continue
            if item["codigo"] not in vistos:
                vistos[item["codigo"]] = item

    resultados = []
    for item in vistos.values():
        fecha_cierre = item.get("fechas", {}).get("fecha_cierre")
        dias = 0
        if fecha_cierre:
            try:
                dt_cierre = datetime.fromisoformat(fecha_cierre.replace("Z", "+00:00"))
                if dt_cierre.tzinfo is None:
                    dt_cierre = dt_cierre.replace(tzinfo=timezone.utc)
                dias = max(0, (dt_cierre - ahora).days)
            except ValueError:
                pass

        resultados.append({
            "codigo": item["codigo"],
            "org": item.get("institucion", {}).get("organismo_comprador", "Organismo no informado"),
            "titulo": item.get("nombre", ""),
            "monto": item.get("montos", {}).get("monto_disponible_clp") or 0,
            "dias": dias,
            "cierre": (fecha_cierre or "")[:10],
            "keyword": item.get("_keyword", ""),
            "ofertas_actuales": item.get("resumen", {}).get("total_ofertas_recibidas", 0),
            "region": item.get("institucion", {}).get("nombre_region", ""),
            "momento": momento,
        })
    return resultados


def calcular_probabilidad(l):
    score = 45
    score += min(l["dias"], 10) * 2
    score -= min(l["ofertas_actuales"], 8) * 5
    if 300_000 <= l["monto"] <= 15_000_000:
        score += 10
    elif l["monto"] > 15_000_000:
        score -= 5
    return max(6, min(94, round(score)))


def generar_reporte(momento):
    if not TICKET:
        print("ERROR: no encontre el ticket. Revisa el Secret MP_TICKET en GitHub.")
        sys.exit(1)

    keywords = cargar_keywords()
    items = buscar_licitaciones(momento, keywords)
    for l in items:
        l["probabilidad"] = calcular_probabilidad(l)
    items.sort(key=lambda l: l["probabilidad"], reverse=True)

    reporte = {
        "momento": momento,
        "generado": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "keywords": keywords,
        "dias_atras": DIAS_ATRAS,
        "licitaciones": items,
    }
    with open("reporte.json", "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    print(f"Reporte '{momento}' generado con {len(items)} compras agiles -> reporte.json")
    return reporte


if __name__ == "__main__":
    momento = sys.argv[1] if len(sys.argv) > 1 else "am"
    if momento not in ("am", "mediodia", "pm"):
        print("Uso: python3 mp_client.py [am|mediodia|pm]")
        sys.exit(1)
    generar_reporte(momento)
