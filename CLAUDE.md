# CLAUDE.md

Contexto del proyecto para cualquier sesión de trabajo en este repositorio.
Léelo completo antes de tocar nada. Buena parte de lo que sigue son decisiones
que ya se tomaron con criterio; cambiarlas sin entenderlas rompe las cifras.

---

## Qué es esto

**Visor de seguimiento al mercado laboral** de la **Cámara de Comercio de Cali**. Una
aplicación web estática que publica los indicadores de mercado laboral de
**Cali A.M.**, con fuente en la Gran Encuesta Integrada de Hogares (GEIH) del
DANE, y permite compararlos contra las otras 22 ciudades y áreas
metropolitanas.

Se va a publicar en el sitio institucional de la CCC (WordPress). El modelo de
publicación es el mismo que se usaba con Power BI: el tablero vive en su propia
URL y desde la página se enlaza o se incrusta.

**El foco es Cali A.M.** Las demás ciudades existen para comparar, no para
competir por el protagonismo. Cualquier vista nueva debe responder primero
"¿cómo está Cali?" y solo después "¿frente a quién?".

---

## Cómo está armado

```
descargar.py                 Trae los anexos del DANE -> datos/
etl.py                       Lee los anexos del DANE -> docs/datos.json
verificar.py                 Pruebas de regresión sobre datos.json
construir_archivo_unico.py   Arma tablero-completo.html (versión portátil)
datos/                       Los cuatro anexos .xlsx del DANE
  historial.csv              Rastro auditable: sha256 y URL de cada descarga
docs/                        Lo que se publica
  index.html                 El tablero entero: HTML + CSS + JS en un archivo
  datos.json                 Generado por etl.py. No se edita a mano.
  assets/
    logo-ccc-blanco.svg      Logo en blanco, para el riel azul
    LogoCCCPrincipal.jpg     Logo a color, sin usar hoy (sirve para og:image)
    fonts/                   Ver LEEME.txt
tablero-completo.html        Versión de un solo archivo, abre con doble clic
.github/workflows/           Construye y publica en GitHub Pages
```

Ciclo mensual completo. **Normalmente no hay que correrlo**: el workflow lo
hace solo todos los días. Esto es para trabajar en local o para reconstruir a
mano si algo falló:

```bash
python descargar.py                 # busca anexos nuevos en el DANE
python etl.py                       # los procesa
python verificar.py                 # confirma que nada se rompió
python construir_archivo_unico.py   # opcional: copia portátil
```

`descargar.py` sale con código 2 cuando no hay nada nuevo, que es lo normal
casi todos los días.

### Sin dependencias

Las gráficas son **SVG generado a mano** en `index.html`: líneas, barras
horizontales, barras apiladas, anillo y cascada de población. No hay Chart.js,
ni D3, ni bundler, ni paso de compilación. Fue una decisión deliberada: el
tablero tiene que sobrevivir años en un servidor institucional sin que nadie le
haga mantenimiento, y cada CDN es una dependencia que algún día se cae.

**No metas librerías de gráficas.** Si necesitas un tipo de gráfica nueva,
escríbela en el mismo estilo que las que ya están.

### Dos formas de servir los mismos datos

`index.html` mira si existe un `<script id="datos-embebidos">` en el documento.
Si está, lo usa; si no, pide `datos.json` con `fetch`. Es un solo código base.

Consecuencia práctica: **`docs/index.html` no funciona con doble clic**. El
navegador bloquea `fetch` bajo `file://`. Para probarlo en local:

```bash
cd docs && python -m http.server 8000
```

`tablero-completo.html` sí abre con doble clic porque lleva los datos y el logo
incrustados. No borres esa ruta doble.

---

## Reglas de datos que no se pueden romper

Cada una está protegida por una prueba en `verificar.py`. Si una falla, no
ajustes la prueba: entiende qué pasó.

### 1. Un cero exacto del DANE no es un dato

Los anexos rellenan con `0` los períodos que no se midieron. El caso claro es
la subocupación entre Ene-Mar y Jul-Sep de 2020, cuando la pandemia interrumpió
la recolección. Dibujar eso como cero produce un desplome que nunca ocurrió.

`num()` en `etl.py` devuelve `None` ante un cero exacto. En un área
metropolitana de millones de habitantes ninguna población ni tasa de este
tablero puede valer exactamente cero.

Las gráficas de línea dibujan el hueco: `lineas()` parte el trazo en tramos y
no une los extremos. Unirlos inventaría una trayectoria que nadie midió.

### 2. El promedio del año son cuatro trimestres que no se traslapan

Ene-Mar, Abr-Jun, Jul-Sep y Oct-Dic. Cada mes del año entra exactamente una
vez. Esta definición la fijó la CCC y reproduce la cifra oficial del DANE:
Cali A.M. en 2025 da 8,75% de desempleo y 1.115.000 ocupados, contra 8,746% y
1.115.100 publicados.

**Los niveles se promedian. Las tasas se recalculan a partir de esos niveles.**
Promediar tasas directamente sesga el resultado hacia los trimestres con menos
población. Esto vale en el ETL y en cualquier cálculo nuevo del front.

Si a un año completo le falta algún trimestre, el promedio queda vacío. Un
promedio con huecos no es el del año: es el de los meses que sobrevivieron.

Se descartó el **año móvil**: no lo necesita el proyecto. Solo existen dos
modos temporales, trimestre móvil y promedio anual.

### 3. Un año a medias no se compara contra uno entero

2026 llega hasta junio. Compararlo contra 2025 completo da +0,3 pp; contra
Ene-Jun de 2025 da −0,7 pp. La segunda es la cifra correcta.

`referencia_anual` en `datos.json` guarda, para cada año, el valor del año
anterior medido con el mismo número de trimestres. Las tarjetas KPI lo usan y
la etiqueta lo dice en voz alta: "vs. 2025 (Ene-Jun)".

