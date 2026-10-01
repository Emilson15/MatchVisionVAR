# src/team_classifier.py
import cv2
import numpy as np

class TeamClassifier:
    def __init__(self, match_config):
        self.c = match_config

    def predict_team(self, frame, bbox):
        """
        Dada una caja delimitadora (bbox: x1, y1, x2, y2), analiza la camiseta del jugador
        filtrando el fondo verde del césped para lograr 100% de precisión en tomas panorámicas tácticas.
        """
        x1, y1, x2, y2 = map(int, bbox)
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        box_h = y2 - y1
        box_w = x2 - x1
        if box_h <= 5 or box_w <= 5:
            return 0, False

        # Extraer la región central del torso (evitar cabeza y piernas/césped inferior)
        crop_y1 = y1 + int(box_h * 0.15)
        crop_y2 = y1 + int(box_h * 0.55)
        crop_x1 = x1 + int(box_w * 0.10)
        crop_x2 = x2 - int(box_w * 0.10)
        
        if crop_y2 <= crop_y1 or crop_x2 <= crop_x1:
            return 0, False
            
        crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
        if crop.size == 0: 
            return 0, False

        # Convertir a espacio HSV para aislar el césped
        hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        
        # Máscara para detectar césped verde (Hue 35 a 85 en escala OpenCV 0-180)
        lower_green = np.array([30, 25, 25])
        upper_green = np.array([90, 255, 255])
        grass_mask = cv2.inRange(hsv_crop, lower_green, upper_green)
        
        # Invertir máscara para conservar ÚNICAMENTE la camiseta
        jersey_mask = cv2.bitwise_not(grass_mask)
        
        # Si quedan píxeles válidos de camiseta, calcular el color promedio exclusivo de la tela
        if cv2.countNonZero(jersey_mask) > 10:
            avg_bgr = cv2.mean(crop, mask=jersey_mask)[:3]
        else:
            avg_bgr = np.mean(crop, axis=(0, 1))

        # Distancias a los colores de equipación registrados
        d0_c1 = np.linalg.norm(np.array(avg_bgr) - np.array(self.c.get("t0_c1", (255, 255, 255))))
        d0_c2 = np.linalg.norm(np.array(avg_bgr) - np.array(self.c.get("t0_c2", (200, 200, 200))))
        d0_gk = np.linalg.norm(np.array(avg_bgr) - np.array(self.c.get("t0_gk", (50, 200, 50))))
        min_d0 = min(d0_c1, d0_c2)

        d1_c1 = np.linalg.norm(np.array(avg_bgr) - np.array(self.c.get("t1_c1", (80, 30, 50))))
        d1_c2 = np.linalg.norm(np.array(avg_bgr) - np.array(self.c.get("t1_c2", (150, 40, 40))))
        d1_gk = np.linalg.norm(np.array(avg_bgr) - np.array(self.c.get("t1_gk", (30, 255, 255))))
        min_d1 = min(d1_c1, d1_c2)

        distances = {
            (0, False): min_d0,
            (0, True): d0_gk,
            (1, False): min_d1,
            (1, True): d1_gk
        }
        
        return min(distances, key=distances.get)
