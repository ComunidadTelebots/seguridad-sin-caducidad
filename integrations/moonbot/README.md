# Verificación de votos de Right to Updates

Esta ampliación añade `plugins/right_to_updates.py` a Moonbot y una ruta para
`/start rtu_<código>` antes del menú de CintiaBot. El resto de comandos, menús y
plugins permanece intacto. Moonbot mantiene su único consumidor de actualizaciones
de Telegram: no se inicia otro polling ni se cambia su webhook.

## Flujo

1. En la web se eligen país y tecnología y se pulsa «Verificar mi voto por Telegram».
2. La API crea un desafío aleatorio válido durante 15 minutos, sin sumar votos.
3. El enlace abre `@cintiabot`. El plugin consulta el desafío mediante la API interna
   y lo vincula al usuario que abrió el enlace, solo en chat privado.
4. Moonbot envía el resumen y un botón de confirmación usando su `bot.api_call` actual.
   El token cifrado de Telegram nunca se copia a la web.
5. Al confirmar, la API comprueba usuario, bot, caducidad y duplicados, guarda el voto
   y actualiza los agregados. La web consulta el resultado automáticamente.

Un desafío no puede ser confirmado por otra cuenta. Repetir la confirmación es
idempotente. Cada cuenta de Telegram aporta un solo voto, incluso con otro enlace.
Correo y Telegram son identidades independientes: no se puede deducir que pertenecen
a la misma persona, por lo que no se garantiza la deduplicación entre ambos canales.
La verificación acredita el control de una cuenta Telegram, no identidad civil,
residencia ni elegibilidad para una ICE.

## Configuración

La instalación local está preparada para `@cintiabot` y la API `http://127.0.0.1:8080`.
El archivo privado de Moonbot es `data/right_to_updates_bridge.json`; el de la web
es `.local/moonbot.json`. Ambos comparten estos campos:

```json
{
  "bot_username": "cintiabot",
  "api_url": "http://127.0.0.1:8080",
  "secret": "GENERAR_UN_SECRETO_ALEATORIO_DE_AL_MENOS_32_CARACTERES"
}
```

Se ha generado una clave de integración independiente para el entorno local.
Ambos archivos están excluidos de Git. `RTU_BRIDGE_CONFIG` permite cambiar la ruta.
No incluir aquí el token de Telegram. La integración reutiliza la instancia de bot
que Moonbot ya haya autenticado. Reiniciar/re cargar Moonbot para cargar el plugin
y la ruta nueva; no iniciar una segunda instancia con el token del bot activo.

## Despliegue

Los cambios están en los repositorios locales; no despliegan automáticamente los
servicios públicos. Si Moonbot vive en otra máquina, su `api_url` debe apuntar a
la API accesible por HTTPS, no a localhost. La API pública debe implementar las
rutas de `moonbot_bridge.py`, usar almacenamiento persistente y el mismo secreto:

- `GET /api/telegram/config`: solo estado y nombre público del bot.
- `POST /api/telegram/challenge`: país y tecnología; devuelve el enlace.
- `POST /api/telegram/status`: código; devuelve solo el estado.
- `POST /api/moonbot/prepare` y `/confirm`: requieren `Authorization: Bearer <secret>`;
  reciben código, ID de usuario obtenido por Moonbot y nombre del bot.

El servidor Python local es una herramienta de desarrollo; el Nginx existente
no ejecuta estas rutas. Para producción, incorporar el contrato al backend público
o servir el backend apropiado detrás del proxy, con límite de peticiones y HTTPS.
Mantener las claves solo en servidores. Ningún endpoint acepta tokens Telegram
o confía en un ID de usuario enviado por el navegador.

Documentación utilizada: [enlaces de inicio de Telegram](https://core.telegram.org/bots/features#deep-linking)
y [Bot API](https://core.telegram.org/bots/api#callbackquery).