### 4. El ETL busca por etiqueta, nunca por número de fila

Los anexos del DANE cambian de nombre cada mes y crecen en columnas.

- **Archivos**: por patrón de nombre. `EISS` → informalidad, `MLJ` → juventud,
  `MLS` → sexo, el resto `anexGEIH*` → general.
- **Bloques de ciudad**: por el nombre en la columna A, normalizado sin tildes
  ni mayúsculas.
- **Indicadores**: por el comienzo de su etiqueta.
- **Períodos**: anclados. La primera columna de trimestre móvil termina en
  marzo de 2007; la columna *i* termina *i* meses después. Informalidad se
  ancla en marzo de 2021.

**No introduzcas índices fijos de fila o columna.** Es lo que hace que el
proceso sobreviva a las actualizaciones del DANE.

### 5. Canonizar SIEMPRE antes de filtrar

Esta es la causa raíz de tres errores seguidos, y vale más que la tabla de
alias que la acompaña. **El orden importa más que la tabla.**

`detectar_bloques()` comparaba el nombre crudo de la columna A contra
`NOMBRES_CIUDAD` y solo *después*, ya aceptado el bloque, lo pasaba por
`titulo_ciudad()`:

```python
validos = {norm(n) for n in nombres_validos}    # ← lista literal
if norm(v) in validos:                          # ← se decide aquí
    bloques.append((i, titulo_ciudad(v)))       # ← se canoniza tarde
```

Con ese orden, la tabla `AGREGADOS` **no servía para nada en la decisión**.
Cualquier grafía que no estuviera literalmente en `NOMBRES_CIUDAD` se
descartaba en silencio, aunque la tabla la resolviera perfectamente. Por eso
`TOTAL 23 CIUDADES Y A.M.` no entraba: el alias existía y nunca se consultaba.

Lo correcto es canonizar los dos lados y comparar formas canónicas:

```python
validos = {norm(titulo_ciudad(n)) for n in nombres_validos}
canon = titulo_ciudad(v)
if norm(canon) in validos:
    bloques.append((i, canon))
```

**La regla general:** cuando haya una tabla de normalización, aplícala antes de
cualquier filtro, comparación o descarte. Una tabla de alias que se consulta
después de decidir es decoración. Vale para ciudades, para nombres de hoja y
para etiquetas de indicador.

Por qué costó tres intentos: el síntoma siempre parecía otro — primero "faltan
hojas", luego "faltan grafías", después "no existe el dato". Las tres veces la
causa era la misma línea.

### 5.1 Una hoja por módulo NO trae todo

El DANE reparte **las mismas variables en varias hojas, una por nivel
geográfico**. Nunca asumir que la hoja de un módulo trae todos los dominios.

El ETL leía una sola hoja por módulo, y por eso juventud y sexo se quedaron
meses sin total nacional ni total de 13 ciudades: el chip de comparación estaba
en la interfaz y no dibujaba nada. Nadie lo notó porque no falla, simplemente
no aparece la línea.

```
JUVENTUD (MLJ)      ' Tnal trimestre móvil'        -> Total nacional
                    '13 ciudades trimestre móvil'  -> Total 13 ciudades
                    '23 ciudades trim móvil'       -> las 23 ciudades

SEXO (MLS)          'P y T N'                      -> nacional, con HOMBRES y MUJERES
                    'P y T 13 Ciud'                -> 13 ciudades, con HOMBRES y MUJERES
                    'Hombres - 23 Ciud'            -> las 23 ciudades
                    'Mujeres - 23 Ciud'
```

### 5.2 El mismo agregado, cuatro grafías

Ninguna normalización razonable las hace converger sola:

```
"Total 23 ciudades y área metropolitanas"    general        ÁREA en singular
"Total 23 ciudades y áreas metropolitanas"   juventud       plural
"TOTAL 23 CIUDADES Y A.M."                   sexo           con sigla
"23 ciudades y A.M."                         informalidad   sin "Total"
```

La tabla `AGREGADOS` en `etl.py` las resuelve todas — **pero solo funciona si
se consulta antes de filtrar**, que es la regla 5. Al agregar una hoja, listar
sus grafías y compararlas contra esa tabla, no suponer que ya están cubiertas.

Los bloques de agregado van **al final de la hoja**, después de las ciudades:
fila 485 de 515 en general, 423 de 448 en sexo.

### 5.3 Tres trampas más, todas comprobadas

1. **`' Tnal trimestre móvil'` empieza con un espacio.** `cargar_hoja()` lo
   tolera porque compara normalizado, pero al escribir el nombre hay que
   saberlo.

2. **El subtítulo de la hoja miente.** Las tres hojas de juventud dicen
   "Total nacional" en su línea de subtítulo, incluso las de 13 y 23 ciudades.
   Es un copiar-pegar del DANE. **No uses el subtítulo para identificar el
   nivel**: usa el nombre de la hoja y la cabecera del bloque de datos.

3. **El título de la hoja normaliza igual que la cabecera del bloque.** En la
   hoja nacional de juventud, la fila 9 dice `Total nacional` como subtítulo y
   la fila 13 es la cabecera real. Buscar por nombre y quedarse con la primera
   coincidencia devuelve un bloque vacío. `bloque_con_nombre()` sigue buscando
   hasta que una coincidencia traiga indicadores.

Esa tercera trampa tuvo un efecto de rebote: al canonizar antes de filtrar, el
subtítulo también pasó a detectarse como bloque, y eso rompió el conteo de
períodos, que se anclaba en "primer bloque + 2 filas". Ahora la fila de
trimestres se busca por contenido, con `fila_encabezado()`. **No quedan
anclajes por posición de fila en el ETL**, y no deben volver.

