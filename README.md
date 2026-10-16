<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./generated/profile-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./generated/profile-light.svg">
  <img src="./generated/profile-dark.svg" alt="Card de GitHub de Gonzalo Mayorga, con avatar pixelado y estadísticas" width="100%">
</picture>

# GitHub Profile Card · v1.0.0

Generador de una card SVG inspirada en terminal/neofetch para un GitHub Profile README. Combina tus datos de `profile.toml`, un avatar pixelado y estadísticas de GitHub. Genera temas dark y light; GitHub Actions puede actualizar los archivos automáticamente, sin servidor propio.

La imagen de arriba es la demo real: [`profile-dark.svg`](generated/profile-dark.svg) y [`profile-light.svg`](generated/profile-light.svg).

## Requisitos e instalación

- Git y Python 3.11 o posterior; CI prueba 3.11 y 3.13 en Linux. Python 3.13 es la referencia de uso.
- Acceso a internet para GitHub y, en el primer uso de eliminación de fondo, para descargar el modelo u2net (~176 MB).
- Dependencias CPU de `rembg`/ONNX disponibles para tu plataforma. Se instalan con el proyecto; no hace falta GPU.

La vía soportada es un clon con instalación editable. Ejecutá desde la raíz del repositorio:

```bash
git clone https://github.com/GonzaloMayorga/GonzaloMayorga.git
cd GonzaloMayorga
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

En Windows, creá el entorno con `py -3 -m venv .venv` y activalo en PowerShell con `.venv\Scripts\Activate.ps1`. Para trabajar sobre tu propio fork, reemplazá la URL de clonación.

## Configuración

Editá `profile.toml`. Este ejemplo completo tiene LOC desactivado:

```toml
[profile]
username = "TU_USUARIO"
name = "Tu nombre"
role = "Software Engineer"
location = "Tu ciudad"

[system]
os = ["Debian", "Windows"]

[skills]
languages = ["Python", "TypeScript"]
backend = []
frontend = ["React"]
tools = ["Git", "Docker"]

[avatar]
width = 96
gamma = 0.9
remove_background = true

[metrics.loc]
enabled = false
include_forks = false
exclude_repositories = []
```

Reemplazá `TU_USUARIO` por un login real antes de ejecutar. `profile.username` y `profile.name` deben ser strings no vacíos; `role` y `location` deben existir, pero pueden quedar vacíos. Las secciones `system` y `skills`, con las claves del ejemplo, son obligatorias; sus listas pueden estar vacías.

`avatar` es opcional: los valores por defecto son ancho 26, gamma 0.9 y eliminación de fondo activada. El ancho admite enteros de 8 a 96; gamma admite números finitos entre 0.1 y 3. El máximo de ancho evita superponer el avatar con las estadísticas en el diseño fijo de 900 × 500. Usá textos breves: no hay ajuste automático de líneas largas.

La v1 siempre dibuja píxeles SVG de 3 × 3. Las antiguas opciones `avatar.style` y `avatar.pixel_size` no cambiaban el resultado y deben quitarse; si siguen presentes, se informa un error de configuración. Los caracteres `&`, `<`, `>`, comillas y Unicode se muestran como texto, sin convertirse en markup.

El `profile.toml` de este repositorio conserva los datos de Gonzalo y LOC habilitado. Si lo reutilizás, cambiá esos datos y elegí explícitamente si querés LOC. Si omitís `metrics.loc.enabled`, LOC queda desactivado.

## Token y generación local

Sin token se pueden consultar las estadísticas REST públicas. Commits y contributions requieren autenticación GraphQL.

Para configurar una credencial local:

```bash
cp .env.example .env
```

Editá `.env` y completá `GITHUB_TOKEN=` con tu token. El archivo está ignorado por Git. También podés definir `GITHUB_TOKEN` en el entorno; el entorno tiene prioridad sobre `.env`, incluso si el valor está vacío. El lector admite asignaciones simples, comillas opcionales, prefijo `export` y comentarios en líneas separadas; no expande variables ni comentarios al final del valor.

Usá un personal access token con acceso de lectura a los datos que querés consultar. Para datos públicos, GitHub documenta lectura pública con tokens fine-grained; si usás un token clásico para GraphQL, documenta el scope `public_repo`. Este generador no necesita permisos de escritura para consultar estadísticas. Consultá la [guía de autenticación GraphQL](https://docs.github.com/en/graphql/guides/forming-calls-with-graphql) y los [permisos del endpoint de commits](https://docs.github.com/en/rest/commits/commits). Dar acceso privado al token no convierte LOC en una métrica de repositorios privados: el inventario usado es el de repositorios públicos del usuario.

Generá ambas cards:

```bash
python -m profile_card
```

El comando instalado `profile-card` es equivalente. Ambos usan el `profile.toml`, `.env`, template y directorio de salida del clon donde instalaste el proyecto. No hay argumentos CLI que cambiar.

Las salidas son `generated/profile-dark.svg` y `generated/profile-light.svg`. El procesamiento también deja imágenes intermedias en `generated/debug/`, ignoradas por Git. El modelo se reutiliza desde `~/.u2net`.

Para probar sin usar el token de `.env`, en Bash:

```bash
GITHUB_TOKEN='' python -m profile_card
```

En PowerShell, podés dejar temporalmente vacío el valor en tu `.env` y quitar una eventual variable de entorno `GITHUB_TOKEN`.

### Comportamiento ante errores

| Situación | Resultado |
|---|---|
| Sin token | REST público disponible; Commits/Contribs muestran `--` |
| Token rechazado en REST (401) | Aborta con mensaje útil; corregí el token o ejecutá sin él |
| Fallo del usuario/listado de repositorios REST | Aborta; no sustituye datos por cero |
| Fallo GraphQL o respuesta incompleta | Warning; Commits/Contribs muestran `--` |
| LOC desactivado | Net LOC muestra `--` |
| Fallo al calcular o guardar LOC | Warning; Net LOC muestra `--`, sin total parcial |
| Cache corrupto/incompatible | Warning; se reconstruye si las consultas completan |
| Fallo al descargar/procesar el avatar | Aborta |

No hay reintentos automáticos ante rate limit. Sin autenticación, el límite REST habitual es 60 requests/hora por IP; una primera ejecución de LOC puede superarlo. Usá un token o desactivá LOC. [Límites oficiales](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).

## Usarlo en tu GitHub Profile README

Para mostrar un README de perfil, el repositorio público debe llamarse igual que tu usuario. Si las cards y el README están en ese mismo repositorio, usá:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./generated/profile-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./generated/profile-light.svg">
  <img src="./generated/profile-dark.svg" alt="Mi perfil de GitHub" width="100%">
</picture>
```

