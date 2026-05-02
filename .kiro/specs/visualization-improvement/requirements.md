# Requirements Document

## Introduction

El sistema actual de visualización médica presenta problemas de calidad en las gráficas generadas, incluyendo conexión incorrecta de puntos temporales, generación inconsistente de visualizaciones, y código generado que no siempre es óptimo. Este documento especifica los requisitos para mejorar el sistema de visualización utilizando Claude Sonnet 4.5, manteniendo código legible, sencillo y sin elementos redundantes.

## Glossary

- **Sistema de Visualización**: Componente que genera gráficas médicas a partir de datos clínicos
- **Agente de Visualización**: Módulo que utiliza LLM para generar código de visualización
- **Datos Temporales**: Información médica con marca de tiempo (charttime)
- **Plotly**: Biblioteca de visualización interactiva en Python
- **Claude Sonnet 4.5**: Modelo de lenguaje de Anthropic para generación de código
- **Preprocesador de Datos**: Componente que limpia y valida datos antes de visualizar
- **Validador de Código**: Componente que verifica la calidad del código generado

## Requirements

### Requirement 1

**User Story:** Como médico, quiero que las gráficas temporales muestren los puntos conectados en orden cronológico correcto, para poder interpretar la evolución del paciente sin confusión.

#### Acceptance Criteria

1. WHEN el Sistema de Visualización recibe datos con marca temporal THEN el Sistema de Visualización SHALL ordenar los datos por charttime antes de generar la gráfica
2. WHEN el Sistema de Visualización genera una gráfica temporal THEN el Sistema de Visualización SHALL eliminar valores duplicados de tiempo para el mismo paciente
3. WHEN el Sistema de Visualización procesa datos temporales THEN el Sistema de Visualización SHALL convertir charttime a formato datetime si no lo está
4. WHEN el Sistema de Visualización detecta gaps temporales mayores a 24 horas THEN el Sistema de Visualización SHALL usar mode='lines+markers' en lugar de solo 'lines'
5. WHEN el Sistema de Visualización ordena datos temporales THEN el Sistema de Visualización SHALL preservar la relación entre todas las columnas de métricas

### Requirement 2

**User Story:** Como médico, quiero que el sistema siempre genere visualizaciones cuando hay datos disponibles, para no perder información valiosa por fallos técnicos.

#### Acceptance Criteria

1. WHEN el Agente de Visualización falla en generar código válido THEN el Agente de Visualización SHALL reintentar con un prompt simplificado
2. WHEN el código generado falla en ejecución THEN el Sistema de Visualización SHALL capturar el error y solicitar corrección al LLM
3. WHEN el Sistema de Visualización recibe datos válidos THEN el Sistema de Visualización SHALL generar al menos una visualización básica
4. WHEN el Agente de Visualización completa tres intentos fallidos THEN el Sistema de Visualización SHALL generar una visualización de respaldo usando plantillas predefinidas
5. WHEN el Sistema de Visualización usa visualización de respaldo THEN el Sistema de Visualización SHALL registrar el error en logs para análisis

### Requirement 3

**User Story:** Como desarrollador, quiero que el código generado sea limpio y eficiente, para mantener la calidad y legibilidad del sistema.

#### Acceptance Criteria

1. WHEN el Agente de Visualización genera código THEN el Agente de Visualización SHALL usar Claude Sonnet 4.5 como modelo de lenguaje
2. WHEN el Agente de Visualización construye el prompt THEN el Agente de Visualización SHALL incluir ejemplos de código limpio sin comentarios redundantes
3. WHEN el Agente de Visualización genera código THEN el código generado SHALL usar nombres de variables descriptivos en español
4. WHEN el código generado contiene imports THEN el código SHALL importar solo los módulos necesarios
5. WHEN el código generado crea figuras THEN el código SHALL usar configuración de layout consistente con template='plotly_white'

### Requirement 4

**User Story:** Como médico, quiero que las visualizaciones manejen correctamente valores faltantes y outliers, para obtener gráficas precisas y útiles.

#### Acceptance Criteria

1. WHEN el Preprocesador de Datos recibe un DataFrame THEN el Preprocesador de Datos SHALL identificar y reportar el porcentaje de valores nulos por columna
2. WHEN una métrica tiene más del 50% de valores nulos THEN el Preprocesador de Datos SHALL excluir esa métrica de la visualización
3. WHEN el Preprocesador de Datos detecta outliers usando IQR THEN el Preprocesador de Datos SHALL marcar pero no eliminar los outliers
4. WHEN el Sistema de Visualización procesa datos con outliers marcados THEN el Sistema de Visualización SHALL usar colores diferentes para outliers en la gráfica
5. WHEN el Preprocesador de Datos encuentra valores infinitos o NaN THEN el Preprocesador de Datos SHALL reemplazarlos con None para Plotly

### Requirement 5

**User Story:** Como médico, quiero que las gráficas tengan configuración visual consistente y profesional, para facilitar la interpretación de datos médicos.

#### Acceptance Criteria