Para acotar dónde termina un bloque, `rango_del_bloque()` usa un criterio
**estructural**: una fila de indicador siempre trae números en las columnas de
período, una cabecera solo trae texto. No se usa la lista de indicadores del
mapa, porque el mapa no cubre todo lo que publica la hoja — "Tasa de
Subocupación" no está en `MAPA_SEXO` y cortaba el bloque a la mitad, dejando
fuera todos los niveles de población.

**Qué agregados existen de verdad:**

| | general | hombres | mujeres | juventud | informalidad | fuera | posición |
|---|---|---|---|---|---|---|---|
| Total nacional | sí | sí | sí | sí | sí | sí* | sí* |
| Total 13 ciudades | sí | sí | sí | sí | sí | sí | sí |
| Total 23 ciudades | sí | sí | sí | sí | sí | — | — |

\* convertido de serie mensual, ver más abajo.

Los tres están en todos los módulos donde el DANE los publica, así que la
comparación por defecto — 13 ciudades, Bogotá, Medellín — dibuja en todas las
secciones, y el comparador nacional también.

`Total 23 ciudades` no existe en las hojas de fuera de la fuerza de trabajo
(solo trae 13 ciudades) ni en la de posición ocupacional (termina en Sincelejo,
sin agregado). Comprobado recorriendo las dos hojas **hasta la última fila**.

Existe además un **`Total 10 ciudades`** en las hojas de general (fila 466) y de
sexo (fila 406). Está a propósito fuera del tablero: no lo pidió el proyecto.
Queda anotado aquí para que nadie lo vuelva a descubrir y pregunte, y hay una
prueba que confirma que no se cuela.

### Las hojas nacionales de fuera de la fuerza y de posición son MENSUALES

`Pob_fuera_fuerza_trabajo_TN` y `Ocupados TN_posición` vienen en serie mensual
(Ene, Feb, Mar…), mientras las de ciudades vienen en trimestre móvil (Ene-Mar,
Feb-Abr…). Pegar una mensual en la grilla de trimestres compararía un mes suelto
contra un promedio de tres.

`mensual_a_trimestre_movil()` las convierte promediando de a tres. **Que eso sea
legítimo está comprobado, no supuesto:** el módulo general publica el total
nacional en las dos formas, y promediar tres meses de la hoja mensual reproduce
la trimestral con diferencia 0,0000 a lo largo de toda la serie. Además, las
series convertidas se contrastan contra las del módulo general en los 196
períodos comparables: diferencia máxima 0,07 mil, que es el redondeo de `num()`.
`verificar.py` mantiene esa comprobación viva.

`verificar.py` comprueba esta matriz. Si alguien deja de leer una de esas
hojas, la prueba lo caza.

### 6. El enlace guarda el período por código, no por posición

El estado de la vista vive en el hash de la URL:

```
#seccion=informal&modo=an&periodo=2024&desde=2021&ciudades=Bogota%20D.C.
```

El período va como **código** (`2024`, `2026-06`), nunca como índice. La grilla
de trimestres crece uno cada mes: un enlace que dijera "posición 231"
apuntaría a junio hoy y a julio el mes entrante, y quien lo abriera vería una
cifra distinta de la que le mandaron sin enterarse de nada. Para una entidad
que cita cifras, eso es peor que un enlace roto.

Cada campo se valida contra los datos que existan al abrirlo. Un enlace de hace
un año puede nombrar un período o una ciudad que ya no están; en ese caso se
ignora ese campo y se abre en lo que sí exista. Un enlace viejo se degrada, no
se rompe.

`escribirHash()` se llama desde `render()` y de ningún otro lado: es el único
punto por el que pasan todos los cambios de estado, así que el enlace no puede
quedar desfasado. Va con `replaceState` para no llenar el historial con una
entrada por clic — dentro de un `try`, porque en `tablero-completo.html` el
origen es `null` y `replaceState` lanza `SecurityError`. Sin ese `try` la
versión de doble clic se caería en cada render.

### 7. Detalles de las fuentes

- Las poblaciones vienen en miles; el front las convierte a personas al mostrar.
- La informalidad solo existe desde el primer trimestre de 2021, por el cambio
  metodológico de la GEIH. Las gráficas recortan solas el tramo vacío inicial.
- Los NINI quedaron fuera a propósito: el DANE solo los publica a nivel
  nacional y el foco es Cali.
- Cali A.M. incluye a Cali y Yumbo.
- Toda variable cuya proporción respecto a la fuerza de trabajo sea menor al
  10% tiene un error de muestreo superior al 5%, que es el límite de calidad
  que admite el DANE. Vale sobre todo para las posiciones ocupacionales
  pequeñas: jornalero, trabajador familiar sin remuneración.
- Entre 2010 y 2020 la información ya incorpora los ajustes de población del
  cambio de marco de 2021.

### 8. Una sola cifra la calculamos nosotros

**`pct_ffft`, la proporción de población fuera de la fuerza de trabajo**, no la
publica el DANE. Se deriva en el ETL dividiendo `ffft` entre `pet`, dos niveles
que sí publica, sobre el módulo general, que trae las 23 ciudades.

Existe porque comparar el nivel absoluto de Cali contra el agregado de 13
ciudades no dice nada: el agregado es diez veces más grande y aplasta la serie
de Cali contra el eje. La proporción sí es comparable entre ciudades.

**Es la única cifra derivada del tablero.** Todo lo demás sale tal cual de los
anexos, o es un promedio anual calculado con la regla 2. Si aparece la
tentación de derivar otra, que quede documentada aquí igual que esta, y con la
misma pregunta contestada antes: ¿por qué no basta con lo que publica el DANE?

### 9. El tablero no lleva pestaña de metodología

Los visores de la CCC no la usan, así que **la documentación metodológica vive
en el README y en este archivo, no en el sitio público**. Hubo una sección
"Fuentes y metodología" y se quitó por eso.

