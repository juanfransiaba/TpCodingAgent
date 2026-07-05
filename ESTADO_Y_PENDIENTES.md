# Estado del TP y Pendientes

Documento para el equipo. Resume **qué ya está hecho y probado**, **cómo levantar el proyecto**, y **qué falta** para completar la entrega del TP Final de Coding Agent Avanzado.

> El código del agente ya estaba ~90% implementado. El trabajo que sigue es sobre todo **ejecutar, generar evidencia y escribir la parte narrativa** de la entrega.

---

## 1. Qué ya hicimos ✅

- **Entorno configurado y agente corriendo.** Se creó el `.venv`, se instalaron las dependencias (`requirements.txt`) y el agente arranca y responde correctamente conectándose a OpenAI.
- **`.env` armado** con las keys de OpenAI, Tavily y Langfuse. (No se commitea, está en `.gitignore`.)
- **RAG ingestado y funcionando.** Se corrió la ingesta: indexó **5 documentos / 8 chunks** en `storage/vector_store/index.json`. La tool `rag_search` recupera chunks con sus scores.
- **Observabilidad OK.** Las trazas se guardan localmente en `runs/traces/` y se suben a Langfuse (el error 401 inicial era por la config del `.env`, ya está resuelto).
- **Evidencia de tarea con RAG (entregable 6, tarea 1).** El agente respondió una consulta sobre *data leakage* usando `rag_search`, mostrando los fragmentos recuperados de `data_leakage.md` y `pandas.md` con sus scores.
- **Mejora concreta implementada y verificada (RAG-first).** Ver detalle abajo.

### Mejora implementada: RAG-first

**Problema detectado:** por defecto el agente se iba a `web_search` en vez de consultar el RAG local, incumpliendo la consigna ("consultar primero el RAG, web como fallback").

**Causa:** el `SYSTEM_PROMPT` (que usa el LLM principal del loop) no tenía la regla de priorizar `rag_search`. El subagente Researcher sí la tenía, pero ese solo arma contexto, no decide las tools.

**Cambio:** se agregaron dos reglas en `src/coding_agent/prompts/system_prompt.py`:
- llamar SIEMPRE a `rag_search` primero y usar `web_search` solo como fallback;
- mostrar qué chunks recuperó.

**Verificación (antes / después, misma pregunta):**
- Antes → `web_search` x5, ignoraba la doc local.
- Después → `rag_search`, respuesta desde la documentación local.

> Esto sirve como "mejora concreta documentada" **y** como material para la reflexión final.

---

## 2. Cómo levantar el proyecto (setup)

> ⚠️ El README principal tiene comandos de **Windows (PowerShell)**. Estos son los equivalentes para **macOS / Linux**.

```bash
# 1. Crear entorno virtual (una sola vez)
python3 -m venv .venv

# 2. Activarlo (cada vez que abrís una terminal nueva)
source .venv/bin/activate        # macOS/Linux
# .\.venv\Scripts\activate       # Windows

# 3. Instalar dependencias (una sola vez)
pip install -r requirements.txt

# 4. Crear el archivo .env copiando de .env.example y completar las keys
#    (OPENAI_API_KEY, TAVILY_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)

# 5. Ingestar el RAG (una vez, o cada vez que cambien los rag_docs)
export PYTHONPATH=src
python -m coding_agent.rag.ingest

# 6. Arrancar el agente
export PYTHONPATH=src
python -m coding_agent.main
```

Comandos del agente en el chat: `/plan`, `/supervision`, `/exit`.

### Notas importantes

- **Keys / `.env`:** nunca commitear el `.env`. Si alguien expone una key por error, revocarla y generar otra.
- **Langfuse región:** si da error `401 Unauthorized` al subir trazas, revisar que `LANGFUSE_BASE_URL` coincida con la región del proyecto (`https://cloud.langfuse.com` para Europa, `https://us.cloud.langfuse.com` para EEUU).
- **IntelliJ:** es un proyecto Python. Hace falta el plugin de Python y apuntar el intérprete al `.venv` (`.venv/bin/python`). Igual todo se puede correr desde la terminal.

---

## 3. Qué falta hacer ⏳

Ordenado por prioridad para la entrega. Los entregables entre paréntesis son los del enunciado.

### Alta prioridad

1. **Conseguir el dataset real de fútbol.**
   - Hoy solo está `data/results_sample.csv` (35 partidos, solo para smoke test).
   - El código busca `cases/football_predictor/data/results.csv` y espera el formato del dataset **"International football results from 1872 to 2024"** de Kaggle (mismas columnas exactas). Bajarlo, renombrarlo a `results.csv` y ponerlo en esa carpeta.

2. **Correr una predicción y una evaluación reales** con el dataset completo (entregable: resultado verificable).
   - `python cases/football_predictor/scripts/predict_match.py --team-a Argentina --team-b France`
   - `python cases/football_predictor/scripts/evaluate.py`
   - Objetivo: mostrar que el modelo Poisson le gana al baseline Elo en las métricas (Brier, log loss, RPS).

3. **Evidencia de 2 tareas ejecutadas (entregable 6).**
   - ✅ Tarea 1: consulta con RAG mostrando fuentes (ya hecha).
   - ⏳ Tarea 2: una tarea que use la **memoria persistente** del proyecto.

4. **Tarea de cambio de estrategia / pedir ayuda (entregable de pruebas).**
   - Diseñar una tarea donde el agente detecte que no tiene evidencia, se detenga o pida ayuda (ej: intentar correr un comando que requiere aprobación o que falla, y ver que propone alternativa).

5. **Capturas de Langfuse (entregable 7).**
   - Entrar al dashboard de Langfuse y capturar al menos **una traza completa** de ejecución (prompts, tools, tokens, latencia, costo).
   - Tip: anotar los `task_id` que imprime la terminal para cruzarlos con las trazas.

### Media / cierre

6. **Escribir la parte narrativa de la entrega (entregables 3, 4, 5, 8):**
   - Descripción del caso de uso y criterio de "cumplido".
   - Explicación de la arquitectura (agente principal + subagentes + estado compartido). *Ya hay base en `docs/ARCHITECTURE.md`.*
   - Documentación de la base RAG (fuentes, chunking, embeddings, almacenamiento).
   - **Reflexión final:** qué funcionó, qué falló, cuándo se detectaron loops o falta de evidencia, qué mejorarían. *(Tenemos buen material: el caso RAG-first, antes/después.)*

7. **Completar el README del caso** en `cases/football_predictor/`.

### Opcional (suma)

- Sistema de plugins de tools con autodescubrimiento (extra opcional del enunciado). Hoy hay wrappers estilo Command pero no autodescubrimiento.

---

## 4. Checklist rápido

- [x] Entorno + agente corriendo
- [x] `.env` con keys
- [x] RAG ingestado
- [x] Langfuse conectado
- [x] Evidencia tarea RAG (tarea 1)
- [x] Mejora RAG-first implementada y verificada
- [ ] Dataset real de fútbol
- [ ] Predicción + evaluación reales
- [ ] Evidencia tarea de memoria (tarea 2)
- [ ] Tarea de cambio de estrategia / pedir ayuda
- [ ] Capturas de Langfuse
- [ ] Textos de entrega (caso, arquitectura, RAG, reflexión)
- [ ] README del caso de fútbol
