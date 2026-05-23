# Guía de recolección y separación de granos — para recolectores

> Hoja de campo para preparar las muestras de **café verde (sin tostar)** que
> alimentan el entrenamiento de almendra. Imprímela y tenla junto a las cubetas.
>
> Fuentes de verdad de este documento: `data/taxonomy.yaml`,
> `capture/protocol.md` y `capture/labeling-sop.md`. Si algo aquí no coincide
> con esos archivos, mandan ellos.

---

## 0. La idea clave (léela antes de empezar)

El modelo NO clasifica el grano por **varietal**. Clasifica cada grano en **dos
ejes separados e independientes**:

1. **Defecto** — ¿el grano está sano o tiene un defecto? (18 categorías SCA)
2. **Morfología** — ¿qué forma tiene el grano? (normal, caracol, etc.)

El **varietal, el origen y el proceso NO son una cubeta**: son **datos del lote**
que se anotan **una sola vez** para todo el costal/muestra (ver §4).

Por eso la regla de oro de organización es:

> **Un varietal = un lote separado.** No mezcles varietales en el mismo lote.
> Dentro de cada lote, reparte los granos en cubetas **por defecto** y anota
> aparte la **morfología**.

Así obtienes lo que pediste —separación por varietal— sin perder la etiqueta
que el modelo realmente necesita (defecto + morfología).

```
Costal del varietal "Bourbon"  ──►  Lote BOURBON-2026-05
                                      │
                                      ├─ Cubeta "Sano"
                                      ├─ Cubeta "Negro total"
                                      ├─ Cubeta "Agrio total"
                                      ├─ ... (una por defecto)
                                      └─ y en cada grano anotas su morfología
```

Trabaja **siempre con grano verde** (almendra sin tostar). Nunca uses el modelo
ni adivines: separa contra lo que ves y contra la carta de referencia SCA.

---

## 1. Cubetas por DEFECTO (eje principal — 18 categorías)

Cada grano va a **exactamente una** cubeta de defecto. Si dudas del tipo exacto pero
es claramente defectuoso, va a **"Defectuoso sin especificar"** — **no adivines**
el tipo.

Columnas de la tabla:
- **¿Pasa?** — `Aceptar` (sano) o `Rechazar` (defectuoso). El sorteador final
  expulsa los `Rechazar`.
- **Equiv. defecto SCA** — cuántos granos de esa clase cuenta la SCA como **un
  defecto completo** (informativo, para graduar la muestra; no afecta cómo
  separas).

### Grano bueno

| Cubeta | Qué buscar | ¿Pasa? | Equiv. defecto SCA |
|---|---|---|---|
| **Sano** (`sound`) | Almendra sana, sin defecto visible ni interno. Color y forma uniformes. | Aceptar | — |

### Categoría 1 — defectos PRIMARIOS (los graves; cada uno = 1 defecto completo)

> Estos son los que más arruinan la taza. **Búscalos a propósito** aunque sean
> raros (ver metas en §6) — no esperes a que aparezcan solos.

| Cubeta | Qué buscar | ¿Pasa? | Equiv. defecto SCA |
|---|---|---|---|
| **Negro total** (`full_black`) | Más de la mitad de la superficie negra; sobre-fermentación o sobre-maduración. | Rechazar | 1 grano = 1 defecto |
| **Agrio total** (`full_sour`) | Grano agrio café-rojizo a amarillo; daño por fermentación. | Rechazar | 1 grano = 1 defecto |
| **Cereza/cápsula seca** (`dried_cherry_pod`) | Grano todavía envuelto en la cereza/cápsula seca (mucílago y cáscara). | Rechazar | 1 grano = 1 defecto |
| **Dañado por hongo** (`fungus_damaged`) | Crecimiento fúngico café-amarillento sobre o dentro del grano. | Rechazar | 1 grano = 1 defecto |
| **Materia extraña** (`foreign_matter`) | Objeto que NO es café: piedra, palo, metal, etc. | Rechazar | 1 grano = 1 defecto |
| **Daño severo de insecto** (`severe_insect_damage`) | Tres o más perforaciones de broca, o barrenado extenso. | Rechazar | 5 granos = 1 defecto |