Lo que sí se queda en el tablero son **las notas al pie de cada gráfica que
explican un dato concreto**: el corte de subocupación de 2020, el arranque de
la informalidad en 2021, la definición de la brecha de género, la dirección del
ranking. Esas son de lectura, no de método — sin ellas alguien malinterpreta la
cifra que está viendo.

El criterio para decidir si una nota se queda: **¿ayuda a leer bien el número
que tiene delante, o explica cómo trabajamos?** Lo primero se queda, lo segundo
va a la documentación.

**Y cómo se redacta: las notas afirman qué es el dato. Nunca explican qué no
es, ni por qué no es de otra forma.** Una nota defensiva delata que quien la
escribió se estaba anticipando a una objeción, y le pasa esa duda al lector.

```
no:  "El corte de 2020 no es una caída: la pandemia interrumpió la medición."
sí:  "Sin dato entre marzo y septiembre de 2020 por interrupción de la
      medición de subocupación durante la pandemia."

no:  "La serie arranca en 2010, no en 2007 como el resto del tablero."
sí:  "La serie de esta hoja del DANE arranca en 2010."

no:  "Puesto 1 = el valor más alto. Para desempleo, subir es una mala señal."
sí:  "Puesto 1 = el valor más alto entre las 23 ciudades y áreas
      metropolitanas."
```

De ahí salen tres consecuencias prácticas:

- **Sin negaciones ni contrastes**: "no es", "a diferencia de", "en vez de".
- **Sin juicios**: "mala señal", "preocupante". El dato es el que es; quien lo
  lee sabe si le conviene o no.
- **La nota tiene que ser cierta para la gráfica que tiene encima.** Una nota
  sobre la tasa de desempleo debajo de una gráfica de niveles de población es
  ruido, por correcta que sea la frase. Y nunca afirmar algo que el tablero no
  muestra: hubo una nota sobre el reparto por sexo de los oficios del hogar en
  un panel que no lo desagrega, y que para Cali el DANE ni siquiera publica.

---

## Qué trae cada anexo

**68 hojas en los cuatro anexos. El ETL lee 15.** Este inventario existe para
poder decidir qué se puede pedir sin volver a abrir los archivos. `USA` marca
las que el ETL lee hoy.

### General — `anexGEIH<mes><año>.xlsx` · 21 hojas

| | hoja | qué trae | nivel | serie |
|---|---|---|---|---|
| **USA** | `Total nacional Trim` | tasas y niveles | nacional | trim. 2007– |
| **USA** | `Total 23 ciudades A.M. Trim` | tasas y niveles | 23 ciudades + Total 13 | trim. 2007– |
| **USA** | `Ocupados 23 Ciudades_pos_Trim` | posición ocupacional | 23 ciudades | trim. 2010– |
| **USA** | `Pob_fuera_fuerza_trab_T13ciud` | fuera de la fuerza, por actividad | 13 ciudades | trim. 2010– |
| | `Total nacional` | lo mismo, serie mensual | nacional | mensual 2001– |
| | `Total 13 ciudades A.M.` | lo mismo, serie mensual | 13 ciudades | mensual 2001– |
| | `Total 7 ciudades sin A.M.` | tasas y niveles | 7 ciudades sin A.M. | trim. 2021– |
| **USA** | `Ocupados TN_posición` | posición ocupacional | nacional | **mensual** 2010– |
| **USA** | `Pob_fuera_fuerza_trabajo_TN` | fuera de la fuerza, por actividad | nacional | **mensual** 2010– |
| | `Ocupados TN_T13_rama` | ramas de actividad CIIU 4 | nacional | mensual 2015– |
| | `Ocupados TN_TCAB_TRES_rama_Trim` | ramas CIIU 4 | nacional, cab., resto | trim. 2015– |
| | `Ocupados 23 Ciudades_rama_Trim` | **ramas CIIU 4 por ciudad** | 23 ciudades | trim. 2015– |
| | `Año_móvil_32_ciudades` | tasas y niveles | 32 ciudades | año móvil |
| | `Año_móvil_5_ciudades_interm` + `_Rama` + `_Posc` | tasas, ramas, posición | 5 ciudades intermedias | año móvil |
| | `Otras_formas_trabajo` | trabajo no remunerado | nacional | mensual 2021– |
| | `Total_nacional_IML_Sexo` | tasas y niveles por sexo | nacional | mensual 2010– |
| | `Índice`, `Ficha metodológica`, `Errores relativos` | documentación | — | — |

**El agregado de 23 ciudades vive al final de `Total 23 ciudades A.M. Trim`**
(fila 485 de 515), escrito `Total 23 ciudades y área metropolitanas`, con
**ÁREA en singular**. En la fila 466 está `Total 10 ciudades`, que el tablero
**no** usa.

**Las dos hojas nacionales que se leen vienen en serie MENSUAL**, no en
trimestre móvil. El ETL las convierte promediando de a tres; ver la regla 5.

### Sexo — `anexGEIHMLS<trimestre>.xlsx` · 16 hojas

| | hoja | qué trae | nivel | serie |
|---|---|---|---|---|
| **USA** | `Hombres - 23 Ciud` / `Mujeres - 23 Ciud` | tasas y niveles | 23 ciudades | trim. móvil 2007– |
| **USA** | `P y T N` | tasas y niveles, bloques HOMBRES/MUJERES | nacional | trim. móvil 2007– |
| **USA** | `P y T 13 Ciud` | ídem | 13 ciudades | trim. móvil 2007– |
| | `P y T Cab` / `P y T Centros` | ídem | cabeceras / resto | trim. móvil 2007– |
| | `Pos ocup N` | **posición ocupacional por sexo** | nacional | trim. móvil 2007– |
| | `Pos ocup 13 Ciud` | **posición ocupacional por sexo** | 13 ciudades | trim. móvil 2007– |
| | `FFT N` | **fuera de la fuerza por actividad y sexo** | nacional | trim. móvil 2007– |
| | `FFT 13 Ciud` | **ídem** | 13 ciudades | trim. móvil 2007– |
| | `Ramas CIIU 4 N` / `Ramas CIIU4 13 Ciud` | ramas por sexo | nacional / 13 ciudades | trim. móvil 2015– |
| | `Índice`, `Ficha metodológica`, `Código_SAS`, `Errores Relativos` | documentación | — | — |