1. WHEN el Sistema de Visualización genera cualquier gráfica THEN el Sistema de Visualización SHALL usar una paleta de colores médicos predefinida
2. WHEN el Sistema de Visualización configura ejes THEN el Sistema de Visualización SHALL incluir títulos descriptivos en español
3. WHEN el Sistema de Visualización genera gráficas temporales THEN el Sistema de Visualización SHALL formatear el eje X con formato de fecha legible
4. WHEN el Sistema de Visualización crea hover tooltips THEN el Sistema de Visualización SHALL incluir todas las métricas relevantes con unidades
5. WHEN el Sistema de Visualización configura el layout THEN el Sistema de Visualización SHALL usar hovermode='x unified' para gráficas temporales

### Requirement 6

**User Story:** Como desarrollador, quiero que el sistema valide el código generado antes de ejecutarlo, para prevenir errores y mejorar la calidad.

#### Acceptance Criteria

1. WHEN el Validador de Código recibe código generado THEN el Validador de Código SHALL verificar que existe la variable 'fig'
2. WHEN el Validador de Código analiza el código THEN el Validador de Código SHALL verificar que se usan las columnas correctas del DataFrame
3. WHEN el Validador de Código detecta uso de columnas inexistentes THEN el Validador de Código SHALL rechazar el código y solicitar regeneración
4. WHEN el código generado usa métodos de Plotly THEN el Validador de Código SHALL verificar que los métodos existen en la versión instalada
5. WHEN el Validador de Código aprueba el código THEN el Validador de Código SHALL retornar True con el código validado

### Requirement 7

**User Story:** Como médico, quiero que el sistema proporcione feedback claro cuando hay problemas con los datos, para entender qué información falta o es incorrecta.

#### Acceptance Criteria

1. WHEN el Sistema de Visualización recibe un DataFrame vacío THEN el Sistema de Visualización SHALL retornar un mensaje descriptivo indicando ausencia de datos
2. WHEN el Preprocesador de Datos detecta que todas las métricas solicitadas están ausentes THEN el Preprocesador de Datos SHALL retornar lista de métricas disponibles
3. WHEN el Sistema de Visualización falla en generar visualización THEN el Sistema de Visualización SHALL incluir el error específico en el mensaje de respuesta
4. WHEN el Sistema de Visualización completa exitosamente THEN el Sistema de Visualización SHALL incluir metadata sobre datos procesados
5. WHEN el Sistema de Visualización usa datos filtrados THEN el Sistema de Visualización SHALL informar cuántos registros fueron excluidos y por qué

### Requirement 8

**User Story:** Como desarrollador, quiero que el sistema use plantillas de código para casos comunes, para mejorar consistencia y velocidad de generación.

#### Acceptance Criteria

1. WHEN el Sistema de Visualización identifica un tipo de visualización común THEN el Sistema de Visualización SHALL verificar si existe una plantilla predefinida
2. WHEN existe una plantilla para el tipo solicitado THEN el Sistema de Visualización SHALL usar la plantilla como base y personalizarla con los datos
3. WHEN el Sistema de Visualización usa plantillas THEN el Sistema de Visualización SHALL mantener plantillas para timeline, comparison, distribution y scatter
4. WHEN una plantilla requiere personalización THEN el Sistema de Visualización SHALL usar el LLM solo para adaptar parámetros específicos
5. WHEN el Sistema de Visualización crea una nueva plantilla THEN el Sistema de Visualización SHALL validar que funciona con al menos tres conjuntos de datos diferentes

### Requirement 9

**User Story:** Como desarrollador, quiero que el sistema de visualización mejorado se integre con el código actual sin duplicación, para mantener un código base limpio y evitar confusión con código legacy.

#### Acceptance Criteria

1. WHEN el Sistema de Visualización se actualiza THEN el Sistema de Visualización SHALL modificar los archivos existentes en services/medical_agent/ en lugar de crear nuevos módulos
2. WHEN el Sistema de Visualización añade funcionalidad THEN el Sistema de Visualización SHALL reutilizar componentes existentes como code_executor.py y llm_manager.py
3. WHEN el Sistema de Visualización detecta código redundante THEN el Sistema de Visualización SHALL consolidar la funcionalidad en un solo módulo
4. WHEN el Sistema de Visualización implementa mejoras THEN el Sistema de Visualización SHALL mantener compatibilidad con las interfaces públicas existentes
5. WHEN el Sistema de Visualización completa la actualización THEN el Sistema de Visualización SHALL eliminar código legacy no utilizado

### Requirement 10

**User Story:** Como médico usando el chat unificado, quiero que las visualizaciones se generen automáticamente cuando son relevantes, para obtener insights visuales sin solicitudes explícitas.

#### Acceptance Criteria

1. WHEN el Chat Unificado detecta una consulta sobre tendencias temporales THEN el Chat Unificado SHALL invocar automáticamente la herramienta de visualización
2. WHEN el Chat Unificado obtiene datos numéricos de múltiples métricas THEN el Chat Unificado SHALL sugerir o generar visualizaciones comparativas
3. WHEN la herramienta de visualización retorna una imagen THEN el Chat Unificado SHALL incluir la visualización en la respuesta al usuario
4. WHEN el Chat Unificado genera múltiples visualizaciones THEN el Chat Unificado SHALL organizarlas de forma coherente en la interfaz
5. WHEN el Chat Unificado falla en generar visualización THEN el Chat Unificado SHALL continuar con la respuesta textual sin interrumpir el flujo
