# Guía Completa del Sistema de Chat Unificad

---

## 📑 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Características Principales](#características-principales)
3. [Cómo Usar el Sistema](#cómo-usar-el-sistema)
4. [Ejemplos de Consultas](#ejemplos-de-consultas)
5. [Solución de Problemas](#solución-de-problemas)
6. [Preguntas Frecuentes](#preguntas-frecuentes)

---

# PARTE 1: GUÍA DE USUARIO

## Introducción

El Sistema de Chat Unificado de ChatHCE proporciona una interfaz única e inteligente para acceder tanto a datos de pacientes de la base de datos MIMIC-IV-ED como a documentos clínicos indexados. El sistema selecciona automáticamente las herramientas apropiadas según tu consulta, eliminando la necesidad de cambiar entre diferentes modos o interfaces.

## Características Principales

### 🎯 Interfaz Única
- **Un solo campo de entrada** para todas tus consultas
- **Selección automática de herramientas** - el agente decide qué usar
- **Sin cambio de modos** - simplemente escribe tu pregunta
- **Respuestas integradas** que combinan múltiples fuentes de datos

### 🔍 Capacidades de Búsqueda
- **Consultas de base de datos**: Información de pacientes, signos vitales, diagnósticos, medicamentos
- **Búsqueda de documentos**: Protocolos clínicos, guías, procedimientos
- **Consultas combinadas**: Integra datos de pacientes con guías clínicas
- **Visualizaciones**: Gráficas automáticas de tendencias y análisis

### 📄 Gestión de Documentos
- **Subir documentos**: PDF, DOCX, TXT
- **Indexación automática**: Los documentos se procesan y están disponibles inmediatamente
- **Búsqueda semántica**: Encuentra información relevante sin palabras clave exactas
- **Citas de fuentes**: Todas las respuestas incluyen referencias a documentos

## Cómo Usar el Sistema

### Inicio Rápido

1. **Accede a la aplicación**
   - Abre tu navegador web
   - Navega a la URL de ChatHCE
   - Inicia sesión con tus credenciales

2. **Selecciona "Chat Unificado"** en el menú lateral

3. **Escribe tu consulta** en el campo de entrada

4. **Presiona Enter** o haz clic en "Enviar"

5. **Revisa la respuesta** con interpretación clínica, fuentes y visualizaciones

### Tipos de Consultas

#### 1. Consultas de Pacientes (Base de Datos)

El sistema usa automáticamente la herramienta de base de datos cuando preguntas sobre:
- Pacientes específicos (por ID)
- Signos vitales
- Diagnósticos
- Medicamentos
- Visitas al departamento de emergencias

#### 2. Consultas de Documentos Clínicos (RAG)

El sistema usa automáticamente la herramienta RAG cuando preguntas sobre:
- Protocolos clínicos
- Guías de tratamiento
- Procedimientos médicos
- Información de medicamentos
- Mejores prácticas clínicas

#### 3. Consultas Combinadas (Base de Datos + RAG)

El sistema usa ambas herramientas cuando tu consulta requiere integrar datos de pacientes con guías clínicas.

#### 4. Consultas con Visualización

El sistema genera visualizaciones automáticamente cuando ayudarían a entender los datos.

### Gestión de Documentos

#### Subir Documentos

1. **Localiza el panel lateral** "Gestión de Documentos"
2. **Haz clic en "Browse files"** o arrastra archivos
3. **Selecciona tu documento** (PDF, DOCX, TXT)
4. **Espera la confirmación**
5. **Usa el documento inmediatamente**

#### Ver Documentos Indexados

El panel lateral muestra todos los documentos indexados con:
- Nombre del archivo
- Fecha de subida
- Especialidad (si está configurada)
- Botón de eliminar

#### Eliminar Documentos

1. Localiza el documento en la lista
2. Haz clic en el botón de eliminar (🗑️)
3. Confirma la eliminación

## Interpretación de Respuestas

### Estructura de Respuestas

```markdown
## 📊 [Título de la Respuesta]

### Resumen Ejecutivo
[Resumen breve de los hallazgos]

### Datos Clínicos Detallados
[Información detallada con datos específicos]

### Interpretación Clínica
[Análisis e interpretación profesional]

### Hallazgos Destacados
[Puntos clave y alertas]

### Visualizaciones
[Gráficas si son aplicables]

### Fuentes
[Referencias a documentos consultados]

---
**Herramientas usadas**: [Database Tool / RAG Tool / Ambas]
**Fuente**: Base de datos MIMIC-IV-ED / Documentos clínicos
```

### Indicadores de Herramientas

- 🔍 **Database Tool**: Consulta a base de datos MIMIC-IV-ED
- 📚 **RAG Tool**: Búsqueda en documentos clínicos
- 📊 **Visualization Tool**: Generación de gráficas
- 🔗 **Multiple Tools**: Combinación de herramientas

## Consejos y Mejores Prácticas

### Para Mejores Resultados

1. **Sé específico**
   - ✅ "Muestra los signos vitales del paciente 10014729 del 19 de marzo"
   - ❌ "Muestra signos vitales"

2. **Usa IDs de pacientes cuando estén disponibles**
   - ✅ "Paciente 10014729"
   - ❌ "El paciente de ayer"

3. **Pregunta en lenguaje natural**
   - ✅ "¿Cuál es el protocolo para hipertensión?"
   - ❌ "protocolo hipertensión"

4. **Solicita visualizaciones cuando sean útiles**
   - ✅ "Muestra gráfica de temperatura"
   - ✅ "Compara presión arterial en gráfica"

5. **Haz preguntas de seguimiento**
   - El sistema mantiene el contexto de la conversación
   - Los datos de consultas previas se reutilizan automáticamente (memoria conversacional)

### Optimización de Búsquedas

#### Para Consultas de Base de Datos
- Usa IDs específicos (subject_id, stay_id)
- Especifica rangos de fechas cuando sea relevante
- Menciona métricas específicas (temperatura, presión arterial, etc.)

#### Para Búsquedas de Documentos
- Usa términos médicos apropiados
- Menciona la especialidad si es relevante
- Pregunta por protocolos, guías o procedimientos específicos

#### Para Consultas Combinadas
- Combina IDs de pacientes con preguntas sobre guías
- Pregunta por comparaciones entre datos y estándares
- Solicita validación de tratamientos contra protocolos

---

# PARTE 2: EJEMPLOS DE CONSULTAS

## Consultas de Base de Datos

### Información de Pacientes

**Resumen General:**
```
"Muéstrame información del paciente 10014729"
"Dame un resumen del paciente 10014729"
"¿Qué datos tenemos del paciente 10014729?"
```

**Información Demográfica:**
```
"¿Cuál es el género y raza del paciente 10014729?"
"Muestra los datos demográficos del paciente 10014729"
```

**Historial de Visitas:**
```
"¿Cuántas visitas tiene el paciente 10014729?"
"Muestra el historial de visitas del paciente 10014729"
```

### Signos Vitales

**Generales:**
```
"Muestra los signos vitales del paciente 10014729"
"¿Cuáles son los signos vitales del paciente 10014729?"
```

**Específicos:**
```
"¿Cuál es la temperatura del paciente 10014729?"
"Muestra la presión arterial del paciente 10014729"
"¿Cuál es la frecuencia cardíaca del paciente 10014729?"
```

**Tendencias:**
```
"Analiza la tendencia de temperatura del paciente 10014729"
"¿Cómo ha variado la presión arterial del paciente 10014729?"
```

**Valores Anormales:**
```
"¿El paciente 10014729 tiene signos vitales anormales?"
"Identifica valores fuera de rango del paciente 10014729"
```

### Diagnósticos

**Lista:**
```
"¿Qué diagnósticos tiene el paciente 10014729?"
"Muestra los diagnósticos del paciente 10014729"
```

**Con Códigos ICD:**
```
"Muestra los diagnósticos del paciente 10014729 con códigos ICD"
"¿Cuáles son los códigos ICD del paciente 10014729?"
```

**Búsqueda Específica:**
```
"¿El paciente 10014729 tiene hipertensión?"
"¿Tiene diabetes el paciente 10014729?"
```

### Medicamentos

**Administrados:**
```
"¿Qué medicamentos recibió el paciente 10014729?"
"Lista los medicamentos del paciente 10014729"
```

**Específicos:**
```
"¿El paciente 10014729 recibió aspirina?"
"Busca administración de insulina al paciente 10014729"
```

**Horarios:**
```
"¿Cuándo se administró medicación al paciente 10014729?"
"Timeline de administración de medicamentos del paciente 10014729"
```

## Consultas de Documentos (RAG)

### Protocolos Clínicos

```
"¿Cuál es el protocolo para hipertensión?"
"Muestra el protocolo de manejo de diabetes"
"Protocolo de intubación de emergencia"
"¿Cuáles son los pasos del protocolo de hipertensión?"
```

### Guías de Tratamiento

```
"¿Cuáles son las guías de tratamiento para diabetes?"
"Muestra las guías de manejo de hipertensión"
"¿Cuál es el tratamiento recomendado para hipertensión severa?"
```

### Información de Medicamentos

```
"¿Cuál es la dosis de aspirina para adultos?"
"¿Cómo se administra la insulina?"
"¿Cuáles son los efectos secundarios de aspirina?"
```

### Procedimientos Médicos

```
"¿Cómo se realiza una intubación?"
"Procedimiento de reanimación cardiopulmonar"
"¿Cómo se interpreta un ECG?"
```

## Consultas Combinadas

### Validación de Tratamiento

```
"¿El tratamiento del paciente 10014729 sigue las guías para hipertensión?"
"Compara la medicación del paciente 10014729 con el protocolo estándar"
```

### Análisis de Diagnóstico

```
"¿El diagnóstico del paciente 10014729 coincide con las guías clínicas?"
"Analiza si los síntomas del paciente 10014729 corresponden al diagnóstico"
```

### Evaluación de Signos Vitales

```
"¿Los signos vitales del paciente 10014729 están dentro de los rangos normales según las guías?"
"Compara la presión arterial del paciente 10014729 con los valores de referencia"
```

## Consultas con Visualización

### Gráficas de Signos Vitales

```
"Muestra gráfica de temperatura del paciente 10014729"
"Gráfica de presión arterial del paciente 10014729"
"Gráfica de temperatura y frecuencia cardíaca del paciente 10014729"
```

### Gráficas Comparativas

```
"Compara temperatura y frecuencia cardíaca del paciente 10014729"
"Gráfica comparativa de presión sistólica vs diastólica"
```

### Gráficas de Distribución

```
"Muestra la distribución de diagnósticos"
"Gráfica de distribución de medicamentos administrados"
```

## Casos de Uso Completos

### Caso 1: Revisión Rápida de Paciente

```
1. "Muéstrame información del paciente 10014729"
2. "¿Tiene signos vitales anormales?"
3. "¿Qué medicamentos está recibiendo?"
4. "¿Su tratamiento sigue el protocolo?"
```

### Caso 2: Análisis Detallado

```
1. "Dame un resumen completo del paciente 10014729"
2. "Muestra gráfica de todos sus signos vitales"
3. "Analiza la evolución de su presión arterial"
4. "Compara su tratamiento con las guías de hipertensión"
5. "¿Qué ajustes recomiendas según el protocolo?"
```

### Caso 3: Consulta de Protocolo

```
1. "¿Cuál es el protocolo para hipertensión severa?"
2. "¿Cuáles son los pasos del tratamiento?"
3. "¿Qué medicamentos se recomiendan?"
4. "¿Cuáles son las contraindicaciones?"
```

---

# PARTE 3: SOLUCIÓN DE PROBLEMAS

## Problemas de Conexión

### Error: "No se puede conectar a la base de datos"

**Síntomas:**
- Mensaje de error al intentar consultar datos
- Timeout en consultas
- Respuestas vacías

**Soluciones:**

1. **Verificar conexión a internet**
2. **Verificar credenciales** en `.env`
3. **Verificar estado de Supabase**
4. **Reiniciar la aplicación**

### Error: "Error de autenticación"

**Soluciones:**

1. Verificar credenciales de usuario
2. Limpiar caché del navegador
3. Verificar configuración de autenticación

## Problemas de Consultas

### Error: "No se encontraron resultados"

**Causas:**
- ID de paciente incorrecto
- Paciente sin datos en el sistema
- Documentos no indexados
- Consulta mal formulada

**Soluciones:**

1. Verificar ID de paciente
2. Reformular la consulta
3. Verificar documentos indexados

### Error: "Consulta demasiado compleja"

**Soluciones:**

1. Simplificar la consulta
2. Limitar rango de datos
3. Usar filtros específicos

### Error: "Herramienta incorrecta seleccionada"

**Soluciones:**

1. Reformular con más contexto
2. Ser más explícito (mencionar "paciente", "protocolo", etc.)
3. Verificar el prompt del sistema

## Problemas de Documentos

### Error: "No se pudo procesar el documento"

**Causas:**
- Formato no soportado
- Archivo corrupto
- Tamaño excesivo
- Error en procesador

**Soluciones:**

1. Verificar formato (PDF, DOCX, TXT)
2. Verificar integridad del archivo
3. Reducir tamaño del archivo
4. Revisar logs de procesamiento

### Error: "Documento no encontrado en búsquedas"

**Soluciones:**

1. Verificar indexación
2. Reformular búsqueda
3. Re-indexar documento
4. Verificar servicio RAG

## Problemas de Visualización

### Error: "No se pudo generar la visualización"

**Causas:**
- Datos insuficientes
- Error en generación de código
- Error en ejecución
- Problema con Plotly

**Soluciones:**

1. Verificar datos disponibles
2. Especificar métricas claramente
3. Revisar logs de Visualization Agent
4. Verificar instalación de Plotly

### Error: "Código de visualización inválido"

**Soluciones:**

1. Revisar código generado en logs
2. Ajustar prompt de Visualization Agent
3. Reportar el problema

## Problemas de Rendimiento

### Problema: "Respuestas lentas"

**Causas:**
- Consultas complejas
- Caché no funcionando
- Conexión lenta
- Recursos limitados

**Soluciones:**

1. Verificar caché
2. Optimizar consultas
3. Verificar recursos del sistema
4. Reiniciar servicios

### Problema: "Memoria insuficiente"

**Soluciones:**

1. Limpiar caché
2. Reducir tamaño de contexto
3. Aumentar recursos

## Mensajes de Error Comunes

### "💾 Problema de Conexión"
**Acción**: Verifica conexión, credenciales, espera y reintenta

### "📚 No se encontraron documentos relevantes"
**Acción**: Sube documentos, reformula búsqueda, usa términos más generales

### "🔍 Paciente no encontrado"
**Acción**: Verifica ID, consulta lista de pacientes disponibles

### "⚠️ Error de validación de consulta"
**Acción**: Reformula consulta, evita caracteres especiales

### "📊 Error generando visualización"
**Acción**: Verifica datos disponibles, especifica métricas, revisa logs

## Diagnóstico Avanzado

### Habilitar Modo Debug

```bash
# En .env
DEBUG=true
LOG_LEVEL=DEBUG

# Reiniciar aplicación
streamlit run main.py
```

### Revisar Logs

```bash
tail -f logs/app.log
tail -f logs/error.log
tail -f logs/performance.log
```

### Verificar Configuración

```python
python check_config.py
python check_env.py
```

### Pruebas de Componentes

```bash
python test_unified_agent_simple.py
python test_database_tool.py
python test_rag_tool_unified.py
python test_visualization_agent.py
```

---

# PARTE 4: PREGUNTAS FRECUENTES

### ¿Necesito cambiar de modo para diferentes tipos de consultas?

No. El sistema selecciona automáticamente las herramientas apropiadas según tu consulta.

### ¿Puedo hacer preguntas de seguimiento?

Sí. El sistema mantiene el contexto de la conversación y reutiliza datos de consultas previas. Por ejemplo, si preguntas por un paciente y luego dices "muestra sus medicamentos", el sistema recuerda el ID del paciente.

### ¿Cómo sé qué herramientas se usaron?

Cada respuesta incluye indicadores de las herramientas usadas al final del mensaje.

### ¿Los documentos que subo son privados?

Los documentos se indexan y están disponibles para todos los usuarios del sistema. Consulta con tu administrador sobre políticas de privacidad.

### ¿Puedo exportar las respuestas?

Actualmente, puedes copiar y pegar las respuestas. La exportación a PDF está planificada para futuras versiones.

### ¿Qué tan actualizados están los datos?

Los datos de MIMIC-IV-ED son un conjunto de demostración con fechas futuras para anonimización. Los documentos clínicos reflejan el contenido que has subido.

### ¿El sistema puede diagnosticar pacientes?

No. El sistema es una herramienta de análisis y consulta, no un sistema de diagnóstico. Todas las decisiones clínicas deben ser tomadas por profesionales médicos calificados.

---

## Soporte y Contacto

Para soporte técnico o preguntas adicionales:
- Consulta la documentación técnica en `/docs`
- Contacta al administrador del sistema
- Revisa los logs de error si tienes acceso

## Actualizaciones y Mejoras Futuras

El sistema está en desarrollo continuo. Próximas características:
- Exportación de conversaciones a PDF
- Análisis comparativo de múltiples pacientes
- Sugerencias de consultas relacionadas
- Filtros avanzados por especialidad
- Soporte para imágenes médicas
- Entrada por voz

---

**Documento consolidado de**:
- UNIFIED_CHAT_USER_GUIDE.md
- UNIFIED_CHAT_QUERY_EXAMPLES.md
- UNIFIED_CHAT_TROUBLESHOOTING.md

**Versión**: 2.0  
**Última actualización**: Febrero 2026  
**Sistema**: ChatHCE - Chat Unificado  
**Modelo**: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
