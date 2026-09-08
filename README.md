# Visor de seguimiento al mercado laboral · Cámara de Comercio de Cali

Tablero interactivo con las cifras de mercado laboral de **Cali A.M.**, con
fuente en la Gran Encuesta Integrada de Hogares del DANE.

El nombre público del tablero es **Visor de seguimiento al mercado laboral**.
El repositorio conserva su nombre original, `Tablero-mercado-laboral`.

---

## Ver el tablero

Hay dos versiones del mismo tablero. Elige según lo que necesites.

### Para mirarlo ahora mismo · `tablero-completo.html`

Doble clic y listo. Los datos y el logo van dentro del archivo, así que no
necesita nada más: funciona desde el escritorio, una memoria USB o un adjunto
de correo. Pesa 1,9 MB.

Se regenera con:

```bash
python construir_archivo_unico.py
```

Sirve para revisar, para mostrarlo en una reunión y para mandarlo por correo.
No sirve para publicar en el sitio web.

### Para publicar · la carpeta `docs/`

Esta es la versión que va al servidor. Es más liviana y separa el tablero de
los datos, así que actualizar el mes siguiente solo cambia el `datos.json`.

**Ojo con esto:** `docs/index.html` pide los datos con `fetch`, y los
navegadores bloquean `fetch` cuando la página se abre con doble clic
(protocolo `file://`). Si lo abres así verás la pantalla de carga y nada más.
No está dañado: necesita servirse por HTTP.

Para verla en tu computador antes de publicar:

```bash
cd docs
python -m http.server 8000
```

y abres `http://localhost:8000`.

---

```
observatorio-mercado-laboral/
├── datos/                  ← aquí van los cuatro anexos del DANE
│   ├── anexGEIHjun2026_2.xlsx           (general)
│   ├── anexGEIHMLSabrjun2026.xlsx       (sexo)
│   ├── anexGEIHEISSabrjun2026.xlsx      (informalidad)
│   └── anexGEIHMLJabrjun2026_1.xlsx     (juventud)
│   └── historial.csv       ← de qué URL salió cada anexo, con su sha256
├── marca/                  ← insumos de marca (brandbook y plantilla)
├── CLAUDE.md               ← contexto y reglas del proyecto
├── BOTON-VISOR.md          ← texto para el equipo de web de la CCC
├── descargar.py            ← baja los anexos del DANE
├── etl.py                  ← convierte los anexos en datos.json
├── verificar.py            ← pruebas de regresión sobre los datos
├── construir_archivo_unico.py  ← arma tablero-completo.html
├── tablero-completo.html   ← versión de un solo archivo, abre con doble clic
├── docs/                   ← esto es lo que se publica
│   ├── index.html          ← el tablero completo
│   ├── datos.json          ← generado por etl.py, no se edita a mano
│   ├── CNAME.pendiente     ← subdominio, sin activar todavía
│   └── assets/
│       ├── logo-ccc-blanco.svg  ← el que va en el riel azul
│       ├── LogoCCCPrincipal.jpg
│       └── fonts/          ← ver LEEME.txt
└── .github/workflows/publicar.yml
```

---

## Actualizar cada mes

**No hay que hacer nada.** Todos los días a las 9 de la mañana, hora de
Colombia, un proceso automático revisa si el DANE publicó anexos nuevos. Si los
hay, los baja, los procesa, comprueba las cifras y republica el tablero. Si no
hay nada nuevo — que es lo normal casi todos los días — termina sin tocar nada.

```
[cron diario] -> descargar.py -> etl.py -> verificar.py -> GitHub Pages
                      |               |         |
                  ¿nada nuevo?     ¿falla?   ¿falla?
                    termina         issue    issue, NO publica
```

**Si `verificar.py` falla, el tablero no se actualiza.** Se queda mostrando las
cifras del mes pasado y se abre un *issue* en GitHub. Es a propósito: es
preferible una cifra vieja a una equivocada con el logo de la Cámara encima.
Cuando el problema se resuelve y vuelve a correr bien, el issue se cierra solo.

### Correrlo a mano

Hace falta para trabajar en local, o para reconstruir si algo falló:

