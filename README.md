# SongVault 🎵

## Suno Music Backup & Downloader

Descarga **todas** tus canciones de Suno AI automaticamente. MP3 o WAV, con caratula, letras y metadatos. Ideal para respaldar tu libreria antes de limpiar tu cuenta.

---

## ✨ Que hace

| Funcion | Descripcion |
|---------|-------------|
| **Descarga masiva** | Todas tus canciones, sin limite |
| **MP3 o WAV** | Elige formato estandar o alta calidad |
| **Metadatos** | Caratula, titulo, artista, genero incrustados en el MP3 |
| **Letras + Tags** | Archivo .txt por cancion con letra y estilo |
| **Workspaces** | Organizado en carpetas por workspace |
| **Limpieza opcional** | Elimina de Suno tras descargar |
| **Reanudable** | Canciones ya descargadas se saltan |

## 🚀 Como usar

### 1. Obtén tu token

1. Ve a [suno.com](https://suno.com) y **logueate**
2. Presiona **F12** → pestaña **Network** (Red)
3. **F5** para recargar
4. Filtra por `feed`
5. Clic al request **POST** `v3`
6. En **Request Headers** → `Authorization: Bearer ey...`
7. **Copia** solo el string despues de `Bearer `

### 2. Configura el Actor

| Campo | Descripcion |
|-------|-------------|
| **Token** | Pega tu token de Suno |
| **Formato** | MP3 (rapido) o WAV (calidad, mas lento) |
| **Modo** | Todas, un workspace, o 5 de prueba |
| **Incluir metadatos** | .txt con letras + .json con metadata |
| **Eliminar tras descarga** | Opcional: envia a papelera de Suno |

### 3. Ejecuta y recibe tus archivos

Los MP3/WAV apareceran en el **Key-Value Store** del Actor, organizados por workspace.

## 📁 Estructura de salida

```
SongVault_Store/
├── My Workspace/
│   ├── NombreCancion__abc12345.mp3
│   ├── NombreCancion__abc12345.jpeg
│   ├── NombreCancion__abc12345.txt
│   └── NombreCancion__abc12345.json
├── Otro Workspace/
│   └── ...
└── _library_all/
    └── ...
```

## 💰 Precios sugeridos (Apify Store)

| Plan | Precio | Limite |
|------|--------|--------|
| **Gratis** | $0 | 10 canciones de prueba |
| **Basico** | $9.99/mes | 500 canciones/mes |
| **Pro** | $19.99/mes | 5000 canciones/mes |
| **Ilimitado** | $49.99/mes | Sin limite + WAV |

## ⚠️ Notas

- El token expira cada ~6 horas. Si ves error 401, obten uno nuevo.
- WAV tarda mas porque Suno debe convertir cada cancion.
- Las canciones van a la **papelera** de Suno (no destruccion permanente).
- No compartas tu token con nadie.

## 🔧 Stack tecnico

- Python 3.12
- Apify SDK
- Suno API (studio-api.prod.suno.com)
- mutagen (tags ID3)

---

*SongVault no esta afiliado con Suno Inc. Es una herramienta independiente para respaldar tu contenido.*