**El agregado de 23 ciudades vive al final de `Hombres - 23 Ciud` y
`Mujeres - 23 Ciud`** (fila 423 de 448), después de las ciudades, escrito
`TOTAL 23 CIUDADES Y A.M.`. Justo antes, en la fila 406, está `TOTAL 10
CIUDADES`, que el tablero **no** usa.

**Ojo con `FFT 13 Ciud` y `Pos ocup 13 Ciud`:** traen el corte por sexo, pero
**solo para el agregado**, en bloques HOMBRES y MUJERES. No hay ciudades, así
que no sirven para desagregar Cali. Es lo que se revisó al construir la sección
de fuera de la fuerza de trabajo.

### Juventud — `anexGEIHMLJ<trimestre>.xlsx` · 12 hojas

| | hoja | qué trae | nivel | serie |
|---|---|---|---|---|
| **USA** | `23 ciudades trim móvil` | tasas y niveles 15-28 | 23 ciudades | trim. móvil 2007– |
| **USA** | `13 ciudades trimestre móvil` | ídem | 13 ciudades | trim. móvil 2007– |
| **USA** | ` Tnal trimestre móvil` | ídem *(empieza con espacio)* | nacional | trim. móvil 2007– |
| | `PoscOcup trim móvil 13 ciudades` | **posición ocupacional juvenil** | 13 ciudades | trim. móvil 2007– |
| | `PoscOcup trim móvil Tnal` | ídem | nacional | trim. móvil 2007– |
| | `Ocup ramas trim 13 ciuda CIIU4` | ramas CIIU 4 juvenil | 13 ciudades | trim. móvil 2015– |
| | `Ocup ramas trim Tnal CIIU4` | ídem | nacional | trim. móvil 2015– |
| | `Jóvenes_NOE Tnal` | **NINI: ni estudian ni trabajan** | nacional | trim. móvil 2007– |
| | `Índice`, `Ficha metodológica`, `Código_SAS`, `Errores relativos` | documentación | — | — |

`Jóvenes_NOE Tnal` es la hoja de los NINI. Solo nacional, que es la razón por la
que quedaron fuera del tablero.

### Informalidad — `anexGEIHEISS<trimestre>.xlsx` · 19 hojas

Todas las de datos arrancan en 2021 y todas traen nacional + 13 + 23 ciudades.

| | hoja | qué trae |
|---|---|---|
| **USA** | `Prop informalidad` | proporción de informalidad, **por ciudad** |
| **USA** | `Ciudades` | ocupados total / formal / informal, **por ciudad** |
| | `Sexo` | ocupados formal/informal **por sexo** |
| | `Posición ocupacional` | formal/informal **por posición** |
| | `Educación ` | formal/informal por nivel educativo |
| | `Ramas de actividad CIIU 4 A.C` | formal/informal por rama |
| | `Tamaño de empresa` | formal/informal por tamaño de empresa |
| | `Lugar de trabajo` | formal/informal por lugar de trabajo |
| | `Seguridad social Tnal` / `13 ciudades ` | afiliación a salud y pensión |
| | `Seguridad social Tnal sexo` / `13C sexo` | afiliación por sexo |
| | `Grandes dominios ` | ocupados formal/informal, serie mensual |
| | `Total nacional` | ocupados formal/informal, nacional y ruralidad |
| | `Indice`, `Ficha Metodológica`, `Código_SAS`, `Código_STATA`, `Errores relativos` | documentación |

**Las hojas de corte de EISS solo traen agregados**, no ciudades. Para cualquier
desglose de informalidad a nivel Cali, la única fuente es `Ciudades`.

### Lo más aprovechable que hay sin usar

Ordenado por lo que aportaría a un tablero centrado en Cali:

1. **`Ocupados 23 Ciudades_rama_Trim`** (general) — ramas de actividad **por
   ciudad**, desde 2015. Es la única hoja de ramas con desglose por ciudad, así
   que es la que permitiría una sección de estructura sectorial de Cali.
   *(Las nacionales de fuera de la fuerza y de posición ocupacional ya se leen.)*
2. **`PoscOcup trim móvil 13 ciudades`** (juventud) — posición ocupacional
   juvenil. Solo agregado de 13 ciudades, no Cali.
3. **`Pos ocup 13 Ciud`** y **`FFT 13 Ciud`** (sexo) — los cortes por sexo de
   posición ocupacional y de fuera de la fuerza. Solo agregado.
4. **`Jóvenes_NOE Tnal`** (juventud) — NINI, solo nacional.

Regla práctica: si la hoja no dice "ciudades" en el nombre y en la cabecera de
sus bloques, casi seguro solo trae agregados y no sirve para hablar de Cali.

---

## Identidad visual

Sale del **Nexus Design System**, el manual de identidad de la CCC (versión 6.2,
mayo de 2026). Todos los colores están declarados con su nombre de marca en el
bloque `:root` al comienzo de `index.html`.

**Paleta principal:** azul sereno `#12176B`, azul pacífico `#253D90`, azul
farallones `#6FBCFF`, blanco maceta `#FAFAFA`.

**Paleta secundaria:** violeta guayacán `#5F27B5`, verde feijó `#65D7B7`,
chontaduro `#F2661F`, verde viche `#99DD3A`, magenta arrebol `#EF0074`.

Cada sección tiene su momento cromático en la constante `TEMAS`.

### Reglas del manual, ya aplicadas

