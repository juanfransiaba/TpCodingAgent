# Football Predictor

Caso de uso del TP Final de Coding Agent Avanzado.

El objetivo es predecir un partido entre dos selecciones y devolver
probabilidades para:

```text
gana equipo A / empate / gana equipo B
```

Este caso sirve para demostrar que el coding agent puede inspeccionar un
proyecto real, correr comandos, usar RAG, registrar evidencia y mejorar codigo.

## Alcance

Incluido:

- Prediccion de un partido puntual entre dos selecciones.
- Baseline Elo.
- Modelo principal Poisson.
- Features historicas sin data leakage.
- Evaluacion con Brier score, log loss y RPS.

Fuera de alcance por ahora:

- Simular el Mundial completo.
- Scraping de planteles o valor de mercado.
- Lesiones, convocatorias o cuotas de apuestas.

## Datos

El predictor busca primero:

```text
cases/football_predictor/data/results.csv
```

Si no existe, usa:

```text
cases/football_predictor/data/results_sample.csv
```

El sample es solo para smoke tests. Para una corrida real hay que agregar el
dataset historico completo como `results.csv`.

Formato esperado:

```text
date
home_team
away_team
home_score
away_score
tournament
city
country
neutral
```

El dataset sugerido es compatible con "International football results" de
Kaggle, siempre que tenga esas columnas.

## Regla Anti-Leakage

Todas las features deben calcularse usando solo partidos anteriores a la fecha
que se predice.

Regla clave:

```python
history = df[df["date"] < match_date]
```

Nunca usar partidos con fecha igual o posterior al partido objetivo.

En evaluacion historica, el codigo usa:

```python
history = results.iloc[:index].copy()
```

Eso evita mirar el futuro porque el dataframe esta ordenado por fecha.

## Modelos

### Elo baseline

Calcula fuerza historica de cada equipo recorriendo partidos anteriores.
Convierte la diferencia de Elo en probabilidades de resultado.

### Poisson v1

Estima goles esperados para cada equipo usando:

- ataque reciente,
- defensa rival,
- diferencia Elo,
- ventaja de localia.

Luego suma probabilidades de scorelines para obtener:

- victoria equipo A,
- empate,
- victoria equipo B.

## Ejecutar Prediccion

Desde la raiz del repo:

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/predict_match.py --team-a Argentina --team-b France
```

Con fecha especifica:

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/predict_match.py --team-a Argentina --team-b France --date 2026-06-20
```

Con dataset explicito:

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/predict_match.py --team-a Argentina --team-b France --data cases/football_predictor/data/results.csv
```

## Ejecutar Evaluacion

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/evaluate.py --data cases/football_predictor/data/results.csv
```

Con el sample:

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/evaluate.py --data cases/football_predictor/data/results_sample.csv --min-history 10
```

Metricas:

- `brier_score`: menor es mejor.
- `log_loss`: menor es mejor.
- `rps`: menor es mejor.

La comparacion principal es:

```text
elo_baseline vs poisson_v1
```

## Validaciones Recomendadas

Compilar el codigo:

```powershell
.\.venv\Scripts\python.exe -m compileall cases\football_predictor
```

Correr prediccion smoke:

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/predict_match.py --team-a Argentina --team-b France --data cases/football_predictor/data/results_sample.csv
```

Correr evaluacion smoke:

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/evaluate.py --data cases/football_predictor/data/results_sample.csv --min-history 10
```

## Evidencia Para La Entrega

Cuando este `results.csv`, conviene guardar:

- salida de una prediccion real;
- salida de una evaluacion real;
- comparacion Elo vs Poisson;
- captura de Langfuse si el agente ejecuto o explico la tarea;
- explicacion de como se evita data leakage.

## Pendiente Principal Del Caso

Falta agregar el dataset real:

```text
cases/football_predictor/data/results.csv
```

Sin ese archivo, el caso funciona como smoke test, pero no alcanza para defender
metricas reales del modelo.
