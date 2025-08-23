
# HCE Analyzer Pro 2.0

## 🏥 Sistema Avanzado de Análisis de Historias Clínicas

HCE Analyzer Pro es una aplicación de vanguardia que utiliza inteligencia artificial para analizar historias clínicas médicas, proporcionando insights valiosos para profesionales de la salud.

## 🚀 Características Principales

### ✨ Funcionalidades Core
- **Análisis Inteligente de Historias Clínicas** - Procesamiento avanzado con IA
- **Sistema RAG** - Recuperación y generación aumentada para guías clínicas
- **Chat Clínico Inteligente** - Asistente IA especializado en medicina
- **Autenticación Segura** - Sistema robusto con Supabase
- **Procesamiento de Documentos** - Soporte para PDF, DOCX, TXT con Docling

### 🆕 Nuevas Funcionalidades v2.0
- **Sistema de Reportes Avanzados** - Generación automática de informes médicos
- **Dashboard de Métricas** - Estadísticas de uso y análisis en tiempo real
- **Sistema de Alertas** - Notificaciones inteligentes para casos críticos
- **Exportación Avanzada** - PDF, Excel, Word con plantillas profesionales
- **Sistema de Backup** - Respaldo automático y recuperación de datos
- **Análisis de Tendencias** - Identificación de patrones en historias clínicas
- **API REST Completa** - Endpoints para integración externa
- **Sistema de Logs** - Monitoreo y auditoría completa
- **Plantillas Médicas** - Templates para diferentes especialidades
- **Sistema de Notificaciones** - Email, SMS, push notifications

## 🏗️ Arquitectura Modular

```
hce_analyzer_pro/
├── src/                    # Código fuente principal
│   ├── core/              # Aplicación principal
│   ├── processors/        # Procesadores de documentos
│   └── analyzers/         # Analizadores de IA
├── utils/                 # Utilidades y helpers
│   ├── helpers/           # Funciones auxiliares
│   ├── validators/        # Validadores de datos
│   └── formatters/        # Formateadores de reportes
├── config/                # Configuraciones
├── services/              # Servicios de negocio
│   ├── auth/             # Autenticación
│   ├── reporting/        # Reportes
│   ├── alerts/           # Alertas
│   ├── backup/           # Respaldos
│   └── notifications/    # Notificaciones
├── models/                # Modelos de datos
├── api/                   # APIs y endpoints
│   ├── routes/           # Rutas de la API
│   └── middleware/       # Middleware personalizado
├── ui/                    # Componentes de interfaz
├── data/                  # Datos y almacenamiento
├── tests/                 # Pruebas unitarias
├── docs/                  # Documentación
├── scripts/               # Scripts de utilidad
└── logs/                  # Logs del sistema
```

## 🛠️ Tecnologías Utilizadas

### Backend
- **FastAPI** - Framework web moderno y rápido
- **Streamlit** - Interfaz de usuario interactiva
- **Pydantic** - Validación de datos y configuración
- **SQLite/Supabase** - Base de datos
- **ChromaDB** - Base de datos vectorial
- **Redis** - Cache y sesiones

### IA y ML
- **OpenAI GPT** - Modelos de lenguaje
- **Anthropic Claude** - Análisis avanzado
- **LangChain** - Framework de IA
- **Sentence Transformers** - Embeddings
- **Docling** - Procesamiento de documentos

### Utilidades
- **Pandas/NumPy** - Análisis de datos
- **Plotly** - Visualizaciones
- **ReportLab** - Generación de PDFs
- **Celery** - Tareas en segundo plano

## 🚀 Instalación y Configuración

### Prerrequisitos
- Python 3.11+
- Redis (opcional, para cache)
- Cuenta de Supabase
- API Keys de OpenAI/Anthropic

### Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd hce_analyzer_pro
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

5. **Ejecutar la aplicación**

**Streamlit (Interfaz Principal):**
```bash
streamlit run main.py
```

**FastAPI (API REST):**
```bash
python -m uvicorn api.main:app --reload
```

## 🔧 Configuración

### Variables de Entorno Principales

```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key

# IA APIs
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Aplicación
SECRET_KEY=your_secret_key
DEBUG=false
LOG_LEVEL=INFO

# Base de datos
CHROMA_PERSIST_DIR=./chroma_db

# Notificaciones
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_password

# Seguridad
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=5
RATE_LIMIT_PER_MINUTE=60
```

## 📊 Uso de la API

### Endpoints Principales

#### Análisis
```bash
# Subir documento
POST /api/v1/analysis/upload-document

# Analizar historia clínica
POST /api/v1/analysis/analyze-medical-record

# Chat clínico
POST /api/v1/analysis/clinical-chat
```

#### Reportes
```bash
# Generar reporte
POST /api/v1/reports/generate-patient-report

# Datos del dashboard
GET /api/v1/reports/dashboard-data

# Exportar reporte
POST /api/v1/reports/export-report
```

#### Alertas
```bash
# Alertas activas
GET /api/v1/alerts/active-alerts

# Reconocer alerta
POST /api/v1/alerts/acknowledge-alert/{alert_id}
```

### Ejemplo de Uso

```python
import requests

# Analizar historia clínica
response = requests.post(
    "http://localhost:8000/api/v1/analysis/analyze-medical-record",
    headers={"Authorization": "Bearer your_token"},
    json={
        "patient_id": "P12345",
        "medical_record": "Historia clínica del paciente...",
        "patient_info": {
            "name": "Juan Pérez",
            "age": 45,
            "gender": "male"
        }
    }
)

analysis_result = response.json()
```

## 🧪 Testing

```bash
# Ejecutar todas las pruebas
pytest

# Ejecutar con cobertura
pytest --cov=src --cov-report=html

# Pruebas específicas
pytest tests/unit/
pytest tests/integration/
```

## 📈 Monitoreo y Logs

### Logs del Sistema
- **Aplicación**: `logs/app.log`
- **Errores**: `logs/error.log`
- **Auditoría**: `logs/audit.log`

### Métricas Disponibles
- Análisis completados
- Tiempo de procesamiento
- Alertas generadas
- Uso de recursos
- Satisfacción del usuario

## 🔒 Seguridad

### Características de Seguridad
- Autenticación JWT
- Rate limiting
- Validación de entrada
- Logs de auditoría
- Encriptación de datos sensibles
- CORS configurado
- Headers de seguridad

### Mejores Prácticas
- Cambiar claves por defecto
- Usar HTTPS en producción
- Configurar firewall
- Monitorear logs de seguridad
- Actualizar dependencias regularmente

## 🚀 Despliegue

### Docker (Recomendado)
```bash
# Construir imagen
docker build -t hce-analyzer-pro .

# Ejecutar contenedor
docker run -p 8000:8000 -p 8501:8501 hce-analyzer-pro
```

### Producción
- Usar servidor ASGI (Gunicorn + Uvicorn)
- Configurar proxy reverso (Nginx)
- Base de datos externa (PostgreSQL)
- Cache distribuido (Redis Cluster)
- Monitoreo (Prometheus + Grafana)

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