Si el generador vive en otro repositorio, reemplazá cada ruta por la URL pública raw correspondiente, por ejemplo `https://raw.githubusercontent.com/USUARIO/REPOSITORIO/RAMA/generated/profile-dark.svg`. Publicá ambos SVG junto con los cambios; GitHub puede tardar en refrescar imágenes cacheadas.

## Automatización con GitHub Actions

Los workflows están en `.github/workflows/`:

- **Tests:** corre en push, pull request y ejecución manual. Instala `.[dev]`, usa cache pip y ejecuta toda la suite con permisos `contents: read`.
- **Update profile:** corre manualmente o cada día a las 06:00 UTC (03:00 en Buenos Aires). Instala el proyecto, reutiliza pip y `~/.u2net`, genera ambos temas y commitea exclusivamente los SVG y `cache/loc.json` si cambiaron. También guarda cambios que afecten solo al cache. Las ejecuciones sobre la misma rama se serializan.

Configuración en tu repositorio:

1. Publicá estos archivos en la rama por defecto y habilitá Actions; en un fork puede ser necesario habilitar los workflows explícitamente.
2. El workflow usa el `GITHUB_TOKEN` automático, sin crear un secret obligatorio. Para usar tu propia credencial de lectura, agregá **Settings → Secrets and variables → Actions → New repository secret → `PROFILE_TOKEN`**. Si existe, tiene prioridad; debe ser válido. `.env` local no se sube a Actions.
3. Permití que Actions escriba contenidos en el repositorio. El workflow solicita `contents: write`; las políticas de organización o protecciones de rama pueden impedir el push. No se hacen force-pushes ni se omiten esas restricciones.
4. Ejecutá **Actions → Update profile → Run workflow** sobre la rama por defecto. Revisá que genere ambos archivos y que el log no contenga warnings inesperados. Verificá que Commits/Contribs sean números si necesitás esas métricas; si el token automático no puede consultarlas, configurá `PROFILE_TOKEN`.
5. Ejecutá nuevamente: sin cambios de avatar, estadísticas o cache, debe finalizar con `No profile changes`. Comprobá también **Tests** y la siguiente ejecución programada.

