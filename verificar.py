#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificacion del Observatorio de Mercado Laboral
================================================

Red de seguridad del proyecto. Comprueba que los datos generados por el ETL
siguen cumpliendo las decisiones metodologicas que costaron trabajo tomar.

Uso:
    python etl.py && python verificar.py

Devuelve codigo 0 si todo pasa, 1 si algo se rompio. Pensado para correr
tambien en CI, despues de cada actualizacion mensual.

Si una prueba falla, NO la ajustes para que pase. Cada una defiende una
decision explicada en CLAUDE.md. Si el DANE cambio algo de verdad, primero
entiende que cambio y luego actualiza la prueba a conciencia.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "docs" / "datos.json"

fallos = []
avisos = []


def check(nombre, condicion, detalle=""):
    if condicion:
        print(f"  ok    {nombre}")
    else:
        print(f"  FALLA {nombre}" + (f" -> {detalle}" if detalle else ""))
        fallos.append(nombre)


def ES_TASA(k):
    """Las tasas se recalculan en el promedio anual a partir de los niveles,
    asi que no tienen por que aparecer en los dos modos.

    Se reconocen por el nombre y no por una lista: una lista se queda vieja en
    cuanto alguien agrega un indicador, y entonces la prueba de mas abajo
    empieza a fallar por una razon que no es la suya.
    """
    return k.startswith(("pct_", "prop_")) or k in ("td", "to", "tgp", "ts")


def normalizar(txt):
    """Minusculas, sin tildes, sin espacios repetidos. Igual que en etl.py.

    Se repite aqui a proposito en vez de importar etl: verificar.py comprueba
    el resultado, y si usara la misma funcion que lo produjo dejaria de ser
    una comprobacion independiente.
    """
    s = unicodedata.normalize("NFKD", str(txt).strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).lower()


def aviso(nombre, detalle):
    print(f"  aviso {nombre} -> {detalle}")
    avisos.append(nombre)


