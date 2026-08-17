# Radar MP — Monitor de Compra Ágil (Mercado Público Chile)

Proyecto completo: PWA + backend Python + GitHub Actions que busca Compra
Ágil por palabras clave, calcula un termómetro de probabilidad, y corre
solo cada hora entre 08:00 y 20:00 hora Chile. Repo real de referencia:
https://github.com/msanmart1n/Radas_MP

## Estructura

```
index.html                    -> PWA (dashboard), fetch a reporte.json
mp_client.py                  -> backend: busca, scorea, genera reporte.json
keywords.txt                  -> palabras clave, editable sin tocar codigo
manifest.json + icon-*.png    -> para "Agregar a inicio" en iPhone
.github/workflows/radar.yml   -> cron que corre el backend solo
README.md                     -> este archivo
```

## Cosas aprendidas sobre las APIs de Mercado Publico (utiles para otros proyectos)

**Hay DOS APIs distintas, no confundir:**

1. `api.mercadopublico.cl` (v1) — Licitaciones y Ordenes de Compra "normales".
   - Ticket va como **parametro de URL**: `?ticket=XXX`
   - Fecha en formato `ddmmaaaa` (ej. `16082026`)
   - El endpoint por fecha NO trae organismo/monto/rubro -- hay que hacer
     un segundo llamado por `?codigo=X` para el detalle completo.
   - Ticket publico de pruebas (solo para probar formatos, no para produccion):
     `F8537A18-6766-4DEF-9E59-426B4FEE2844`

2. `api2.mercadopublico.cl` (v2) — Compra Agil (version Beta, lanzada
   mayo 2026). API distinta y mas moderna.
   - Ticket va como **header HTTP**: `-H "ticket: XXX"`, no como parametro.
   - Busqueda por palabra clave (`q=`) y rango de fechas
     (`publicado_desde`, `publicado_hasta` en formato ISO
     `2026-08-09T00:00:00Z`) ya vienen incluidos, no hay que armarlos a mano.
   - `tamano_pagina` debe estar entre 10 y 50 (no acepta menos de 10).
   - **Esta API es beta y tira errores 500 sin motivo aparente con
     cierta frecuencia** (confirmado en la consulta ciudadana de
     ChileCompra, no es un bug de tu codigo). Por eso el script
     reintenta 3 veces con espera antes de rendirse, y si una keyword
     falla igual, sigue con las demas en vez de morir.
   - **La busqueda `q=` es "difusa"**: puede traer resultados que no
     contienen literalmente la palabra buscada. Por eso el script
     filtra de nuevo del lado nuestro, exigiendo que la keyword
     aparezca literal en el titulo antes de aceptarlo.
   - Evitar keywords demasiado genericas de una sola palabra corta
     (ej. "foto", "geo", "mapa" solas) -- traen ruido real aunque el
     filtro este funcionando bien, porque esas palabras aparecen en
     contextos no relacionados (fotocopias, fotos adjuntas, etc).
     Mejor usar compuestos especificos: "fotogrametria",
     "georreferencia", etc.

## Debug rapido con curl (sirve para cualquier proyecto futuro)

Para probar la API v2 directo, sin pasar por Python:

```bash
curl -s -H "ticket: TU_TICKET" "https://api2.mercadopublico.cl/v2/compra-agil?q=PALABRA&estado=publicada&tamano_pagina=10&numero_pagina=1"
```

Util para aislar si un error es de parametros (400), del servidor (500,
suele ser transitorio) o de autenticacion (401/403).

## Notas de despliegue (GitHub)

- El **ticket nunca va en el codigo ni en la pagina** (GitHub Pages es
  publica) -- se guarda como Secret: Settings -> Secrets and variables
  -> Actions -> `MP_TICKET`.
- La carpeta `.github` empieza con punto y el Finder de Mac la esconde
  por defecto -- si subes archivos arrastrando desde Finder, revisa que
  se haya incluido, o creala directo desde la web de GitHub
  ("Add file" -> escribir la ruta completa `.github/workflows/x.yml`).
- Si un workflow da error de permisos raro en tu Mac local (`Operation
  not permitted` al ejecutar/editar), casi siempre es porque la carpeta
  esta en Escritorio/Documentos/Descargas y macOS restringe el acceso
  de Terminal ahi por defecto. Se arregla en Ajustes del Sistema ->
  Privacidad y Seguridad -> Carpetas y Archivos (o Acceso total al
  disco) -- o mas simple, trabajar en una carpeta dentro de `~` directo
  (ej. `~/mi-proyecto`), que no tiene esa restriccion.
- TextEdit en Mac reemplaza comillas rectas `"` por comillas curvas
  cuando escribes texto nuevo ahi ("comillas inteligentes"), lo que
  rompe cualquier archivo de codigo. Desactivar en TextEdit -> Ajustes
  -> Nuevo Documento, o mejor editar codigo con el editor web de GitHub.

## Proximos pasos pendientes (si se retoma)

- Calibrar `calcular_probabilidad()` en `mp_client.py` con historial
  real de compras ganadas/perdidas (hoy es un modelo de reglas simple).
- Si la cantidad de keywords crece mucho, revisar cuota diaria de la
  API (no deberia ser problema con uso normal).