```bash
python descargar.py     # busca anexos nuevos en el DANE
python etl.py           # los procesa
python verificar.py     # comprueba que nada se rompió
```

`descargar.py` habla por su código de salida: `0` hay datos nuevos, `2` no hay
nada que hacer, `1` error de verdad. El `2` es lo normal.

Otras formas de usarlo:

```bash
python descargar.py --simular      # dice qué haría, sin escribir nada
python descargar.py --probar       # comprueba los nombres, sin tocar la red
python descargar.py --mes may2026  # fuerza un mes concreto
```

Si además quieres la copia de un solo archivo para circular por correo, agrega
`python construir_archivo_unico.py`.

### Si el DANE cambia algo

Los anexos se buscan primero por su URL predecible y, si esa da 404, leyendo la
página del módulo en el portal del DANE. `datos/historial.csv` guarda de qué
URL salió cada archivo y su `sha256`, así que meses después se puede volver a
bajar y comprobar que es el mismo que produjo las cifras publicadas.

### Por qué no se rompe

`etl.py` no depende de números de fila ni de columna. Busca las cosas por su
etiqueta de texto:

- **Los archivos**, por patrón de nombre (`EISS` → informalidad, `MLJ` →
  juventud, `MLS` → sexo, el resto → general). Da igual que cambie el sufijo
  del mes.
- **Los bloques de ciudad**, por el nombre de la ciudad en la columna A,
  ignorando tildes y mayúsculas.
- **Los indicadores**, por el comienzo de su etiqueta (`Tasa de desocupación…`).
- **Los períodos**, anclados en que la primera columna de datos es el trimestre
  que termina en marzo de 2007. La columna *i* termina *i* meses después.

Si el DANE agrega períodos, mueve un bloque o renombra un archivo, sigue
funcionando. Si cambia el nombre de una hoja o de un indicador, el proceso
avisa en pantalla en vez de producir datos silenciosamente equivocados.

### Comprobación rápida después de actualizar

El script imprime cuántas ciudades y períodos leyó de cada módulo, y cuál es
el último trimestre. Si el último trimestre no es el que esperabas, algo pasó
con los archivos de entrada.

---

## Publicar

El tablero está en:

**https://cccjaguirre.github.io/Tablero-mercado-laboral/**

Se republica solo. No hay que subir nada a mano.

### Lo que hubo que configurar una vez

Estos pasos ya están hechos. Quedan anotados porque no se pueden automatizar y
habría que repetirlos si el proyecto se mudara a otro repositorio:

1. **Crear el repositorio en GitHub y hacerlo público.** Pages gratuito
   necesita repositorio público.
2. **Settings → Pages → Source = GitHub Actions.** Sin esto el workflow corre
   entero y se cae en el último paso.
3. **Subir el código** (`git push`).

Nada más. El resto lo hace el workflow.

### El repositorio cambió de dueño

En septiembre de 2026 pasó de una cuenta personal a la institucional
`CCCJAGUIRRE`. Qué implica:

- **La URL del repositorio redirige sola.** GitHub deja un 301 permanente, así
  que los enlaces viejos a `github.com` siguen funcionando y un `git push`
  contra el remote antiguo también. Aun así conviene actualizarlo:

  ```bash
  git remote set-url origin https://github.com/CCCJAGUIRRE/Tablero-mercado-laboral.git
  ```

- **La URL de Pages NO redirige.** `blasco2001.github.io/Tablero-mercado-laboral/`
  devuelve 404, sin reenvío. Cualquier enlace que se haya compartido con esa
  dirección está roto y hay que reemplazarlo. Es la razón de más peso para
  activar cuanto antes el subdominio propio: un dominio de la CCC sobrevive a
  cualquier mudanza futura de cuenta.

- **El workflow, los issues y el cron siguen igual.** Las corridas programadas
  no se interrumpieron y el historial de Actions viaja con el repositorio.

### Subdominio propio · pendiente

La idea es que quede en `observatoriolaboral.ccc.org.co`. El archivo está
preparado como `docs/CNAME.pendiente` y **sin activar a propósito**: con un
archivo `CNAME` presente, Pages redirige la URL de `github.io` al dominio
propio, así que si el DNS todavía no resuelve el tablero queda inalcanzable por
las dos rutas.

