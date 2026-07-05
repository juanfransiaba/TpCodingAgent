# Next Steps

## Bloqueados Por Credenciales

### RAG real

La implementacion ya existe, pero la ingesta real requiere una `OPENAI_API_KEY` valida.

Comando:

```powershell
$env:PYTHONPATH="src"
python -m coding_agent.rag.ingest
```

Resultado esperado:

```text
storage/vector_store/index.json
```

### Langfuse real

La integracion ya existe, pero para enviar trazas a Langfuse hay que configurar:

```env
LANGFUSE_SECRET_KEY=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Despues ejecutar al menos una tarea real del agente y capturar la traza desde Langfuse.

## Siguiente Trabajo Recomendado

1. Configurar keys correctas.
2. Ejecutar ingesta RAG.
3. Probar `rag_search` con una consulta sobre data leakage.
4. Ejecutar una tarea del agente que use RAG.
5. Ejecutar una tarea del agente que use memoria persistente.
6. Guardar evidencia en `docs/EVIDENCE_TEMPLATE.md`.
7. Sacar captura de Langfuse.
8. Redactar reflexion final.

## Prompts Sugeridos Para Pruebas

### Prueba RAG

```text
Usando la documentacion del RAG, explicame como evitar data leakage al calcular features temporales con pandas.
```

### Prueba Memoria

```text
Recorda que para este proyecto preferimos validar cambios con compileall antes de correr evaluaciones mas pesadas.
```

Luego:

```text
Segun la memoria del proyecto, que comando conviene correr primero para validar cambios?
```

### Prueba Cambio De Estrategia

```text
Intenta ejecutar la evaluacion del predictor. Si el comando requiere aprobacion o falla, explica que paso y propone una alternativa segura.
```
