🛠️ ResQ Auto - Backend (FastAPI + Neon DB)
Este repositorio contiene la lógica del servidor y la conexión a la base de datos en la nube para el sistema ResQ Auto.

📋 Requisitos Previos
Antes de empezar, asegúrate de tener instalado:

Python 3.10 o superior

Git

Un cliente de base de datos como DBeaver (Opcional, pero recomendado).

🚀 Guía de Instalación y Configuración
Sigue estos pasos exactamente en tu terminal para poner a correr el proyecto:

1. Clonar el Repositorio
Bash
git clone https://github.com/MOSZDan/ParcialSI2AutomotrizBackend.git
2. Crear un Entorno Virtual (venv)
Esto sirve para que las librerías del proyecto no se mezclen con las de tu computadora.

Bash
# Crear el entorno
python -m venv venv

# Activar el entorno (En Windows)
.\venv\Scripts\activate
Si se activó correctamente, verás un (venv) al principio de tu línea de comandos.

3. Instalar Dependencias
Bash
pip install -r requirements.txt
(Si el archivo requirements.txt no existe aún, ejecuta: pip install fastapi uvicorn psycopg2-binary dj-database-url)

🗄️ Configuración de la Base de Datos (Neon)
La base de datos ya está en la nube (Neon.tech). No necesitas instalar PostgreSQL localmente.

Abre el archivo main.py.

Busca la variable DATABASE_URL.

Asegúrate de que la URL de conexión sea la siguiente (pídela por privado si no está en el código):
postgresql://neondb_owner:TU_PASSWORD@ep-jolly-morning-pooler...

Nota: Si usas DBeaver, recuerda activar en la configuración de la conexión:

Use SSL: Marcado.

SSL Mode: require.

🏃‍♂️ Cómo ejecutar el servidor
Para iniciar el Backend en modo desarrollo (con recarga automática al guardar cambios), ejecuta:

Bash
python -m uvicorn main:app --reload
Una vez que veas el mensaje Application startup complete, el servidor estará vivo en:

URL Base: http://127.0.0.1:8000

Documentación Interactiva (Swagger): http://127.0.0.1:8000/docs 👈 Entra aquí para probar los endpoints de Login y Técnicos.

🛠️ Reglas de Trabajo en Equipo
Antes de programar: Haz un git pull para bajar los cambios que yo haya subido.

Al terminar una tarea: 1. git add .
2. git commit -m "Descripción clara de lo que hiciste"
3. git push

Cuidado con la BD: Los cambios que hagas en las tablas desde DBeaver o Neon afectan a ambos. ¡No borres tablas sin avisar!
