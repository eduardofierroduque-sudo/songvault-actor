# SongVault

## Suno Music Backup and Downloader

Descarga todas tus canciones de Suno AI automaticamente en MP3 o WAV, con caratula, letras y metadatos incluidos. Ideal para respaldar tu libreria completa antes de limpiar tu cuenta.

---

## Funciones

| Funcion | Descripcion |
|---------|-------------|
| Descarga masiva | Todas tus canciones sin limite |
| Formato MP3 o WAV | Elige rapidez o maxima calidad |
| Metadatos ID3 | Caratula, titulo, artista, genero incrustados en el MP3 |
| Letra y estilo | Archivo .txt por cancion con letra y tags |
| Organizacion | Separado por workspaces automaticamente |
| Limpieza opcional | Elimina de Suno tras descargar |
| Reanudable | Canciones ya descargadas se omiten |

## Como usar

### 1. Obtener el token

1. Ingresa a suno.com y asegurate de estar logueado
2. Presiona F12 y ve a la pestana Network (Red)
3. Recarga la pagina con F5
4. Escribe "feed" en el filtro de busqueda
5. Selecciona el request POST llamado "v3"
6. En Request Headers busca el campo Authorization con valor "Bearer ey..."
7. Copia solo la parte despues de "Bearer " (el string que comienza con ey...)

### 2. Configurar el actor

| Campo | Descripcion |
|-------|-------------|
| Token | El token que copiaste de Suno |
| Formato | MP3 (rapido, recomendado) o WAV (mayor calidad, conversion lenta) |
| Modo | Todas las canciones, solo un workspace, o 5 de prueba |
| Incluir metadatos | Guarda .txt con letras y .json con metadata completa |
| Eliminar tras descarga | Envia las canciones a la papelera de Suno al terminar |

### 3. Ejecutar

Los archivos MP3 o WAV apareceran en el Key-Value Store del actor, organizados por workspace.

## Estructura de salida

```
output/
  My Workspace/
    NombreCancion__abc12345.mp3
    NombreCancion__abc12345.jpeg
    NombreCancion__abc12345.txt
    NombreCancion__abc12345.json
  Otro Workspace/
    ...
  _library_all/
    ...
```

## Precios sugeridos

| Plan | Precio | Limite |
|------|--------|--------|
| Gratis | $0 | 10 canciones de prueba |
| Basico | $9.99/mes | 500 canciones/mes |
| Pro | $19.99/mes | 5000 canciones/mes |
| Ilimitado | $49.99/mes | Sin limite + formato WAV |

## Notas importantes

- El token de Suno expira cada 6 horas aproximadamente. Si el actor reporta error 401, obten un token nuevo y vuelve a ejecutar.
- El formato WAV requiere conversion por parte de Suno, lo que hace el proceso significativamente mas lento que MP3.
- La opcion de eliminar canciones las envia a la papelera de Suno (no es destruccion permanente).
- No compartas tu token con nadie. Da acceso completo a tu cuenta de Suno.

## Stack tecnologico

- Python 3.12
- Apify SDK
- Suno API (studio-api.prod.suno.com)
- mutagen para metadatos ID3

---

*SongVault no esta afiliado con Suno Inc. Es una herramienta independiente para respaldar tu contenido.*
