🧠 API Semántica de Hardware y Procesadores
<!-- Insignias de estado: dan un aspecto profesional y resumen las tecnologías -->

Este proyecto implementa un Backend Semántico utilizando FastAPI y RDFLib. Su función es consultar una Ontología OWL/RDF sobre procesadores y servir los datos en formato JSON simple. Actúa como el puente entre la base de conocimiento y cualquier aplicación Frontend.

📋 Características Principales
Carga de Ontología RDF/XML: Lee automáticamente el archivo ontologia.rdf al iniciar el servidor.

Traducción Semántica: Convierte tripletas de grafos a JSON limpio y legible.

Endpoints Específicos: Rutas definidas para listar clases, individuos (procesadores) y sus detalles.

Robustez: Manejo de errores para evitar bloqueos si el archivo de ontología tiene problemas de carga.

🧩 Estructura de la Ontología
La base de conocimiento (ontologia.rdf) modela las siguientes entidades principales, basadas en el archivo proporcionado:

Clases Principales
Procesador: Entidad central (ej: Snapdragon 8 Gen 2, Apple A16 Bionic).

Fabricante

GPU

Nucleo

Rendimiento

Entre otras.

🚀 Instalación y Ejecución
1. Prerrequisitos
Asegúrate de tener Python 3.8+ instalado.

2. Instalación de Dependencias
Ejecuta el siguiente comando para instalar las librerías necesarias:

pip install -r requirements.txt

3. Ejecución del Servidor
Asegúrate de que app.py y ontologia.rdf estén en la misma carpeta, y luego ejecuta:

python app.py

El servidor iniciará en: http://127.0.0.1:8000

🛠️ Estructura del Proyecto
backend-ontologia/
├── app.py              # Lógica del servidor y endpoints.
├── ontologia.rdf       # Archivo de la Ontología (Base de Datos).
├── requirements.txt    # Lista de librerías.
└── README.md           # Documentación del proyecto.
