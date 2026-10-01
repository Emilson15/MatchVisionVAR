# ⚽ MatchVision VAR

<div align="center">
 
 <img width="333" height="334" alt="logo" src="https://github.com/user-attachments/assets/d668e9c8-8578-4b09-bc1f-af64803b2ea5" />

  <p align="center">
    <strong>Sistema avanzado de escritorio para el análisis táctico, corrección de perspectiva y proyección de líneas 3D en videos de fútbol.</strong>
  </p>

  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://opencv.org/">
    <img src="https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8.svg?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV">
  </a>
  <a href="https://github.com/ultralytics/ultralytics">
    <img src="https://img.shields.io/badge/YOLOv8-Deep_Learning-FF9900.svg?style=for-the-badge&logo=pytorch&logoColor=white" alt="YOLOv8">
  </a>
  <a href="https://github.com/TomSchimansky/CustomTkinter">
    <img src="https://img.shields.io/badge/CustomTkinter-Dark_GUI-4CAF50.svg?style=for-the-badge&logo=python&logoColor=white" alt="CustomTkinter">
  </a>
</div>

---

## 📖 Sobre el Proyecto

**MatchVision VAR** es una solución de escritorio desarrollada para llevar el análisis de jugadas al siguiente nivel. Ya sea para estudiar la filosofía posicional del FC Barcelona o analizar el fútbol internacional, permite cargar clips de video y realizar un estudio geométrico del terreno de juego. 

A través de visión por computadora y redes neuronales, el software ajusta la perspectiva de la cámara, clasifica equipos por color y proyecta elementos volumétricos en 3D (como muros de fuera de juego o barreras) sobre el césped real.

## 📂 Estructura del Sistema

El proyecto está modularizado para mantener un código limpio y escalable:

* `app_desktop.py`: Lanzador principal de la plataforma.
* **`src/` (Código fuente):**
  * `gui_app.py`: Interfaz gráfica con el flujo de las 4 pantallas.
  * `style.py`: Paleta oficial y diseño visual de la sala VAR.
  * `rules_engine.py`: Motor matemático 3D, cálculos de Homografía y tecnología SAOT.
  * `team_classifier.py`: Clasificador de camisetas mediante color.
  * `database.py`: Gestión de escudos, ligas y generación de reportes en Excel.
* **`models/`:** Contiene los pesos del modelo de Deep Learning (`yolov8n.pt`).
* **`data/`:** Base de datos local (`escudos/`, `raw_videos/`, y la carpeta `reportes/` para los Excel y clips generados).
* `actualizar_instalador.bat`: Script de compilación automática en 1 clic.

---

## 🚀 Flujo de Uso

El sistema opera a través de un flujo intuitivo de 4 pantallas:

1. **Selección de Liga:** Navega con `<` y `>` entre las principales ligas europeas (LaLiga, Premier League, etc.) y haz clic en *Siguiente*.
2. **Selección de Equipos:** Elige a los equipos Local y Visitante mediante menús desplegables para cargar automáticamente sus escudos y datos.
3. **Repetición y Videos:** Los clips correspondientes al partido se resaltarán en verde. Puedes previsualizarlos o hacer clic en **`+ Añadir Videos`** para cargar una nueva jugada local en formato `.mp4`.
4. **Sala de Revisión VAR:**
   * **Controles:** Pausa, reproduce o salta ±10 fotogramas.
   * **Calibración:** Con el video pausado, haz clic en la cancha para fijar los puntos de referencia (P1-P4 para calibrar el césped, P5 para defensor, P6 para atacante).
   * **Análisis Táctico:**
     * `MARCAR OFFSIDE`: Mide la diferencia en cm (SAOT) y levanta muros volumétricos 3D.
     * `GENERAR PLANO 3D`: Dibuja una cuadrícula métrica oficial (105m × 68m) respetando la perspectiva de la cámara.
     * `MARCAR FALTA`: Proyecta el círculo reglamentario de 9.15m de distancia.
   * **Finalizar:** Al confirmar, se genera un clip de 10s, se actualiza el `VAR_Reports.xlsx` y se lanza un visor 3D interactivo rotable en 360°.

---

## 📥 Descarga e Instalación (Usuario Final)

Si solo quieres usar el programa sin tocar el código:

1. Ve al enlace **(https://drive.google.com/file/d/1H2L2hA5Se64MJ8ZvL6v5qR0Kh0qQiajl/view?usp=drive_link)**  
2. Descarga el archivo instalador más reciente (`.exe`).
3. (Opcional): Si estás en el repositorio local y tienes el código, simplemente haz doble clic en `actualizar_instalador.bat` para regenerar el instalador automáticamente.
4. Para añadir las ligas y equipos, descargas el archivo .zip que esta en este enlace **https://drive.google.com/drive/folders/1NX3Ccf23Cz-oPivB1rP7WjG8OUaYstn1?usp=drive_link**

---

## 🛠️ Ejecución para Desarrolladores

Si deseas correr el sistema desde el código fuente en tu entorno local:

1. **Clonar y preparar:**
   ```bash
   git clone [https://github.com/Emilson15/MatchvisionVAR.git](https://github.com/Emilson15/MatchvisionVAR.git)
   cd MatchvisionVAR

---

👨‍💻 Autor
Desarrollado por Emilson Alandete y Aaron Godoy

Estudiante de Computación (Universidad del Zulia - LUZ)

Si te gusta el proyecto o te ha sido útil, ¡no olvides darle una ⭐ al repositorio!
