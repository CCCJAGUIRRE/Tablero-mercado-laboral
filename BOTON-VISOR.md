# Texto del botón para la página del Visor de Datos

Para el equipo de web de la CCC. Va en
`ccc.org.co/informacion-y-estudios-economicos/visor-de-datos/`, entre los
visores vigentes — **no** en "Visores históricos".

Redactado en el estilo de los botones que ya están en esa página: sintagma
nominal, sin verbo, empezando por "Visor". Los vigentes usan la fórmula "Visor
de Datos ..."; este usa "Visor de seguimiento al ...", que es el nombre que la
CCC le puso al tablero.

---

## Lo que hay que pegar

**Título**

```
Visor de seguimiento al mercado laboral
```

**Descripción corta**

```
Indicadores de mercado laboral de Cali A.M. con fuente en la Gran Encuesta
Integrada de Hogares del DANE, comparables con las otras 22 ciudades y áreas
metropolitanas del país. Se actualiza cada mes.
```

**URL**

```
https://observatoriolaboral.ccc.org.co/
```

> Mientras el subdominio no esté activo, la URL provisional es
> `https://cccjaguirre.github.io/Tablero-mercado-laboral/`. Conviene esperar al
> subdominio antes de publicar el botón, para no tener que cambiarlo después.

**Abre en**: pestaña nueva, igual que los demás visores.

---

## Variantes, por si el título no cabe

El más largo que hay hoy en esa página es "Visor de Datos Tejido empresarial
del suroccidente de Colombia" (58 caracteres), así que el propuesto (39) entra
sin problema. Si aun así hiciera falta acortarlo:

| Variante | Caracteres |
|----------|-----------|
| Visor de seguimiento al mercado laboral | 39 |
| Visor de seguimiento al mercado laboral de Cali | 47 |
| Visor de mercado laboral | 24 |

## Descripción, versión de una línea

Si el diseño del botón solo admite un renglón:

```
Mercado laboral de Cali A.M. y las 22 ciudades comparables, con datos del DANE.
```

---

## Notas para quien lo publique

- **El enlace es externo**, como los de Power BI y Tableau que ya están ahí. No
  hay que incrustar nada: el tablero vive en su propia URL.
- **Se actualiza solo.** Un proceso automático revisa a diario si el DANE
  publicó cifras nuevas; si las hay y pasan las comprobaciones, el tablero se
  republica. Nadie tiene que tocar la página de la CCC cuando eso pase.
- **Funciona en celular.** No hace falta ofrecer un enlace distinto.
- El tablero permite mandar por correo un enlace que abra en una vista concreta
  — por ejemplo la informalidad de Cali en 2024 — porque la vista queda
  guardada en la propia URL.