- **Proporción 95 / 5.** La paleta principal domina la composición; el color
  temático es acento, no relleno. Por eso las barras de ranking son azules
  aunque la sección sea violeta o naranja.
- **Gradaciones solo verticales (90°), con el tono oscuro en la base.**
- **Extremos redondeados** en barras y líneas.
- **Datos ordenados por tamaño**, de mayor a menor.
- **Titulares sin mayúsculas sostenidas y sin itálicas.** El manual es
  explícito: las mayúsculas se leen como un grito y chocan con la cercanía que
  busca la marca. Las itálicas están prohibidas en la tipografía principal.
- **Números tabulares** en tablas y gráficas.

### Tipografía

Savior Sans Expanded (Sudtipos) para títulos, Libertad (TipoType) para texto.
Ambas comerciales. Los `@font-face` ya están declarados apuntando a
`docs/assets/fonts/`; apenas aparezcan los `.woff2` entran solas.

Mientras tanto: **Encode Sans Expanded** sustituye a Savior Sans Expanded y
**Source Sans 3** a Libertad, desde Google Fonts.

Advertencia para la CCC: la licencia de escritorio de esas fuentes no cubre
publicarlas en un sitio web. Se necesita licencia *webfont*.

### Morfologías

Los trazos son **el arte original de la marca**, extraído de
`marca/CCC_PlantillaPPTX.pptx` (slide 4) y guardado en la constante
`MORFOLOGIAS` de `index.html`. Ya no son una interpretación.

Las reglas, verificadas contra el brandbook (págs. 79-86):

- Los aros nacen del concepto **Nexo Vital**: tres aros por los tres motores de
  la CCC — capital social, empresas esenciales, conexión global.
- Se **fragmentan en seis partes iguales**. De ahí sale el arco, que es la
  unidad mínima y existe en **tres tamaños**, uno por aro.
- **Un arco solo lleva todas sus esquinas redondeadas.**
- **En composición, las esquinas que se tocan o se alinean van RECTAS**; las
  que quedan libres conservan el redondeo. Esto es más preciso de lo que decía
  antes esta nota ("al menos una esquina en contacto"): lo que manda no es que
  se toquen, sino cómo se resuelve la esquina cuando se tocan.
- Las composiciones van **de uno a tres arcos**, y pueden mezclar arcos de
  distintos tamaños.

**Los colores no se copian del arte.** El original viene siempre en azules;
cada trazo guarda su nivel de tono (0 el más oscuro, 2 el más claro) y quien
llama a `arcos()` decide qué color va en cada nivel. Así cada sección conserva
su momento cromático. Por eso `TEMAS` tiene un tercer tono, `claro`, tomado de
las escalas UI del Nexus que ya estaban en `:root`.

En el riel azul la jerarquía **se invierte**: el trazo que en el arte es el más
oscuro se dibuja con el tono más claro del tema, o desaparece contra el fondo.

El azul sereno del arte venía como `#12186B`, un dígito por debajo del
`#12176B` que fija el brandbook. Se normalizó. Es una inconsistencia del PPTX,
no un cambio de marca: sus propios íconos de redes traen el valor bueno. Lo
mismo con el violeta de los íconos, `#5E26B5` contra `#5F27B5`.

---

## Que esto se mantenga vivo

Este es el requisito central del proyecto, no un extra: el tablero tiene que
actualizarse **cada mes con las cifras nuevas, sin que nadie tenga que
acordarse de hacerlo**, y quedar publicado en el sitio de la CCC.

### Dónde está hoy

Cerrado. `descargar.py` trae los cuatro anexos del DANE y el workflow corre
solo todos los días a las 9 de la mañana. Nadie tiene que acordarse de nada.

```
[cron diario] -> descargar.py -> etl.py -> verificar.py -> GitHub Pages
                      |              |          |
                   nada nuevo?    falla?     falla?
                    termina       issue      issue, NO publica
```

### Las URLs del DANE

Los cuatro patrones están **comprobados contra el portal**, no supuestos:

```
general        anex-GEIH-{mes}{anio}.xlsx              anex-GEIH-jun2026.xlsx
informalidad   anex-GEIHEISS-{trimestre}.xlsx          anex-GEIHEISS-abr-jun2026.xlsx
sexo           anex-GEIHMLS-{trimestre}.xlsx           anex-GEIHMLS-abr-jun2026.xlsx
juventud       anex-GEIHMLJ-{trimestre}.xlsx           anex-GEIHMLJ-abr-jun2026.xlsx
```

Todos cuelgan de `https://www.dane.gov.co/files/operaciones/GEIH/`. Ojo con
tres cosas que no se adivinan:

1. **No hay guion entre `GEIH` y el módulo.** Es `anex-GEIHEISS-`, no
   `anex-GEIH-EISS-`. Esa segunda forma da 404.

2. **El general se nombra por el mes de cierre; los otros tres, por el
   trimestre completo.** El mismo período es `jun2026` para uno y
   `abr-jun2026` para los otros.

3. **Cuando el trimestre cruza el fin de año, cada extremo carga el suyo.**

   ```
   abr-jun2026        mismo año
   dic2025-feb2026    a caballo entre dos años
   dic-feb2026        ← 404. Es la forma que uno escribiría por analogía.
   ```

   Esto muerde tres meses al año: los trimestres que cierran en enero, febrero
   y marzo. `nombre_esperado()` en `descargar.py` lo maneja, y hay una prueba
   que lo cubre.

El patrón se mantiene estable desde abril de 2023; antes vivían en otra ruta y
con otro nombre. Por eso `descargar.py` no confía solo en el patrón: si la URL
directa da 404, lee la página del módulo y saca el enlace de ahí. Cuidado al
tocar ese respaldo, porque en las mismas páginas cuelgan el anexo
desestacionalizado, los de RELAB y el de economía creativa, que este tablero no
usa; el filtro por prefijo exacto es lo que los deja fuera.

### Por qué espera a que estén los cuatro