El orden correcto:

1. Pedirle a TI de la CCC este registro:

   ```
   Tipo    CNAME
   Nombre  observatoriolaboral
   Valor   cccjaguirre.github.io
   TTL     3600
   ```

2. Esperar a que `dig observatoriolaboral.ccc.org.co` responda.
3. Solo entonces:

   ```bash
   git mv docs/CNAME.pendiente docs/CNAME
   git commit -m "Activar el subdominio observatoriolaboral.ccc.org.co"
   git push
   ```

4. En Settings → Pages, marcar **Enforce HTTPS** cuando GitHub termine de
   emitir el certificado.

### Servidor propio, si algún día hace falta

`docs/` es un sitio estático: HTML, un JSON y dos imágenes. No necesita PHP,
base de datos ni Node. Se sube por FTP a cualquier carpeta pública.

**Importante:** el tablero carga `datos.json` con `fetch`, así que tiene que
servirse por HTTP. Abrir `index.html` con doble clic no funciona. Para probarlo
en local:

```bash
cd docs && python -m http.server 8000
# luego abrir http://localhost:8000
```

### Ponerlo en la página de la CCC

**Se enlaza, no se incrusta.** La página del Visor de Datos de la CCC no
incrusta tableros: es una lista de botones que abren enlaces externos, igual
que los visores de Power BI y Tableau que ya están ahí.

El texto listo para pasarle al equipo de web — título, descripción y URL, en el
estilo de los botones que ya existen — está en [`BOTON-VISOR.md`](BOTON-VISOR.md).

### Enlaces a una vista concreta

La vista queda guardada en la propia URL, así que se puede mandar por correo un
enlace que abra justo donde uno quiere:

```
https://cccjaguirre.github.io/Tablero-mercado-laboral/#seccion=informal&modo=an&periodo=2024
```

El período va por su código, no por su posición, así que el enlace sigue
apuntando a la misma cifra cuando lleguen datos nuevos.

---

## Qué contiene el tablero

| Sección | Qué muestra | Desde |
|---|---|---|
| Resumen | Las tres tasas de Cali A.M., composición de la fuerza de trabajo y ranking | 2007 |
| Panorama general | Desempleo, ocupación, participación, subocupación y niveles | 2007 |
| Brechas de género | Los mismos indicadores separados por sexo, más las brechas | 2007 |
| Informalidad | Proporción, composición formal/informal y posición ocupacional | 2021 |
| Juventud | Mercado laboral de 15 a 28 años | 2007 |
| Fuera de la fuerza de trabajo | Quién no busca empleo ni lo tiene, y en qué ocupa el tiempo | 2010 |
| Comparativo ciudades | Ranking, puesto de Cali en el tiempo y tabla completa | 2007 |

**El tablero no lleva pestaña de metodología.** Los visores de la CCC no la
usan, así que la documentación vive aquí y en `CLAUDE.md`, no en el sitio
público. Lo que sí queda en el tablero son las notas al pie de cada gráfica
que explican un dato concreto — el corte de subocupación de 2020, el arranque
de la informalidad en 2021, la definición de la brecha de género.

**Controles:** agregación temporal (trimestre móvil o promedio anual), período,
año de inicio de la serie, y hasta siete ciudades de comparación. Además,
descarga de los datos en CSV y exportación a PDF.

### De dónde sale cada sección

| Sección | Anexo del DANE | Hoja |
|---|---|---|
| Resumen, Panorama, Comparativo | general | `Total 23 ciudades A.M. Trim`, `Total nacional Trim` |
| Brechas de género | sexo (MLS) | `Hombres - 23 Ciud`, `Mujeres - 23 Ciud`, `P y T N`, `P y T 13 Ciud` |
| Informalidad · proporción y niveles | informalidad (EISS) | `Prop informalidad`, `Ciudades` |
| Informalidad · posición ocupacional | general | `Ocupados 23 Ciudades_pos_Trim`, `Ocupados TN_posición` |
| Juventud | juventud (MLJ) | `23 ciudades trim móvil`, `13 ciudades trimestre móvil`, ` Tnal trimestre móvil` |
| Fuera de la fuerza de trabajo | general | `Pob_fuera_fuerza_trab_T13ciud`, `Pob_fuera_fuerza_trabajo_TN` |

