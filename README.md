# INDUSIM 3D — Simulador de Producción Industrial

Simulador de planeamiento sistemático de la distribución en planta (SLP), costos de manejo de materiales y producción en un escenario tridimensional construido con **Three.js / React Three Fiber**.

**Estado:** MVP v0.1 en desarrollo. Los algoritmos iniciales usan distancias Manhattan entre centroides y simulación determinista; las rutas reales, SimPy, CRAFT, CORELAP, ALDEP y MILP pertenecen al roadmap, no se presentan como funciones terminadas.

Arquitectura objetivo: React + TypeScript + Three.js; Python + FastAPI + Pydantic; optimización SLP, producción y pruebas. Orden: configurar → evaluar SLP → simular → analizar.

**Uso:** `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`; en otra terminal `cd frontend && npm install && npm run dev`. Ver documentación adicional en el repositorio una vez completada la importación.