`descargar.py` no actualiza nada hasta que los cuatro módulos existen **para el
mismo mes de cierre**. No es prudencia de más:

El módulo general fija la grilla de períodos del ETL (`cod_tm`). Informalidad
se realinea con `alinear()`, pero **sexo y juventud se leen sin realinear**. Si
uno llega un mes tarde, sus series quedan más cortas que la grilla y
`verificar.py` lo tumba con "todas las series miden lo mismo que la grilla".

Es decir: la red de seguridad funciona, pero saltaría en falso cada mes que el
DANE se desacompase. Antes que enseñar a ignorar una alarma roja, se espera.

### Los códigos de salida son la interfaz

`descargar.py` le habla al workflow por el código de salida. No son adorno:

| código | significa | qué hace el workflow |
|--------|-----------|----------------------|
| `0` | hay anexos nuevos | ETL, verificar, comitear, publicar |
| `2` | nada que hacer: el DANE no ha publicado, o ya estamos al día | termina en silencio |
| `1` | error de verdad | abre un *issue*, no publica |

Un corte de red devuelve `2`, no `1`. Un cron diario contra un portal público
se va a topar con caídas, y una caída no es motivo para despertar a nadie:
mañana lo vuelve a intentar. Lo que sí devuelve `1` es un archivo corrupto —
cuando el portal está en mantenimiento contesta una página de error con código
200 y extensión `.xlsx`, y esa página **no** puede entrar a `datos/`. Por eso
se comprueba que cada descarga sea un ZIP con un `xl/` adentro.

**La regla que no se negocia:** si `verificar.py` falla, el flujo **no
publica**. Es preferible que el sitio muestre las cifras del mes pasado a que
muestre cifras equivocadas con el logo de la Cámara encima. El workflow abre un
*issue* (y comenta en el que ya esté abierto, en vez de abrir uno nuevo cada
día).

### Qué queda de los .xlsx descargados

Se comitean. Para una entidad que cita cifras públicamente la trazabilidad pesa
más que los ~14 MB al año de historial.

Además `datos/historial.csv` guarda un renglón por descarga con fecha, cierre,
módulo, nombre, **sha256 y URL de origen**. Con eso se puede volver a bajar el
archivo meses después y comprobar que es exactamente el que produjo las cifras
publicadas.

Si algún día el historial pesa demasiado, el `historial.csv` es lo que permite
dejar de comitear los `.xlsx` sin perder la auditoría.

### Certificados

`descargar.py` usa `certifi` **solo si el Python que lo corre no trae almacén
de certificados** (`ssl.get_default_verify_paths().cafile` es `None`, que pasa
en algunos Python de macOS). En Linux, que es donde corre el workflow, no hace
falta y no se usa. Nunca se apaga la verificación: da lo mismo que sean cifras
públicas, bajarlas sin verificar el certificado sería confiar en cualquiera que
se meta en medio.

Si en tu máquina toda descarga falla con `self-signed certificate in
certificate chain`, no es el DANE: es tu Python. Se arregla con
`pip install certifi`.

### Nombres de archivo

`localizar_anexos()` normaliza el nombre quitando guiones, espacios y
paréntesis antes de clasificar. Eso hace que `anex-GEIH-jun2026.xlsx` (como lo
sirve el DANE) y `anexGEIHjun2026 (2).xlsx` (como lo guarda el navegador)
lleguen al mismo lugar. También ignora explícitamente los anexos vecinos que
el tablero no usa: desestacionalizado, RELAB y economía creativa.

Si aparece un módulo nuevo, va en esa misma función.

---

## Qué falta

Ordenado por lo que más aporta primero.

### Insumos de marca

Los originales están en `marca/`: `CCC_PlantillaPPTX.pptx` (53 MB),
`CCC_Brandbook_2026.pdf` (24 MB) y `fuentes/`. El `.pptx` es un ZIP y sus
imágenes viven en `ppt/media/`: **255 SVG y 258 PNG, ningún EMF**, así que no
hay que convertir nada.

Qué hay en cada slide: 1-2 logo (azul y blanco, cuatro proporciones cada uno),
3 morfologías para enmascarar, 4 morfologías para decorar, 5-7 íconos, 8 íconos
de redes.

Ya integrados: las morfologías del slide 4 y el logo blanco del slide 2.

1. **Queda pendiente, si algún día hace falta:**
   - Las **224 iconos** de los slides 5 a 8 (mediana ~1,2 KB). No se
     extrajeron porque hoy el tablero no tiene dónde ponerlos: la navegación
     usa las morfologías. Los 7 del slide 8 son de redes sociales y ya vienen
     en el azul sereno correcto.
   - Las **morfologías para enmascarar del slide 3**, que no son imágenes sino
     cuatro formas nativas de PowerPoint (`custGeom`). Convertirlas exige
     interpretar geometría DrawingML. Sirven para recortar fotografías, algo
     que este tablero no hace.

**`marca/fuentes/` está en `.gitignore`**, a propósito. Solo trae `.otf` y
`.ttf` — formato de escritorio —, no hay ningún archivo de licencia en la
carpeta, y las fuentes no declaran términos: el metadato de licencia viene
vacío y el copyright dice "All rights reserved". Comitearlas en un repo que se
hace público para GitHub Pages sería redistribuirlas.

### Publicación

**No hay trabajo de incrustación.** Se verificó la página del Visor de Datos de
la CCC (`ccc.org.co/informacion-y-estudios-economicos/visor-de-datos/`) y **no
incrusta tableros**: es una lista de botones que abren enlaces externos. Los
visores actuales viven en `app.powerbi.com` y `public.tableau.com`, y el único
`iframe` de la página es un video de YouTube.

Eso simplifica todo. El tablero vive en su propia URL y desde la página de la
CCC se enlaza, igual que los demás visores. No hace falta el script de
`postMessage` para la altura del `iframe` que se había previsto.