El inventario completo de las 68 hojas, con cuáles se usan y qué trae cada una,
está en `CLAUDE.md`.

### Una cifra que calculamos nosotros

**La proporción de población fuera de la fuerza de trabajo** (`pct_ffft`) no la
publica el DANE: se deriva dividiendo la población fuera de la fuerza entre la
población en edad de trabajar, dos niveles que sí publica.

Existe porque comparar el nivel absoluto de Cali contra el agregado de 13
ciudades no dice nada — el agregado es diez veces más grande y aplasta la serie
de Cali contra el eje. La proporción sí es comparable entre ciudades.

Es la única cifra derivada del tablero. Todo lo demás sale tal cual de los
anexos, o es un promedio anual calculado con la regla de más abajo.

### El promedio anual

Se calcula con los cuatro trimestres móviles que **no se traslapan**:
Ene-Mar, Abr-Jun, Jul-Sep y Oct-Dic. Cada mes del año entra exactamente una vez.

Los niveles de población se promedian; las tasas se **recalculan** a partir de
esos niveles. Promediar tasas directamente sesgaría el resultado hacia los
trimestres con menos población.

*Comprobación:* para Cali A.M. en 2025 este método da 8,75% de desempleo y
1.115.000 ocupados. El DANE publica 8,746% y 1.115.100 para el año completo.

**Año en curso:** cuando un año todavía no tiene los cuatro trimestres, se
promedia con los que haya y aparece marcado — *2026 (Ene-Jun)*. La comparación
se hace contra el mismo tramo del año anterior, no contra el año entero, así
que 2026 hasta junio se mide contra Ene-Jun de 2025.

---

## Personalizar

### Cambiar la ciudad de referencia

En `index.html`, la constante `FOCO`. En `etl.py`, `CIUDAD_FOCO`.

### Cambiar qué ciudades salen comparadas por defecto

En `index.html`, la variable `comparar`.

### Colores

Todos salen del Nexus Design System y están en un solo bloque `:root` al
comienzo de `index.html`, con el nombre de cada color de la marca. Los momentos
cromáticos por sección están en la constante `TEMAS`.

Reglas del sistema que ya vienen aplicadas: la paleta principal domina la
composición y el color temático funciona como acento; las gradaciones son
verticales con el tono oscuro en la base; los extremos de barras y líneas van
redondeados; los datos se ordenan por tamaño; y los titulares no usan
mayúsculas ni itálicas.

### Tipografía

Las fuentes de marca están **desactivadas**: en `marca/fuentes/` solo hay
`.otf` y `.ttf`, que es licencia de escritorio y no cubre publicarlas en un
sitio web. Mientras tanto se usan Encode Sans Expanded y Source Sans 3, de
Google Fonts.

Cómo activarlas cuando haya licencia *webfont*: `docs/assets/fonts/LEEME.txt`.

### Morfologías

Los arcos de las cabeceras y del riel son **el arte original de la marca**,
extraído de `marca/CCC_PlantillaPPTX.pptx`. Están en la constante
`MORFOLOGIAS` de `docs/index.html` y se dibujan con la función `arcos()`.

Los colores no vienen del arte, que es siempre azul. Cada trazo guarda su nivel
de tono y el tema de la sección decide qué color va en cada nivel, así que las
morfologías cambian de color con la sección sin perder la jerarquía del
original.

---

## Advertencias de lectura

- Las poblaciones vienen del DANE en miles; el tablero ya las convierte a personas.
- Toda variable cuya proporción respecto a la fuerza de trabajo sea menor al
  10% tiene un error de muestreo superior al 5%, el límite de calidad que
  admite el DANE.
- Entre 2010 y 2020 la información ya incorpora los ajustes de población del
  cambio de marco de 2021.
- La serie de informalidad arranca en 2021 por el cambio metodológico de la GEIH.
- Cali A.M. incluye a Cali y Yumbo.

---

**Fuente:** DANE — Gran Encuesta Integrada de Hogares (GEIH).
**Elaboración:** Cámara de Comercio de Cali.
