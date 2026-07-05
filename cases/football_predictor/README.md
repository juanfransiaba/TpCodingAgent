# Football Predictor

Caso de uso del coding agent avanzado.

Predice un partido entre dos selecciones y devuelve **probabilidades** de gana A /
empate / gana B, comparando un modelo principal (Poisson de goles) contra un baseline
(Elo). Detalle de features, modelos y métricas en [`SPEC.md`](SPEC.md).

## Objetivo y criterio de "cumplido"

- **Objetivo:** producir una predicción probabilística reproducible y **evaluarla** con
  métricas de calibración (Brier, log loss, RPS) sobre datos históricos, sin data leakage.
- **Criterio verificable:** el pipeline corre de punta a punta sobre el dataset real y
  reporta la comparación Poisson vs Elo de forma honesta (ver "Resultados" abajo).

## Datos

El predictor busca, en orden:

```text
cases/football_predictor/data/results.csv          # dataset real
cases/football_predictor/data/results_sample.csv   # fallback: 35 partidos, solo smoke test
```

### Bajar el dataset real (martj42, la fuente del SPEC)

```bash
curl -sSL -o cases/football_predictor/data/results.csv \
  https://raw.githubusercontent.com/martj42/international_results/master/results.csv
```

El archivo trae partidos futuros del Mundial 2026 con score `NA` (sin jugar). Como
`data.py` parsea los goles a numérico, hay que **quitar las filas no jugadas** una vez:

```bash
python - <<'PY'
import pandas as pd
p = "cases/football_predictor/data/results.csv"
df = pd.read_csv(p)
for col in ("home_score", "away_score"):
    df[col] = pd.to_numeric(df[col], errors="coerce")
df = df.dropna(subset=["home_score", "away_score"])
df["home_score"] = df["home_score"].astype(int)
df["away_score"] = df["away_score"].astype(int)
df.to_csv(p, index=False)
print("Partidos jugados:", len(df))
PY
```

Resultado: ~49.495 partidos jugados (1872 → jul 2026), 336 selecciones, columnas
`date, home_team, away_team, home_score, away_score, tournament, city, country, neutral`.

## Uso

Predecir un partido:

```bash
PYTHONPATH=cases/football_predictor/src \
  python cases/football_predictor/scripts/predict_match.py --team-a Argentina --team-b France
# opcionales: --date 2026-06-11  --not-neutral --host-team Argentina  --data <ruta>
```

Evaluar los modelos. Como cada predicción recomputa el Elo sobre todo el historial previo
(O(n²)), sobre el dataset completo hay que acotar el **test set** a los últimos N partidos
(sigue usando todo el historial previo como features, así que **no hay leakage**):

```bash
PYTHONPATH=cases/football_predictor/src \
  python cases/football_predictor/scripts/evaluate.py --max-eval 300
```

Sin `--max-eval` evalúa todos los partidos posteriores a `--min-history` (inviable en el
dataset completo; útil solo con el sample).

## Resultados (dataset real, últimos 300 partidos, jul 2026)

| Métrica (menor = mejor) | Elo baseline | Poisson v1 (viejo) | **Poisson v2** |
| --- | --- | --- | --- |
| Brier    | 0.5479 | 0.5725 | **0.5221** |
| Log loss | 0.9264 | 0.9703 | **0.8903** |
| RPS      | 0.1770 | 0.1885 | **0.1642** |

**El modelo principal (Poisson v2) le gana al baseline Elo en las tres métricas** → criterio
cumplido. Cómo se llegó ahí (metodología sin data leakage ni overfitting):

1. **Diagnóstico.** La primera versión (`poisson_v1`) *perdía* contra el Elo simple: apilaba
   muchos factores multiplicativos clampeados (ataque, defensa, forma, h2h, localía) y metía
   el Elo —la señal mejor calibrada— como un ajuste débil de ±25%. Además el baseline Elo
   ignora la localía: predecía 0.395 de victoria local cuando la frecuencia real es 0.483.
2. **Rediseño (`poisson_v2`).** Los goles esperados se derivan de la **supremacía Elo**
   log-lineal `exp(γ·(elo_a − elo_b + localía)/400)`, con un peso moderado del volumen de
   goles reciente. La localía son +60 Elo al anfitrión (el mismo `HOME_ADVANTAGE` de `elo.py`).
3. **Selección honesta de parámetros.** `γ=0.9`, `home=60`, `w=0.5` se eligieron sobre una
   **ventana de validación** (partidos `[-1300:-300]`) y recién se reportó **una vez** sobre
   el test set de los últimos 300, que no se tocó. Las features de cada partido usan solo el
   historial previo → sin data leakage.

Ejemplo de predicción (Argentina vs France, neutral, jul 2026): Argentina 47.7% / empate 22.8%
/ France 29.5% (Elo 2076 vs 2016). La v1 daba un 65% inflado; la v2 es menos sobreconfiada.

> Reproducir la comparación: `python cases/football_predictor/scripts/evaluate.py --max-eval 300`.