2. **Dejar andando GitHub Pages.** El workflow ya está completo (cron diario,
   descarga, ETL, verificación, *issue* al fallar), pero falta el paso manual
   que nadie puede automatizar: entrar a Settings -> Pages del repositorio y
   elegir **GitHub Actions** como origen. Hasta que alguien haga eso, el
   workflow corre y falla en el último paso.

   Publica en `https://cccjaguirre.github.io/Tablero-mercado-laboral/`.

   **El repositorio cambió de dueño en septiembre de 2026**, de una cuenta
   personal a la institucional `CCCJAGUIRRE`. La URL del repositorio redirige
   sola con un 301 permanente, pero **la de Pages no**: la dirección anterior
   devuelve 404 sin reenvío. Es el argumento más fuerte para activar el
   subdominio propio — un dominio de la CCC sobrevive a la próxima mudanza.

3. **Activar el subdominio propio**, `observatoriolaboral.ccc.org.co`.

   **El orden importa y hacerlo al revés tumba el sitio.** Con un archivo
   `CNAME` presente, GitHub Pages redirige `cccjaguirre.github.io` al dominio
   propio; si el DNS todavía no resuelve, el tablero queda inalcanzable por
   las dos rutas. Por eso el archivo está preparado como
   `docs/CNAME.pendiente` y **no** como `docs/CNAME`.

   La secuencia:

   1. Dejar andando Pages (punto 2) y comprobar que el tablero abre en la URL
      de `github.io`.
   2. Pedirle a TI de la CCC este registro DNS:

      ```
      Tipo    CNAME
      Nombre  observatoriolaboral
      Valor   cccjaguirre.github.io
      TTL     3600
      ```

   3. Cuando `dig observatoriolaboral.ccc.org.co` responda, y solo entonces:

      ```bash
      git mv docs/CNAME.pendiente docs/CNAME
      git commit -m "Activar el subdominio observatoriolaboral.ccc.org.co"
      git push
      ```

   4. En Settings -> Pages, marcar **Enforce HTTPS** cuando GitHub termine de
      emitir el certificado (tarda unos minutos).

4. **Pasarle al equipo de web el texto del botón.** Redactado y listo en
   `BOTON-VISOR.md`, siguiendo el estilo de los que ya están en esa
   página. Falta mandárselo cuando la URL definitiva esté en pie.

### Calidad

5. **Accesibilidad.** Las gráficas SVG necesitan `<title>` y `aria-label`
   descriptivos, y una alternativa en tabla para lectores de pantalla. Revisar
   contraste de los textos secundarios sobre blanco maceta.

6. **Metadatos.** `og:image`, `og:description`, favicon con el isotipo. Cuando
   alguien comparta el enlace en LinkedIn o WhatsApp, tiene que verse la marca.

7. **Peso.** `datos.json` pesa 1,75 MB (unos 400 KB comprimido). Se puede
   bajar bastante separando el archivo por módulo y cargando bajo demanda, o
   recortando la precisión de los niveles. No es urgente, pero en conexiones
   lentas se nota.

### Referencia de diseño

8. **Revisar el monitor de la Secretaría de Desarrollo Económico de Bogotá**
   (`https://observatorio.desarrolloeconomico.gov.co/monitor-mercado-laboral-en-cifras/`),
   que es la referencia que pidió el cliente. Extraer ideas de estructura y
   navegación, no de estética: la identidad visual acá es la de la CCC.

---

## Cómo verificar antes de dar algo por hecho

```bash
python etl.py && python verificar.py
```

Y abrir el tablero de verdad en un navegador. Los errores que importan —
etiquetas encimadas, series que no pintan, paneles vacíos — no salen en la
consola. Recorrer las siete secciones en los dos modos temporales, cambiar
período, agregar y quitar ciudades, y mirarlo en ancho de celular.

---

## Cómo trabajar aquí

- **El español es el idioma del proyecto.** Interfaz, comentarios, nombres de
  variables, mensajes de commit. Ya está así; mantenerlo.
- **Los comentarios explican por qué, no qué.** Los que hay marcan las
  decisiones difíciles: por qué un cero no es un dato, por qué no se promedian
  tasas, por qué el SVG mide el ancho real del panel. Ese es el estándar.
- **Ante una cifra rara, sospecha primero de la fuente.** Los anexos del DANE
  tienen rellenos, cambios de metodología y convenciones inconsistentes de un
  año a otro. Ya aparecieron tres.
- **Antes de concluir que un dato no existe, agota la búsqueda.** Van tres veces
  que se dio por inexistente algo que sí estaba, siempre por la misma causa: se
  busca por etiqueta y el DANE escribe la misma cosa de varias formas. El
  procedimiento:

  1. **Recorre la hoja completa hasta la última fila**, no hasta donde esperas
     que terminen los bloques. Los agregados van al final, después de las
     ciudades: en el anexo general, el de 23 ciudades está en la fila 485 de
     515; en el de sexo, en la 423 de 448.
  2. **Lista todas las grafías que aparecen y compáralas** contra la tabla de
     alias, en vez de asumir que las cubre.
  3. **Si un módulo no trae un agregado que otros sí, sospecha de la lectura
     antes que del archivo.** Esa asimetría casi siempre es un bug propio, no
     una laguna del DANE.

  Los tres síntomas fueron distintos — "faltan hojas", "faltan grafías", "no
  existe el dato" — pero **la causa era la misma línea**: `detectar_bloques()`
  filtraba por nombre literal antes de canonizar, así que la tabla de alias
  nunca entraba en la decisión. Está explicado en la regla 5. Cuando aparezca
  un cuarto síntoma parecido, empieza por ahí: **¿se está normalizando antes de
  filtrar, o después?**
- **Nada de datos inventados ni de ejemplo.** Si algo no se puede calcular,
  queda vacío y se dice por qué.
