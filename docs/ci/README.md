# Workflows de CI pendientes de publicacion

`security-suite.workflow.yml` es el workflow de GitHub Actions de la suite adversarial de Fase 2. Debe moverse sin cambios a:

```text
.github/workflows/security-suite.yml
```

No se publica desde este PR porque el token de la cuenta con permiso sobre el repositorio no incluye el scope OAuth `workflow`; GitHub rechaza cualquier push que cree o modifique un workflow. Tras ejecutar `gh auth refresh -h github.com -s workflow` con una cuenta que tenga acceso al repositorio, mover el fichero a la ruta anterior y abrir un PR independiente.

El workflow ejecuta `pytest tests/security` como gate bloqueante y `pytest tests` como job informativo sin `.env` en cada pull request y push a `main`. Ambos publican resumen y JUnit; los fallos de la suite completa no ocultan ni bloquean el gate adversarial mientras se corrigen los tests ajenos pendientes.