### Categoría 2 — defectos SECUNDARIOS (menos graves)

| Cubeta | Qué buscar | ¿Pasa? | Equiv. defecto SCA |
|---|---|---|---|
| **Negro parcial** (`partial_black`) | Menos de la mitad de la superficie negra. | Rechazar | 3 granos = 1 defecto |
| **Agrio parcial** (`partial_sour`) | Menos de la mitad con decoloración agria. | Rechazar | 3 granos = 1 defecto |
| **Pergamino** (`parchment`) | Grano parcial o totalmente envuelto en pergamino seco. | Rechazar | 5 granos = 1 defecto |
| **Flotador** (`floater`) | Grano pálido y de baja densidad; secado o almacenamiento deficiente. | Rechazar | 5 granos = 1 defecto |
| **Inmaduro** (`immature`) | Grano verde/no maduro con película plateada adherida; precursor del "quaker" del tueste. | Rechazar | 5 granos = 1 defecto |
| **Marchito** (`withered`) | Grano deforme y arrugado; estrés hídrico durante el desarrollo. | Rechazar | 5 granos = 1 defecto |
| **Concha/oreja** (`shell`) | Grano deforme en forma de concha; deformación genética. | Rechazar | 5 granos = 1 defecto |
| **Quebrado/mordido/cortado** (`broken_chipped_cut`) | Grano fragmentado o dañado mecánicamente. | Rechazar | 5 granos = 1 defecto |
| **Cascarilla/cáscara** (`hull_husk`) | Fragmento de cáscara o cascarilla seca. | Rechazar | 5 granos = 1 defecto |
| **Daño leve de insecto** (`slight_insect_damage`) | Una o dos perforaciones de broca. | Rechazar | 10 granos = 1 defecto |

### Comodín

| Cubeta | Qué buscar | ¿Pasa? | Equiv. defecto SCA |
|---|---|---|---|
| **Defectuoso sin especificar** (`defect_unspecified`) | Es claramente defectuoso pero no logras decir de qué tipo. **Úsala en lugar de adivinar.** | Rechazar | 5 granos = 1 defecto |

---

## 2. Eje de MORFOLOGÍA (forma — NO es un defecto)

La forma se anota **además** del defecto. Un caracol puede estar perfectamente
sano — es un grano normal de otra forma, **no un defecto**. Por eso la morfología
NO inflama la tasa de defectos.

Cómo manejarlo en la práctica: la mayoría de los granos serán **normal**. Cuando
veas una forma especial, **anótala en la etiqueta del grano** (o, si quieres,
ten una sub-cubeta de morfología dentro de la cubeta "Sano").

| Morfología | Qué buscar |
|---|---|
| **Normal** (`normal`) | Grano plano estándar (lo más común). |
| **Caracol** (`peaberry`) | Grano único redondeado (caracol/peaberry); forma normal y a menudo apreciada. |
| **Longberry** (`longberry`) | Grano alargado; rasgo de varietal/tamaño. |
| **Elefante** (`elephant`) | Dos granos fusionados (sobredimensionado). |

---

## 3. Qué escribir en la etiqueta de cada cubeta / grano

Cada cubeta debe quedar **bien etiquetada** y rastreable. Por grano (o por
cubeta, según tu flujo), registra:

- **Defecto** — la categoría de §1.
- **Morfología** — la categoría de §2 (`normal` salvo que sea claramente otra).
- **ID del clasificador** (`grader_id`) — quién clasificó.
- **Versión de taxonomía** (`taxonomy_version`) — la de `data/taxonomy.yaml`
  (hoy `schema_version: 1`).
- **Fecha/hora** (`timestamp`).
- **Notas** — texto libre para cualquier cosa ambigua o dudosa.

> Si más adelante usas el **protocolo de bandeja** (`capture/protocol.md`), la
> identidad del grano es su celda `(fila, columna)` en la bandeja, y las
> etiquetas van en `labels.csv` como `fila,columna,defecto,morfología`.

---

## 4. Datos del LOTE a registrar — **aquí va el varietal** (lo que te puede faltar)

