# Moda Urbana

Sitio web de prácticas para el módulo de Ciberseguridad, posicionamiento e IA en la web (DAW2).

## Puesta en marcha

Requiere Docker con Compose.

```bash
docker compose up -d
```

Añade esta línea al fichero `hosts` de tu equipo (como administrador / con `sudo`):

```
127.0.0.1   www.modaurbana.test
```

y abre `http://www.modaurbana.test/`. Si el puerto 80 está ocupado, cambia `"80:80"` por `"8080:80"` en `docker-compose.yml` y usa `http://www.modaurbana.test:8080/`.

Para pararlo: `docker compose down`.

## Rastreador

`rastrear.py` es un rastreador sencillo en Python 3 (sin dependencias) para la práctica 4.1.
Es una herramienta casera: no sustituye a un rastreador profesional.

```bash
python rastrear.py http://www.modaurbana.test/ --salida rastreo.csv
```
