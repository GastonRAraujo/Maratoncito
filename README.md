# Maratoncito
App web autoalojada para pedir, buscar y descargar películas y series por torrent, con perfiles de audio y subtítulos y grupos de release preferidos por temporada.

## Arranque local

Requiere Docker con el plugin Compose. Desde la Raspberry Pi o tu equipo de desarrollo:

```sh
cp .env.example .env
docker compose up --build -d
curl --fail http://127.0.0.1:8000/health
```

La respuesta esperada es `{"status":"ok"}`. Esta base implementa el endpoint de salud.

El puerto queda publicado en localhost. Para acceder desde otro equipo de tu red, configurá `MARATONCITO_BIND_HOST` con la IP local de la Pi en `.env`. Cambiá `MARATONCITO_PORT` si el 8000 ya está ocupado.

Para detener el servicio:

```sh
docker compose down
```
