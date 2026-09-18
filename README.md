# Right to Updates — Iniciativa Ciudadana Europea

Campaña para reconocer el derecho de los ciudadanos europeos a recibir
actualizaciones de seguridad para sus dispositivos conectados.

## Versiones

- **v1** (`web/index.html` en el commit `v1-es`): landing original en español con GA4.
- **v2** (`web/index.html` actual): versión multiidioma con los 24 idiomas oficiales
  de la UE, con GA4.

## Enlace oficial

<https://righttoupdates.eu>

> **Aviso:** Las traducciones de lenguas minoritarias no han sido revisadas
> por hablantes nativos. Pueden contener errores.

## Desarrollo local: mapa y apoyos a tecnologías

La integración adicional con **Moonbot / @cintiabot** está documentada en
[integrations/moonbot/README.md](integrations/moonbot/README.md). Añade votos
confirmados por Telegram al mismo mapa, conservando el formulario de correo.

Con Python 3.11 o posterior, sin dependencias adicionales:

```sh
python server.py --port 8080
```

Abre `http://127.0.0.1:8080/?lang=es#community`. El servidor sirve `web/` y una
API local. Los apoyos se guardan en `.local/supports.sqlite3`, excluido de Git.
No utiliza los apoyos de producción ni envía correos. El email se normaliza y se
almacena como hash para evitar duplicados; no es un sistema de identidad verificada.
El servidor solo escucha en la interfaz local: es una herramienta de desarrollo.

El mapa muestra los 27 países de la UE, sus apoyos registrados y el total europeo.
Cada alta permite elegir una de las 38 tecnologías del catálogo. Una persona
cuenta una vez en el total, en su país y, si la ha elegido, en una tecnología.
Un correo ya registrado no crea votos adicionales ni modifica el voto anterior.
Las cifras son apoyos de campaña, no firmas oficiales ni emails verificados.
La interfaz nueva está traducida al español e inglés (inglés como alternativa
para los demás idiomas); los nombres de los países se localizan con `Intl`.

Pruebas de validación, duplicados, persistencia y recuentos con base temporal:

```sh
python -m unittest test_server.py -v
node --check web/community.js
```

### Conexión a producción pendiente

El despliegue Nginx existente solo sirve archivos; **no ejecuta `server.py`**.
En dominios públicos se conserva `https://data.righttoupdates.eu` como API.
Para activar mapa y votos en producción hay que adaptar ese servicio PocketBase:

- Mantener `POST /api/collections/supports/records` y aceptar un campo opcional
  `technology`, validado contra los identificadores de `web/technologies.json`.
  Conservar la unicidad del correo y validar país y tecnología en el servidor.
- Añadir `GET /api/community/stats` que solo devuelva agregados públicos. Nunca
  hacer pública la colección de correos para calcular las cifras en el navegador.
- Devolver un objeto con `mode: "production"`, `total` (entero), `countries`
  (27 códigos ISO de dos letras y sus recuentos), `technologies` (todos los IDs
  del catálogo y sus recuentos), y `technologyVoting: true` solo cuando las altas
  realmente persistan la tecnología. Incluir ceros explícitos. El total debe
  coincidir con la suma de países. Contar apoyos registrados, coherente con las etiquetas.
- Configurar CORS para el dominio de la web y conservar las medidas de validación,
  confirmación y protección contra abuso del servicio de producción.

Sin ese endpoint, se muestran datos no disponibles y se impide enviar una
tecnología para evitar aparentar que se guardó un campo que el backend ignora.
El apoyo general existente permanece disponible. `?api=...` permite apuntar
explícitamente a un backend de pruebas compatible.

### Cartografía

`web/europe.geojson` contiene contornos simplificados de Natural Earth mediante
[datasets/geo-countries](https://github.com/datasets/geo-countries), datos de
dominio público. Se han filtrado los 27 países de la UE y los territorios fuera
del encuadre europeo. Malta, Luxemburgo y Chipre tienen marcadores para facilitar
su selección. El mapa funciona sin cargar bibliotecas ni mapas de terceros.
