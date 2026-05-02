# Configuración del Entorno Conda HCE

Este documento explica cómo configurar el entorno de desarrollo para el proyecto HCE usando Conda.

## Requisitos Previos

- **Anaconda** o **Miniconda** instalado en tu sistema
- Descargar desde: https://www.anaconda.com/download o https://docs.conda.io/en/latest/miniconda.html

## Opción 1: Instalación Automática (Recomendada)

### Windows
Ejecuta el script de instalación:
```cmd
setup_conda_env.bat
```

## Opción 2: Instalación Manual

### Paso 1: Crear el entorno desde el archivo YAML
```cmd
conda env create -f environment.yml
```

### Paso 2: Activar el entorno
```cmd
conda activate HCE
```

### Paso 3: Verificar la instalación
```cmd
python --version
pip list
```

## Uso del Entorno

### Activar el entorno
```cmd
conda activate HCE
```

### Desactivar el entorno
```cmd
conda deactivate
```

### Actualizar el entorno (si se modifican las dependencias)
```cmd
conda env update -f environment.yml --prune
```

### Eliminar el entorno (si necesitas empezar de nuevo)
```cmd
conda env remove -n HCE
```

## Configuración del Proyecto

Una vez activado el entorno, configura las variables de entorno:

1. Copia el archivo de ejemplo:
```cmd
copy .env.example .env
```

2. Edita `.env` con tus credenciales y configuraciones

## Ejecutar la Aplicación

Con el entorno activado:

```cmd
streamlit run main.py
```

O usando el script de inicio:

```cmd
python start_app.py
```

## Solución de Problemas

### Error: "conda no se reconoce como comando"
- Asegúrate de que Anaconda/Miniconda esté instalado
- Reinicia tu terminal después de la instalación
- Verifica que conda esté en tu PATH

### Error: "El entorno ya existe"
Elimina el entorno existente primero:
```cmd
conda env remove -n HCE
```

### Problemas con dependencias específicas
Si alguna dependencia falla, puedes instalarla manualmente:
```cmd
conda activate HCE
pip install nombre-del-paquete
```

### Actualizar pip dentro del entorno
```cmd
conda activate HCE
python -m pip install --upgrade pip
```

## Exportar el Entorno

Para compartir tu configuración exacta:

```cmd
conda activate HCE
conda env export > environment_exact.yml
```

## Información del Entorno

- **Nombre**: HCE
- **Python**: 3.11
- **Gestor de paquetes**: pip (dentro de conda)
- **Dependencias principales**:
  - Streamlit (UI)
  - FastAPI (API)
  - LangChain (AI/ML)
  - Supabase (Database + pgvector RAG)
  - Anthropic Claude (LLM)

## Comandos Útiles

```cmd
# Listar todos los entornos
conda env list

# Ver paquetes instalados
conda list

# Buscar un paquete específico
conda list | findstr nombre-paquete

# Actualizar conda
conda update conda

# Limpiar caché de conda
conda clean --all
```