`PROFILE_TOKEN` se usa solo para consultar APIs. El push utiliza el token automático de checkout. Update profile no escucha eventos push, y los pushes hechos con `GITHUB_TOKEN` no disparan otros workflows por push, evitando ciclos. [Comportamiento de triggers](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

El cron requiere que el workflow esté en la rama por defecto. GitHub puede retrasar ejecuciones y desactivar schedules de repositorios públicos tras 60 días sin actividad. [Documentación de schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Qué significan las estadísticas

| Campo | Fuente y significado |
|---|---|
| Repos | `public_repos` del usuario; cantidad de repositorios públicos, incluidos forks |
| Followers | Seguidores actuales del usuario |
| Stars | Suma de stars de sus repositorios públicos enumerados, incluidos forks; no las stars que dio a otros |
| Commits | `totalCommitContributions` de GraphQL: contribuciones de commits que GitHub atribuye al usuario en el último año |
| Contribs | `contributionCalendar.totalContributions`: contribuciones del último año según las reglas y visibilidad de GitHub; incluye actividad distinta de commits |
| Net LOC | Suma histórica de additions menos deletions de los commits elegibles descritos abajo |

Commits y Contribs usan el período por defecto de GitHub (desde hace un año hasta ahora), no un total de toda la vida ni necesariamente el año calendario. LOC no tiene ese filtro temporal. Sus valores no son directamente comparables. [Referencia de `contributionsCollection`](https://docs.github.com/en/graphql/reference/users).

### Net LOC y sus límites

```text
net LOC = Σ additions − Σ deletions
```

Se recorren los repositorios públicos propiedad del usuario. Por cada uno, GitHub lista commits filtrados por `author=username` desde la default branch. No se recorren todas las ramas ni todos los repositorios ajenos donde colaboraste. [Semántica del endpoint](https://docs.github.com/en/rest/commits/commits).

- Se omiten merges (más de un padre), forks por defecto y exclusiones `owner/repository` sin distinguir mayúsculas.
- Siempre se excluye `username/username`, para evitar contar el propio perfil. Si el generador vive en otro repositorio, agregalo a `exclude_repositories`.
- Un repositorio repetido se procesa una sola vez; un SHA compartido se suma una sola vez en todo el cálculo, incluso al habilitar forks.
- La atribución depende del autor que reconoce GitHub; no es el committer ni una suma especial de coautores.
- Cuenta cambios de texto de cualquier archivo: código, documentación, dependencias vendorizadas o archivos generados. No mide líneas actuales ni productividad.
- Puede ser negativo. Merges omitidos también omiten cambios exclusivos de resolución de conflictos. Squashes/cherry-picks pueden cambiar la atribución o representar cambios similares con distintos SHAs.
- Rebases, force-pushes, cambios de rama por defecto y repositorios eliminados/renombrados pueden cambiar el total: refleja la historia actualmente alcanzable, no un registro inmutable.
- La API paginada no proporciona una instantánea de todos los repositorios; cambios concurrentes durante el recorrido pueden afectar una ejecución.

### Cache LOC

`cache/loc.json` se versiona como estado reutilizable pequeño. Guarda exclusivamente nombres de repositorios públicos, SHAs, additions/deletions y versión del formato; no tokens, mensajes, autores ni diffs. No edites los contadores manualmente: el esquema se valida, pero los valores cacheados válidos se reutilizan como datos de confianza.

Cada ejecución vuelve a listar los commits; solo descarga los detalles de SHAs desconocidos. No es incremental respecto del listado. La segunda ejecución sin cambios reutiliza los detalles existentes.

El cálculo trabaja sobre una copia en memoria. Solo al completar todos los repositorios elimina entradas obsoletas y reemplaza el JSON mediante un archivo temporal en el mismo directorio. Un fallo no persiste pruning parcial ni publica una suma incompleta. Un JSON inválido se ignora con warning y solo se reemplaza si la reconstrucción termina correctamente.

Al cambiar de usuario, una ejecución LOC exitosa reemplaza el conjunto anterior. Si LOC está desactivado, el archivo existente no se usa ni modifica. Podés quitar ese archivo para forzar una reconstrucción; el costo será consultar nuevamente los detalles históricos. En Actions, checkout restaura el cache versionado y el commit final guarda sus cambios junto con los SVG.

## Arquitectura

`main.py` coordina configuración/entorno, GitHub, avatar y salida. `config.py` valida las tablas TOML; `github.py` encapsula REST/GraphQL; `metrics.py` calcula LOC; `cache.py` valida y persiste su cache. `avatar.py` descarga y procesa el avatar con Pillow/rembg. `renderer.py` renderiza `templates/profile.svg.j2` con Jinja2 y escape XML activo para ambos temas.

## Tests

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q src/profile_card
```

Los tests no necesitan token, red ni descargar u2net. Cubren configuración, XML y escape en ambos temas, transparencia, respuestas HTTP simuladas, LOC/cache y degradación ante fallos. Para validar la integración real, ejecutá `python -m profile_card` dos veces y revisá ambas imágenes y los warnings.

## Licencia

[MIT](LICENSE). Copyright © 2026 Gonzalo Gabriel Mayorga.