Esto se anota **una sola vez por lote/muestra**, no por grano. Es la
"procedencia" (Paso 2 del protocolo de captura). **Es justo lo que pediste
sobre el varietal** y lo más fácil de olvidar:

| Dato | Ejemplo / unidad |
|---|---|
| **Finca** (`farm`) | nombre de la finca |
| **ID de lote** (`lot_id`) | identificador único del lote |
| **Varietal** (`varietal`) | p. ej. Typica, Bourbon, Caturra, Geisha, Catuaí… |
| **Proceso** (`process`) | lavado / natural / honey |
| **Altitud** (`altitude_m`) | metros sobre el nivel del mar |
| **Fecha de cosecha** (`harvest_date`) | AAAA-MM-DD |
| **Humedad** (`moisture_pct`) | % de humedad del grano |

Tamaño de muestra recomendado por la SCA: una porción **representativa de 350 g**
de un lote bien mezclado.

---

## 5. Reglas de oro (calidad del etiquetado)

La calidad de las etiquetas pone el techo a la calidad del modelo. Trátalo con
el mismo rigor que el código:

- **A ciegas:** clasifica contra el grano y la referencia SCA — **nunca** contra
  lo que diga un modelo.
- **Lo físico manda:** etiqueta el **grano físico**; las fotos solo apoyan.
- **Un eje a la vez:** primero el defecto, luego la morfología.
- **Si dudas del tipo de defecto → "Defectuoso sin especificar".** No adivines.
- **No descartes en silencio:** un grano dudoso o una foto mala se registra y se
  anota, no se tira sin dejar rastro.
- **Doble revisión:** al menos un **10 % al azar** de cada lote lo clasifica una
  segunda persona de forma independiente (control de acuerdo entre evaluadores).

---

## 6. Metas de recolección (cuántos granos)

- **Meta v1:** **≥ 200 granos por cada categoría de defecto**, balanceado.
- **Busca a propósito los defectos raros de Categoría 1** (negro total, agrio
  total, hongo, etc.) en lugar de esperar a que aparezcan.
- Después de cada sesión, revisa el conteo por categoría y orienta el siguiente
  muestreo hacia las categorías con pocos granos.

---

## 7. Cosas que se te pueden olvidar (checklist rápido)

- [ ] **Grano verde, sin tostar** — siempre.
- [ ] **No mezclar varietales** en un mismo lote (§0).
- [ ] **Anotar la procedencia del lote** (finca, varietal, proceso, altitud,
      cosecha, humedad) **antes** de empezar a separar (§4).
- [ ] **Materia extraña y cascarilla** también se recolectan: piedras, palos,
      metal, fragmentos de cáscara — son categorías válidas, no basura.
- [ ] **La morfología se anota aparte del defecto** (caracol/longberry/elefante
      no son defectos).
- [ ] **Caso dudoso → "Defectuoso sin especificar"** + nota; no inventes el tipo.
- [ ] **Buscar los defectos raros de Categoría 1** activamente (§6).
- [ ] **Mantener limpio** el área: la cascarilla/polvo contamina y dispersa la
      luz al fotografiar.
- [ ] **Etiquetar cada cubeta** con clasificador, fecha y versión de taxonomía (§3).

---

## 8. Notas técnicas importantes

- **Taxonomía PROVISIONAL.** Está alineada al *SCA Arabica Green Coffee Defect
  Handbook* pero **aún no verificada** contra el manual oficial. Los valores de
  "equivalente de defecto" pueden ajustarse. (`verified: false` en
  `data/taxonomy.yaml`.)
- **Es para café Arábica.** La mayor parte de los datos públicos existentes son
  Robusta; por eso esta recolección propietaria de Arábica es valiosa.
- **Graduación de muestra (informativa):** en 350 g, grado *specialty* exige
  **0 defectos completos de Categoría 1** y **máximo 5 de Categoría 2**. El
  modelo decide grano por grano; el grado se calcula sumando.
- Si una categoría te genera desacuerdos repetidos, **no es tu culpa: es un
  hueco de la taxonomía** — repórtalo para que se aclare o se ajuste
  `data/taxonomy.yaml`.
