#!/usr/bin/env python3
"""
Script de prueba para verificar renderizado HTML en Streamlit
"""
import streamlit as st

st.set_page_config(
    page_title="Test HTML Rendering",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Test de Renderizado HTML")

# Test básico de HTML
st.subheader("1. Test Básico")
st.markdown("""
<div style='background-color: #f0f0f0; padding: 1rem; border-radius: 5px;'>
    <h3 style='color: #333;'>Este es un test de HTML</h3>
    <p style='color: #666;'>Si ves esto formateado, el HTML funciona correctamente.</p>
</div>
""", unsafe_allow_html=True)

# Test del footer problemático
st.subheader("2. Test del Footer")
st.markdown("""
<div style='display: flex; justify-content: center; gap: 2rem; margin: 1rem 0; flex-wrap: wrap;'>
    <div style='text-align: center;'>
        <strong>🏥 Para Profesionales</strong><br>
        <small>Médicos • Enfermeros • Especialistas</small>
    </div>
    <div style='text-align: center;'>
        <strong>🔒 Seguro y Confiable</strong><br>
        <small>Datos Encriptados • HIPAA Compliant</small>
    </div>
    <div style='text-align: center;'>
        <strong>🤖 IA Avanzada</strong><br>
        <small>Modelos LLM • RAG • Análisis Inteligente</small>
    </div>
</div>
""", unsafe_allow_html=True)

# Test sin unsafe_allow_html para comparar
st.subheader("3. Test SIN unsafe_allow_html (debería mostrar HTML crudo)")
st.markdown("""
<div style='background-color: red; padding: 1rem;'>
    <p>Este HTML NO debería renderizarse</p>
</div>
""")

st.success("✅ Si el HTML se renderiza correctamente arriba, el problema está en otro lugar.")