def main():
    if not DATOS.exists():
        sys.exit("[ERROR] No existe docs/datos.json. Ejecuta antes: python etl.py")

    d = json.loads(DATOS.read_text(encoding="utf-8"))
    tm, an = d["periodos"]["tm"], d["periodos"]["an"]
    gen_tm = d["series"]["tm"]["general"]["Cali A.M."]
    gen_an = d["series"]["an"]["general"]["Cali A.M."]

    # ── 1. Estructura de la serie ────────────────────────────────────
    print("\n1. Estructura de las series")
    check("la serie de trimestres arranca en Ene-Mar 2007",
          tm["codigos"][0] == "2007-03", tm["codigos"][0])
    check("los trimestres moviles son consecutivos, uno por mes",
          all(
              (int(b[:4]) * 12 + int(b[5:])) - (int(a[:4]) * 12 + int(a[5:])) == 1
              for a, b in zip(tm["codigos"], tm["codigos"][1:])
          ))
    for modulo in ("general", "hombres", "mujeres", "juventud", "informalidad"):
        series = d["series"]["tm"][modulo]["Cali A.M."]
        largos = {len(s) for s in series.values()}
        check(f"{modulo}: todas las series miden lo mismo que la grilla",
              largos == {len(tm["codigos"])}, f"largos {largos}")

    # ── 2. Ceros del DANE tratados como dato faltante ────────────────
    print("\n2. Un cero exacto del DANE no es un dato")
    print("   (la subocupacion no se midio entre marzo y septiembre de 2020)")
    ceros = {
        f"{mod}.{k}": sum(1 for v in s if v == 0)
        for mod in d["series"]["tm"]
        for ciudad in d["series"]["tm"][mod]
        for k, s in d["series"]["tm"][mod][ciudad].items()
        if any(v == 0 for v in s)
    }
    check("ninguna serie contiene ceros exactos", not ceros, str(list(ceros)[:5]))

    i2020 = [tm["codigos"].index(f"2020-{m:02d}") for m in (3, 6, 9)]
    check("la subocupacion de 2020 queda vacia, no en cero",
          all(gen_tm["ts"][i] is None for i in i2020),
          str([gen_tm["ts"][i] for i in i2020]))
    check("el desempleo de 2020 si tiene dato",
          all(gen_tm["td"][i] is not None for i in i2020))

    # ── 3. Promedio anual: cuatro trimestres que no se traslapan ─────
    print("\n3. Promedio anual = Ene-Mar, Abr-Jun, Jul-Sep y Oct-Dic")
    i25 = an["codigos"].index("2025")
    cierres = [tm["codigos"].index(f"2025-{m:02d}") for m in (3, 6, 9, 12)]

    oc = sum(gen_tm["ocupados"][i] for i in cierres) / 4
    ft = sum(gen_tm["ft"][i] for i in cierres) / 4
    td_esperada = (ft - oc) / ft * 100

    check("los niveles se promedian sobre los cuatro trimestres de cierre",
          abs(gen_an["ocupados"][i25] - oc) < 0.05,
          f"{gen_an['ocupados'][i25]} vs {oc:.2f}")
    check("las tasas se recalculan desde los niveles, no se promedian",
          abs(gen_an["td"][i25] - td_esperada) < 0.02,
          f"{gen_an['td'][i25]} vs {td_esperada:.2f}")

    # El promedio de las tasas da otro numero: si coincidiera, algo se rompio
    td_promediada = sum(gen_tm["td"][i] for i in cierres) / 4
    check("el resultado NO coincide con promediar tasas",
          abs(gen_an["td"][i25] - td_promediada) > 0.005,
          "se esta promediando tasas en vez de recalcularlas")

    # ── 4. Contraste con la cifra publicada por el DANE ──────────────
    print("\n4. Contraste con lo que publica el DANE para 2025")
    check("desempleo de Cali A.M. en 2025 cerca de 8,746%",
          abs(gen_an["td"][i25] - 8.746) < 0.05, str(gen_an["td"][i25]))
    check("ocupados de Cali A.M. en 2025 cerca de 1.115.100",
          abs(gen_an["ocupados"][i25] - 1115.1) < 1.5, str(gen_an["ocupados"][i25]))

    # ── 5. Anio incompleto ───────────────────────────────────────────
    print("\n5. Un anio a medias no se compara contra uno entero")
    parciales = d["meta"].get("anios_parciales", [])
    if parciales:
        ip = an["codigos"].index(str(parciales[-1]))
        n = an["trimestres"][ip]
        check("el anio en curso queda marcado en la etiqueta",
              "(" in an["etiquetas"][ip], an["etiquetas"][ip])
        check("su referencia es el mismo tramo del anio anterior",
              an["referencia"][ip] and "(" in an["referencia"][ip],
              str(an["referencia"][ip]))
        ref = d["referencia_anual"]["general"]["Cali A.M."]["td"][ip]
        prev = [tm["codigos"].index(f"{parciales[-1]-1}-{m:02d}")
                for m in (3, 6, 9, 12)[:n]]
        oc_r = sum(gen_tm["ocupados"][i] for i in prev) / n
        ft_r = sum(gen_tm["ft"][i] for i in prev) / n
        check("la referencia usa solo los trimestres equivalentes",
              abs(ref - (ft_r - oc_r) / ft_r * 100) < 0.02,
              f"{ref} vs {(ft_r-oc_r)/ft_r*100:.2f}")
    else:
        aviso("no hay anios parciales", "no se pudo probar la comparacion equivalente")

    check("un anio completo con trimestres faltantes queda vacio",
          gen_an["ts"][an["codigos"].index("2020")] is None,
          "2020 no tiene los cuatro trimestres de subocupacion")

    # ── 6. Cobertura ─────────────────────────────────────────────────
    print("\n6. Cobertura")
    check("Cali A.M. esta en los cuatro modulos",
          all("Cali A.M." in d["series"]["tm"][m]
              for m in ("general", "hombres", "mujeres", "juventud", "informalidad")))
    check("hay al menos 23 ciudades", len(d["ciudades"]) >= 23, str(len(d["ciudades"])))
    inf = d["series"]["tm"]["informalidad"]["Cali A.M."]["prop_informalidad"]
    i2020_dic = tm["codigos"].index("2020-12")
    check("la informalidad no existe antes de 2021",
          all(v is None for v in inf[:i2020_dic + 1]))
    check("la informalidad si existe en el ultimo trimestre", inf[-1] is not None)

    # Los agregados venian escritos distinto en cada anexo: el modulo general
    # decia "Total nacional" y el de informalidad "Total Nacional". Eso parte
    # la misma entidad en dos filas del selector, cada una con la mitad de los
    # datos. titulo_ciudad() los resuelve contra una tabla de alias; esto
    # comprueba que ninguna variante nueva se vuelva a escapar.
    colisiones = {}
    for c in d["ciudades"]:
        colisiones.setdefault(normalizar(c), []).append(c)
    repetidas = {k: v for k, v in colisiones.items() if len(v) > 1}
    check("ninguna entidad aparece dos veces con distinta grafia",
          not repetidas,
          "; ".join(f"{k} -> {v}" for k, v in repetidas.items()))

    # Y que los tres agregados esten, escritos como toca
    for esperado in ("Total nacional", "Total 13 ciudades y A.M.",
                     "Total 23 ciudades y A.M."):
        check(f"'{esperado}' existe con esa grafia exacta",
              esperado in d["ciudades"],
              f"hay: {[c for c in d['ciudades'] if 'otal' in c]}")

    # ── 7. Modulos nuevos ────────────────────────────────────────────
    print("\n7. Fuera de la fuerza de trabajo y posicion ocupacional")
    i_ult = len(tm["codigos"]) - 1

    # Las dos hojas arrancan en 2010, no en 2007. El promedio anual no puede
    # inventarse los tres primeros anios.
    for mod, primer_anio in (("fuera", 2010), ("posicion", 2010)):
        ser = d["series"]["an"][mod]["Cali A.M."]
        clave = "ffft" if mod == "fuera" else "ocupados"
        con_dato = [an["codigos"][j] for j, v in enumerate(ser[clave]) if v is not None]
        check(f"{mod}: el promedio anual no inventa anios antes de {primer_anio}",
              con_dato and int(con_dato[0]) == primer_anio,
              f"primer anio con dato: {con_dato[0] if con_dato else 'ninguno'}")

    # Fuera de la fuerza de trabajo: las tres actividades suman el total
    f = d["series"]["tm"]["fuera"]["Cali A.M."]
    tot_f = f["ffft"][i_ult]
    partes_f = sum(f[k][i_ult] for k in ("estudiando", "hogar", "otros_ffft"))
    check("fuera: estudiando + hogar + otros = el total",
          abs(partes_f - tot_f) < 0.6, f"{partes_f:.1f} vs {tot_f:.1f} (miles)")
    check("fuera: Cali A.M. cerca de 684.200 personas",
          abs(tot_f * 1000 - 684_200) < 700, f"{tot_f * 1000:,.0f}")
    for k, esperado in (("hogar", 54.4), ("estudiando", 23.2), ("otros_ffft", 22.5)):
        pct = f[k][i_ult] / tot_f * 100
        check(f"fuera: {k} cerca de {esperado}%", abs(pct - esperado) < 0.15, f"{pct:.2f}%")

    # Posicion ocupacional: las categorias suman los ocupados, y esos ocupados
    # son los mismos del modulo general. Si esas dos cosas dejan de cuadrar,
    # el anexo cambio de forma.
    q = d["series"]["tm"]["posicion"]["Cali A.M."]
    oc_pos = q["ocupados"][i_ult]
    cats = ("particular", "gobierno", "domestico", "cuenta",
            "patron", "familiar", "jornalero", "otro_pos")
    suma = sum(q[k][i_ult] for k in cats if q.get(k) and q[k][i_ult] is not None)
    check("posicion: las categorias suman la poblacion ocupada",
          abs(suma - oc_pos) < 0.6, f"{suma:.1f} vs {oc_pos:.1f} (miles)")
    oc_gen = d["series"]["tm"]["general"]["Cali A.M."]["ocupados"][i_ult]
    check("posicion: sus ocupados son los mismos del modulo general",
          abs(oc_pos - oc_gen) < 0.6, f"{oc_pos:.1f} vs {oc_gen:.1f} (miles)")
    for k, esperado in (("particular", 56.0), ("cuenta", 34.4), ("domestico", 3.4),
                        ("patron", 2.6), ("gobierno", 2.4), ("familiar", 1.1)):
        pct = q[k][i_ult] / oc_pos * 100
        check(f"posicion: {k} cerca de {esperado}%", abs(pct - esperado) < 0.15, f"{pct:.2f}%")

    # "Otro" viene en cero exacto, que por la regla 1 no es un dato
    check("posicion: la categoria 'Otro' del DANE queda vacia, no en cero",
          q.get("otro_pos", [None])[i_ult] is None)

    # Cali tiene que estar en los dos modulos nuevos
    for mod in ("fuera", "posicion"):
        check(f"{mod}: Cali A.M. esta presente", "Cali A.M." in d["series"]["tm"][mod])

    # ── Agregados: el hueco que estuvo ahi desde el principio ────────
    #
    # El DANE reparte las MISMAS variables en varias hojas, una por nivel
    # geografico, Y escribe el mismo agregado de varias formas. Las dos cosas
    # juntas hicieron que se diera por inexistente, tres veces, un dato que si
    # estaba. Estas pruebas existen para que no vuelva a pasar en silencio.
    NACIONAL = ("general", "hombres", "mujeres", "juventud", "informalidad",
                "fuera", "posicion")
    TRECE = NACIONAL
    # Total 23 no existe en las hojas de fuera de la fuerza de trabajo (solo
    # 13 ciudades) ni en la de posicion ocupacional (termina en Sincelejo).
    # Comprobado recorriendo las dos hojas hasta la ultima fila.
    VEINTITRES = ("general", "hombres", "mujeres", "juventud", "informalidad")

    for agregado, modulos in (("Total nacional", NACIONAL),
                              ("Total 13 ciudades y A.M.", TRECE),
                              ("Total 23 ciudades y A.M.", VEINTITRES)):
        for mod in modulos:
            ind = d["series"]["tm"].get(mod, {}).get(agregado, {})
            vivos = [k for k, v in ind.items() if any(x is not None for x in v)]
            check(f"{mod}: '{agregado}' existe y trae datos",
                  len(vivos) >= 1, f"indicadores con dato: {len(vivos)}")

    # Y que no se colara el agregado de 10 ciudades, que el tablero no usa
    check("no entro el agregado de 10 ciudades",
          not [c for c in d["ciudades"] if "10 ciudades" in normalizar(c)],
          str([c for c in d["ciudades"] if "10" in c]))

    # Las hojas nacionales de fuera de la fuerza y de posicion vienen en serie
    # MENSUAL, y el ETL las pasa a trimestre movil promediando de a tres.
    # El modulo general publica las mismas dos variables a nivel nacional ya en
    # trimestre movil, asi que sirven de contraste independiente: si la
    # conversion se rompe, estas dos pruebas lo cazan.
    for mod, clave, etq in (("fuera", "ffft", "poblacion fuera de la fuerza"),
                            ("posicion", "ocupados", "ocupados")):
        conv = d["series"]["tm"][mod]["Total nacional"][clave]
        ofic = d["series"]["tm"]["general"]["Total nacional"][clave]
        difs = [abs(a - b) for a, b in zip(ofic, conv)
                if a is not None and b is not None]
        check(f"{mod}: el nacional convertido de mensual reproduce el oficial ({etq})",
              difs and max(difs) < 0.15,
              f"{len(difs)} periodos, diferencia maxima {max(difs) if difs else '-'}")

    # Un indicador de nivel que no este en NIVELES desaparece del promedio anual
    # sin avisar: la serie existe en trimestre movil y en anual no. Paso justo
    # eso al agregar estos dos modulos. Las tasas no aplican, porque el anual
    # las recalcula y algunas solo existen en uno de los dos modos.
    for mod in d["series"]["tm"]:
        en_tm = {k for k, v in d["series"]["tm"][mod].get("Cali A.M.", {}).items()
                 if any(x is not None for x in v)}
        en_an = set(d["series"]["an"].get(mod, {}).get("Cali A.M.", {}))
        faltan = {k for k in en_tm - en_an if not ES_TASA(k)}
        check(f"{mod}: ningun nivel se pierde en el promedio anual",
              not faltan, f"solo en trimestre movil: {sorted(faltan)}")

    # ── 8. Rangos plausibles ─────────────────────────────────────────
    print("\n8. Los numeros caen donde deben")
    for k, lo, hi in (("td", 3, 40), ("to", 30, 75), ("tgp", 45, 80),
                      ("pct_pet", 60, 90)):
        vals = [v for v in gen_tm[k] if v is not None]
        check(f"{k} entre {lo} y {hi}",
              vals and min(vals) >= lo and max(vals) <= hi,
              f"min {min(vals):.1f} max {max(vals):.1f}" if vals else "sin datos")
    ult = gen_tm["td"][-1]
    check("el ultimo trimestre trae dato de Cali", ult is not None)
    if len(gen_tm["td"]) > 13 and gen_tm["td"][-13] is not None:
        salto = abs(ult - gen_tm["td"][-13])
        if salto > 5:
            aviso("salto grande frente al mismo trimestre del anio pasado",
                  f"{salto:.1f} pp; revisa que los anexos sean los correctos")

    # ── Cierre ───────────────────────────────────────────────────────
    print("\n" + "=" * 62)
    print(f"Ultimo trimestre movil : {d['meta']['ultimo_tm']}")
    print(f"Ultimo anio            : {d['meta']['ultimo_anio']}")
    print(f"Ciudades               : {len(d['ciudades'])}")
    if avisos:
        print(f"Avisos                 : {len(avisos)}")
    if fallos:
        print(f"\nFALLARON {len(fallos)} prueba(s):")
        for f in fallos:
            print(f"  - {f}")
        print("\nNo publiques hasta resolverlo. Lee CLAUDE.md antes de tocar el ETL.")
        return 1
    print("\nTodo en orden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
