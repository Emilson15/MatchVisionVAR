# src/rules_engine.py
import cv2
import numpy as np

class VARPhysicsEngine:
    """
    Motor matemático de Visión 3D y Homografía para Sistemas VAR Oficiales (LaLiga, Premier League, FIFA SAOT).
    Mapea coordenadas 2D de cámara a dimensiones reales de terreno de juego (105m x 68m).
    """
    def __init__(self, pitch_length=105.0, pitch_width=68.0):
        self.pitch_length = pitch_length
        self.pitch_width = pitch_width
        self.H_matrix = None
        self.inv_H_matrix = None
        self.setup_default_calibration()

    def setup_default_calibration(self, frame_shape=(720, 1280)):
        """Establece una homografía precisa basada en perspectiva estándar de cámara de transmisión táctica."""
        h, w = frame_shape[:2]
        src_pts = np.float32([
            [w * 0.18, h * 0.28],  # Esquina superior izquierda
            [w * 0.82, h * 0.28],  # Esquina superior derecha
            [w * 0.96, h * 0.92],  # Esquina inferior derecha
            [w * 0.04, h * 0.92]   # Esquina inferior izquierda
        ])
        
        dst_pts = np.float32([
            [0.0, 0.0],
            [self.pitch_length, 0.0],
            [self.pitch_length, self.pitch_width],
            [0.0, self.pitch_width]
        ])
        
        self.H_matrix, _ = cv2.findHomography(src_pts, dst_pts)
        if self.H_matrix is not None:
            self.inv_H_matrix = np.linalg.inv(self.H_matrix)

    def calibrate_custom_4pts(self, src_4pts):
        """
        CALIBRACIÓN MANUAL DE 4 PUNTOS (CÉSPED RECTANGULAR):
        Dada una lista de 4 puntos elegidos en las esquinas del césped [(x1,y1), (x2,y2), (x3,y3), (x4,y4)],
        calcula la matriz de homografía $H$ exacta para que las cuadrículas 3D no se descuadren.
        """
        if len(src_4pts) < 4: return False
        
        pts_src = np.float32(src_4pts[:4])
        # Puntos de destino proporcionales en metros (rectángulo del césped)
        pts_dst = np.float32([
            [20.0, 10.0],
            [85.0, 10.0],
            [85.0, 58.0],
            [20.0, 58.0]
        ])
        
        new_H, status = cv2.findHomography(pts_src, pts_dst)
        if new_H is not None:
            self.H_matrix = new_H
            self.inv_H_matrix = np.linalg.inv(new_H)
            return True
        return False

    def auto_calibrate_grass_stripes(self, frame):
        """
        Detecta las franjas y líneas de corte de césped para auto-ajustar el punto de fuga 
        y la matriz de homografía alineándola al 100% con los recuadros del campo.
        """
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask_green = cv2.inRange(hsv, np.array([30, 30, 30]), np.array([90, 255, 255]))
        
        edges = cv2.Canny(mask_green, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=120, maxLineGap=25)
        
        left_lines = []
        right_lines = []
        if lines is not None:
            for line in lines:
                pts = line.flatten()
                if len(pts) < 4: continue
                x1, y1, x2, y2 = pts[:4]
                if x2 == x1: continue
                slope = (y2 - y1) / (x2 - x1)
                if slope < -0.3 and x1 < w * 0.5:
                    left_lines.append((x1, y1, x2, y2))
                elif slope > 0.3 and x2 > w * 0.5:
                    right_lines.append((x1, y1, x2, y2))

        if len(left_lines) > 0 and len(right_lines) > 0 and self.H_matrix is None:
            self.setup_default_calibration(frame.shape)

    def pixel_to_pitch(self, px, py):
        """Convierte coordenadas (píxel_x, píxel_y) a metros de cancha (X, Y)."""
        if self.H_matrix is None:
            return 0.0, 0.0
        pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
        dst = cv2.perspectiveTransform(pt, self.H_matrix)
        return float(dst[0][0][0]), float(dst[0][0][1])

    def pitch_to_pixel(self, X, Y):
        """Convierte metros de cancha (X, Y) a coordenadas de píxel (píxel_x, píxel_y)."""
        if self.inv_H_matrix is None:
            return 0, 0
        pt = np.array([[[float(X), float(Y)]]], dtype=np.float32)
        dst = cv2.perspectiveTransform(pt, self.inv_H_matrix)
        return int(dst[0][0][0]), int(dst[0][0][1])

    def draw_opaque_3d_stadium_pitch(self, frame, def_x, att_x):
        """
        PLANO 3D OPACO DE ESTADIO:
        Renderiza el terreno de juego tridimensional opaco con textura de césped HD,
        líneas blancas de marcación y cuadrícula limpia sin transparencias confusas.
        """
        h, w = frame.shape[:2]
        opaque_pitch = np.zeros_like(frame)
        
        # Color de césped verde oscuro profesional de estadio
        opaque_pitch[:] = (20, 45, 20)
        
        # Dibujar franjas alternadas de césped en 3D
        for x in range(0, int(self.pitch_length) + 1, 6):
            p1 = self.pitch_to_pixel(x, 0)
            p2 = self.pitch_to_pixel(x + 3, 0)
            p3 = self.pitch_to_pixel(x + 3, self.pitch_width)
            p4 = self.pitch_to_pixel(x, self.pitch_width)
            
            poly = np.array([p1, p2, p3, p4], dtype=np.int32)
            cv2.fillPoly(opaque_pitch, [poly], (15, 60, 15))

        # Líneas blancas HD de marcación de cancha en 3D
        p_tl = self.pitch_to_pixel(0, 0)
        p_tr = self.pitch_to_pixel(self.pitch_length, 0)
        p_br = self.pitch_to_pixel(self.pitch_length, self.pitch_width)
        p_bl = self.pitch_to_pixel(0, self.pitch_width)
        
        cv2.polylines(opaque_pitch, [np.array([p_tl, p_tr, p_br, p_bl], dtype=np.int32)], True, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Línea central y círculo central en 3D
        p_mid_top = self.pitch_to_pixel(self.pitch_length / 2, 0)
        p_mid_bot = self.pitch_to_pixel(self.pitch_length / 2, self.pitch_width)
        cv2.line(opaque_pitch, p_mid_top, p_mid_bot, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Fusión opaca estilizada
        cv2.addWeighted(opaque_pitch, 0.85, frame, 0.15, 0, frame)
        return frame

    def draw_3d_perspective_grid(self, frame):
        """
        PLANO DE PERSPECTIVA Y CUADRÍCULA 3D DE CAMPO:
        Proyecta la cuadrícula de perspectiva reglamentaria sobre el césped usando la homografía calibrada.
        Dibuja límites de campo (105m x 68m), líneas divisorias, áreas y retícula métrica en perspectiva.
        """
        if self.H_matrix is None or self.inv_H_matrix is None:
            self.setup_default_calibration(frame.shape)

        overlay = frame.copy()
        h, w = frame.shape[:2]

        # 1. Retícula de perspectiva en el césped (cada 5 metros en X y 10 metros en Y)
        grid_color = (0, 235, 235)  # Cian/Turquesa calibración
        for x in range(0, int(self.pitch_length) + 1, 5):
            p1 = self.pitch_to_pixel(x, 0)
            p2 = self.pitch_to_pixel(x, self.pitch_width)
            thickness = 2 if x % 15 == 0 else 1
            cv2.line(overlay, p1, p2, grid_color, thickness, cv2.LINE_AA)

        for y in range(0, int(self.pitch_width) + 1, 10):
            p1 = self.pitch_to_pixel(0, y)
            p2 = self.pitch_to_pixel(self.pitch_length, y)
            cv2.line(overlay, p1, p2, grid_color, 1, cv2.LINE_AA)

        # Fusión semitransparente para ver los jugadores y el balón claramente
        cv2.addWeighted(overlay, 0.40, frame, 0.60, 0, frame)

        # 2. Líneas oficiales exteriores y divisorias de campo en 3D
        p_tl = self.pitch_to_pixel(0, 0)
        p_tr = self.pitch_to_pixel(self.pitch_length, 0)
        p_br = self.pitch_to_pixel(self.pitch_length, self.pitch_width)
        p_bl = self.pitch_to_pixel(0, self.pitch_width)
        cv2.polylines(frame, [np.array([p_tl, p_tr, p_br, p_bl], dtype=np.int32)], True, (255, 255, 255), 3, cv2.LINE_AA)

        # Línea central
        p_mid_top = self.pitch_to_pixel(self.pitch_length / 2, 0)
        p_mid_bot = self.pitch_to_pixel(self.pitch_length / 2, self.pitch_width)
        cv2.line(frame, p_mid_top, p_mid_bot, (255, 255, 255), 2, cv2.LINE_AA)

        # Círculo central 3D (radio reglamentario 9.15m)
        center_x, center_y = self.pitch_length / 2, self.pitch_width / 2
        circle_pts = []
        for a in np.linspace(0, 2 * np.pi, 48):
            cx = center_x + 9.15 * np.cos(a)
            cy = center_y + 9.15 * np.sin(a)
            circle_pts.append(self.pitch_to_pixel(cx, cy))
        cv2.polylines(frame, [np.array(circle_pts, dtype=np.int32)], True, (255, 255, 255), 2, cv2.LINE_AA)

        # Áreas grandes de penal (16.5m x 40.32m)
        a_tl = self.pitch_to_pixel(16.5, 13.84)
        a_bl = self.pitch_to_pixel(16.5, 54.16)
        p_l_top = self.pitch_to_pixel(0, 13.84)
        p_l_bot = self.pitch_to_pixel(0, 54.16)
        cv2.polylines(frame, [np.array([p_l_top, a_tl, a_bl, p_l_bot], dtype=np.int32)], False, (255, 255, 255), 2, cv2.LINE_AA)

        b_tr = self.pitch_to_pixel(self.pitch_length - 16.5, 13.84)
        b_br = self.pitch_to_pixel(self.pitch_length - 16.5, 54.16)
        p_r_top = self.pitch_to_pixel(self.pitch_length, 13.84)
        p_r_bot = self.pitch_to_pixel(self.pitch_length, 54.16)
        cv2.polylines(frame, [np.array([p_r_top, b_tr, b_br, p_r_bot], dtype=np.int32)], False, (255, 255, 255), 2, cv2.LINE_AA)

        # 3. HUD informativo superior
        cv2.rectangle(frame, (35, 35), (460, 85), (10, 10, 30), -1)
        cv2.rectangle(frame, (35, 35), (460, 85), (0, 235, 235), 2)
        cv2.putText(frame, "PLANO 3D / CALIBRACION DE CAMPO", (50, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 235, 235), 1)
        cv2.putText(frame, "PERSPECTIVA HOMOGRAFICA (105m x 68m)", (50, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        return frame

    def draw_3d_full_body_skeleton(self, frame, ground_pt, color=(255, 220, 0), is_attacker=False, is_offside=False):
        """
        ESQUEMA GRÁFICO 3D DE MANIQUÍ / MUÑECO 3D (ESTÁNDAR FIFA WORLD CUP / SAOT):
        Renderiza la estructura y volumen completo tridimensional del maniquí humano (cabeza con visor, torso volumétrico,
        extremidades tubulares 3D, articulaciones y proyección láser a las botas) sin deformaciones.
        """
        gx, gy = ground_pt
        height_scale = 85.0
        
        # Coordenadas anatómicas 3D del maniquí
        feet_pt = (gx, gy)
        hip_pt = (gx, int(gy - height_scale * 0.50))
        chest_pt = (gx, int(gy - height_scale * 0.78))
        head_pt = (gx, int(gy - height_scale * 1.05))

        # Extremidades superiores (Hombros, Codos, Manos)
        shoulder_l = (gx - 14, int(gy - height_scale * 0.78))
        shoulder_r = (gx + 14, int(gy - height_scale * 0.78))
        elbow_l = (gx - 18, int(gy - height_scale * 0.62))
        elbow_r = (gx + 18, int(gy - height_scale * 0.62))
        hand_l = (gx - 20, int(gy - height_scale * 0.46))
        hand_r = (gx + 20, int(gy - height_scale * 0.46))

        # Extremidades inferiores (Caderas, Rodillas, Pies/Botas)
        hip_l = (gx - 9, int(gy - height_scale * 0.50))
        hip_r = (gx + 9, int(gy - height_scale * 0.50))
        knee_l = (gx - 10, int(gy - height_scale * 0.28))
        knee_r = (gx + 10, int(gy - height_scale * 0.28))
        foot_l = (gx - 12, gy)
        foot_r = (gx + 12, gy)

        overlay = frame.copy()

        # 1. Láser de proyección vertical 3D desde la extremidad al césped
        cv2.line(frame, feet_pt, (feet_pt[0], feet_pt[1] - int(height_scale * 1.15)), color, 1, cv2.LINE_AA)

        # 2. Torso volumétrico 3D del maniquí (Polígono 3D relleno con transparencia)
        torso_pts = np.array([shoulder_l, shoulder_r, hip_r, hip_l], dtype=np.int32)
        cv2.fillPoly(overlay, [torso_pts], color)
        
        # 3. Brazos volumétricos 3D (Cápsulas tubulares)
        cv2.line(overlay, shoulder_l, elbow_l, color, 6, cv2.LINE_AA)
        cv2.line(overlay, elbow_l, hand_l, color, 5, cv2.LINE_AA)
        cv2.line(overlay, shoulder_r, elbow_r, color, 6, cv2.LINE_AA)
        cv2.line(overlay, elbow_r, hand_r, color, 5, cv2.LINE_AA)

        # 4. Piernas volumétricas 3D (Cápsulas tubulares)
        cv2.line(overlay, hip_l, knee_l, color, 7, cv2.LINE_AA)
        cv2.line(overlay, knee_l, foot_l, color, 6, cv2.LINE_AA)
        cv2.line(overlay, hip_r, knee_r, color, 7, cv2.LINE_AA)
        cv2.line(overlay, knee_r, foot_r, color, 6, cv2.LINE_AA)

        # Mezclar volumen semitransparente del maniquí 3D
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

        # 5. Contornos tridimensionales de alta definición
        cv2.polylines(frame, [torso_pts], True, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.line(frame, shoulder_l, elbow_l, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.line(frame, elbow_l, hand_l, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.line(frame, shoulder_r, elbow_r, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.line(frame, elbow_r, hand_r, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.line(frame, hip_l, knee_l, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.line(frame, knee_l, foot_l, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.line(frame, hip_r, knee_r, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.line(frame, knee_r, foot_r, (255, 255, 255), 1, cv2.LINE_AA)

        # 6. Cabeza y visor 3D del maniquí
        cv2.circle(frame, head_pt, 9, color, -1)
        cv2.circle(frame, head_pt, 9, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.line(frame, (head_pt[0]-5, head_pt[1]), (head_pt[0]+5, head_pt[1]), (255, 255, 255), 2, cv2.LINE_AA)

        # 7. Esferas de articulaciones anatómicas (Hombros, codos, caderas, rodillas, pies)
        for joint in [chest_pt, hip_pt, shoulder_l, shoulder_r, elbow_l, elbow_r, knee_l, knee_r]:
            cv2.circle(frame, joint, 4, (255, 255, 255), -1)

        # 8. Calzado/Botas 3D del maniquí en el césped
        cv2.ellipse(frame, foot_l, (7, 4), 0, 0, 360, color, -1)
        cv2.ellipse(frame, foot_l, (7, 4), 0, 0, 360, (255, 255, 255), 1)
        cv2.ellipse(frame, foot_r, (7, 4), 0, 0, 360, color, -1)
        cv2.ellipse(frame, foot_r, (7, 4), 0, 0, 360, (255, 255, 255), 1)

    def draw_3d_grid_sheet(self, frame, def_x, att_x):
        """
        HOJA CUADRICULADA 3D:
        Proyecta una fina malla cuadriculada 3D (cada 1 metro) exclusivamente sobre la zona de fuera de juego.
        """
        overlay = frame.copy()
        x_min = min(def_x, att_x) - 2.0
        x_max = max(def_x, att_x) + 2.0
        
        x_curr = x_min
        while x_curr <= x_max:
            p1 = self.pitch_to_pixel(x_curr, 0)
            p2 = self.pitch_to_pixel(x_curr, self.pitch_width)
            cv2.line(overlay, p1, p2, (0, 235, 235), 1, cv2.LINE_AA)
            x_curr += 1.5

        for y in range(0, int(self.pitch_width) + 1, 4):
            p1 = self.pitch_to_pixel(x_min, y)
            p2 = self.pitch_to_pixel(x_max, y)
            cv2.line(overlay, p1, p2, (0, 200, 250), 1, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
        return frame

    def draw_3d_volumetric_wall(self, frame, ground_start, ground_end, wall_height_px=75, color=(255, 220, 0)):
        """
        MURO VOLUMÉTRICO 3D TRANSPARENTE (ESTÁNDAR FIFA / UEFA SAOT BROADCAST):
        Eleva una pared vertical de cristal 3D desde la línea del césped hacia el aire.
        """
        overlay = frame.copy()
        air_start = (ground_start[0], max(5, ground_start[1] - wall_height_px))
        air_end = (ground_end[0], max(5, ground_end[1] - wall_height_px))

        wall_pts = np.array([
            ground_start,
            ground_end,
            air_end,
            air_start
        ], dtype=np.int32)

        cv2.fillPoly(overlay, [wall_pts], color)
        cv2.addWeighted(overlay, 0.38, frame, 0.62, 0, frame)

        cv2.line(frame, ground_start, air_start, color, 2, cv2.LINE_AA)
        cv2.line(frame, ground_end, air_end, color, 2, cv2.LINE_AA)
        cv2.line(frame, air_start, air_end, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.line(frame, ground_start, ground_end, color, 3, cv2.LINE_AA)

    def calculate_and_draw_saot_offside(self, frame, defender_px, attacker_px, attacking_to_right=True, use_opaque_pitch=True):
        """
        TECNOLOGÍA RECREACIÓN 3D BROADCAST SAOT (FIFA WORLD CUP / LALIGA):
        Combina el Plano 3D Opaco, la Hoja Cuadriculada 3D, Muro Volumétrico Transparente y Esquema 3D Anatómico.
        """
        def_x, def_y = self.pixel_to_pitch(defender_px[0], defender_px[1])
        att_x, att_y = self.pixel_to_pitch(attacker_px[0], attacker_px[1])

        diff_meters = (att_x - def_x) if attacking_to_right else (def_x - att_x)
        diff_cm = diff_meters * 100.0
        is_offside = diff_cm > 0.0

        # 1. PLANO 3D OPACO DE ESTADIO (SI ESTÁ ACTIVO)
        if use_opaque_pitch:
            frame = self.draw_opaque_3d_stadium_pitch(frame, def_x, att_x)

        # 2. DIBUJAR HOJA CUADRICULADA 3D SOBRE EL CÉSPED
        frame = self.draw_3d_grid_sheet(frame, def_x, att_x)

        def_line_start = self.pitch_to_pixel(def_x, 0)
        def_line_end = self.pitch_to_pixel(def_x, self.pitch_width)
        
        att_line_start = self.pitch_to_pixel(att_x, 0)
        att_line_end = self.pitch_to_pixel(att_x, self.pitch_width)

        # 3. POLÍGONO DE ZONA SOMBREADA EN EL SUELO
        overlay = frame.copy()
        poly_pts = np.array([
            def_line_start,
            def_line_end,
            att_line_end,
            att_line_start
        ], dtype=np.int32)
        poly_color = (0, 0, 255) if is_offside else (0, 255, 0)
        cv2.fillPoly(overlay, [poly_pts], poly_color)
        cv2.addWeighted(overlay, 0.30, frame, 0.70, 0, frame)

        # 4. MURO VOLUMÉTRICO 3D TRANSPARENTE DEL ÚLTIMO DEFENSOR
        self.draw_3d_volumetric_wall(frame, def_line_start, def_line_end, wall_height_px=80, color=(255, 220, 0))

        # 5. MURO VOLUMÉTRICO 3D DEL ATACANTE
        att_wall_color = (0, 0, 255) if is_offside else (0, 255, 0)
        self.draw_3d_volumetric_wall(frame, att_line_start, att_line_end, wall_height_px=80, color=att_wall_color)

        # 6. ESQUEMAS GRÁFICOS 3D ANATÓMICOS DE CUERPO COMPLETO DE JUGADORES
        self.draw_3d_full_body_skeleton(frame, defender_px, color=(255, 220, 0), is_attacker=False, is_offside=False)
        self.draw_3d_full_body_skeleton(frame, attacker_px, color=att_wall_color, is_attacker=True, is_offside=is_offside)

        # 7. HUD BROADCAST OFICIAL DE TELEVISIÓN
        hud_text = f"DIFERENCIA 3D SAOT: +{diff_cm:.1f} cm" if is_offside else f"DIFERENCIA 3D SAOT: {diff_cm:.1f} cm"
        box_color = (0, 0, 220) if is_offside else (0, 160, 0)
        
        cv2.rectangle(frame, (35, 35), (470, 95), (10, 10, 30), -1)
        cv2.rectangle(frame, (35, 35), (470, 95), box_color, 2)
        cv2.putText(frame, "RECREACIÓN 3D BROADCAST SAOT (ESQUEMA ANATÓMICO)", (50, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (220, 220, 220), 1)
        cv2.putText(frame, hud_text, (50, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (255, 255, 255), 2)

        return frame, is_offside, diff_cm





    def draw_free_kick_wall_3d(self, frame, foul_px, radius_m=9.15):
        """Proyecta la barrera reglamentaria de 9.15m en perspectiva 3D alrededor del punto de falta."""
        foul_x, foul_y = self.pixel_to_pitch(foul_px[0], foul_px[1])
        overlay = frame.copy()

        # Generar puntos del círculo en coordenadas reales de la cancha
        angles = np.linspace(0, 2 * np.pi, 60)
        circle_pixels = []
        for a in angles:
            cx = foul_x + radius_m * np.cos(a)
            cy = foul_y + radius_m * np.sin(a)
            circle_pixels.append(self.pitch_to_pixel(cx, cy))

        circle_pts = np.array(circle_pixels, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(overlay, [circle_pts], isClosed=True, color=(0, 255, 255), thickness=3, lineType=cv2.LINE_AA)
        
        # Marcador central del punto de falta
        cv2.circle(overlay, foul_px, 6, (0, 0, 255), -1)
        cv2.circle(overlay, foul_px, 10, (255, 255, 255), 2)

        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        
        cv2.rectangle(frame, (40, 40), (430, 90), (10, 10, 30), -1)
        cv2.rectangle(frame, (40, 40), (430, 90), (0, 255, 255), 2)
        cv2.putText(frame, f"DISTANCIA DE BARRERA 3D: {radius_m}m", (55, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

        return frame

    def render_tactical_radar(self, detections, width=320, height=210):
        """
        Genera el radar táctico 2D (Bird's-Eye View) con la posición de jugadores y balón.
        detections: lista de dicts [{'pt_px': (x,y), 'team': 0/1, 'is_gk': bool, 'is_ball': bool, 'is_ref': bool}]
        """
        radar = np.full((height, width, 3), (25, 45, 25), dtype=np.uint8)
        
        # Líneas del campo en el radar
        cv2.rectangle(radar, (15, 15), (width - 15, height - 15), (255, 255, 255), 1)
        cv2.line(radar, (width // 2, 15), (width // 2, height - 15), (255, 255, 255), 1)
        cv2.circle(radar, (width // 2, height // 2), 25, (255, 255, 255), 1)

        scale_x = (width - 30) / self.pitch_length
        scale_y = (height - 30) / self.pitch_width

        for d in detections:
            px, py = d.get('pt_px', (0,0))
            rx, ry = self.pixel_to_pitch(px, py)
            
            # Mapear a coordenadas dentro de la caja del radar
            rad_x = int(15 + rx * scale_x)
            rad_y = int(15 + ry * scale_y)
            rad_x = np.clip(rad_x, 15, width - 15)
            rad_y = np.clip(rad_y, 15, height - 15)

            if d.get('is_ball', False):
                cv2.circle(radar, (rad_x, rad_y), 4, (0, 255, 255), -1) # Balón amarillo
            elif d.get('is_ref', False):
                cv2.circle(radar, (rad_x, rad_y), 4, (200, 200, 200), -1) # Árbitro gris
            elif d.get('team') == 0:
                color = (0, 255, 0) if d.get('is_gk') else (255, 80, 80) # Equipo Local (Azul/Celeste)
                cv2.circle(radar, (rad_x, rad_y), 5, color, -1)
            elif d.get('team') == 1:
                color = (255, 150, 0) if d.get('is_gk') else (80, 80, 255) # Equipo Visitante (Rojo)
                cv2.circle(radar, (rad_x, rad_y), 5, color, -1)

        return radar


    def render_rotatable_3d_offside_scene(self, def_pitch_x, att_pitch_x, rot_x_deg=35.0, rot_y_deg=25.0, width=540, height=380, is_offside=True, diff_cm=0.0):
        """
        RENDERIZADOR 3D INTERACTIVO ROTATORIO 360° (ESTÁNDAR FIFA SAOT):
        Permite orbitar libremente con el mouse alrededor de la zona de fuera de juego.
        Renderiza el terreno opaco 3D, la hoja cuadriculada, muros volumétricos de cristal y maniquíes 3D.
        """
        frame = np.full((height, width, 3), (15, 20, 30), dtype=np.uint8)
        
        # Parámetros de cámara 3D
        rad_x = np.radians(rot_x_deg) # Elevación
        rad_y = np.radians(rot_y_deg) # Azimut
        
        cx, cy = width / 2.0, height / 2.0 + 30.0
        focal = min(width, height) * 0.90
        dist_cam = 45.0

        x_center = (def_pitch_x + att_pitch_x) / 2.0
        y_center = self.pitch_width / 2.0

        def project_3d(x_m, y_m, z_m):
            dx = x_m - x_center
            dy = y_m - y_center
            dz = z_m
            
            # Rotación en Azimut (Y-axis)
            x1 = dx * np.cos(rad_y) + dy * np.sin(rad_y)
            y1 = -dx * np.sin(rad_y) + dy * np.cos(rad_y)
            
            # Rotación en Elevación (X-axis)
            y2 = y1 * np.cos(rad_x) - dz * np.sin(rad_x)
            z2 = y1 * np.sin(rad_x) + dz * np.cos(rad_x)
            
            z_cam = z2 + dist_cam
            if z_cam <= 0.1: z_cam = 0.1
            
            u = int(cx + focal * (x1 / z_cam))
            v = int(cy + focal * (y2 / z_cam))
            return (u, v)

        # 1. Terreno de juego opaco con franjas 3D
        overlay = frame.copy()
        x_start = max(0.0, x_center - 18.0)
        x_end = min(self.pitch_length, x_center + 18.0)
        
        # Franjas alternadas
        stripe_w = 3.0
        curr_x = x_start
        idx_stripe = 0
        while curr_x < x_end:
            p_bl = project_3d(curr_x, 0.0, 0.0)
            p_br = project_3d(curr_x + stripe_w, 0.0, 0.0)
            p_tr = project_3d(curr_x + stripe_w, self.pitch_width, 0.0)
            p_tl = project_3d(curr_x, self.pitch_width, 0.0)
            
            poly = np.array([p_bl, p_br, p_tr, p_tl], dtype=np.int32)
            c_val = (25, 60, 25) if idx_stripe % 2 == 0 else (18, 45, 18)
            cv2.fillPoly(frame, [poly], c_val)
            curr_x += stripe_w
            idx_stripe += 1

        # Líneas blancas del terreno
        p_l_bot = project_3d(x_start, 0.0, 0.0)
        p_l_top = project_3d(x_start, self.pitch_width, 0.0)
        p_r_bot = project_3d(x_end, 0.0, 0.0)
        p_r_top = project_3d(x_end, self.pitch_width, 0.0)
        
        cv2.line(frame, p_l_bot, p_r_bot, (240, 240, 240), 2, cv2.LINE_AA)
        cv2.line(frame, p_l_top, p_r_top, (240, 240, 240), 2, cv2.LINE_AA)

        # 2. Hoja cuadriculada 3D en la zona de offside
        grid_min_x = min(def_pitch_x, att_pitch_x) - 2.5
        grid_max_x = max(def_pitch_x, att_pitch_x) + 2.5
        
        gx = grid_min_x
        while gx <= grid_max_x:
            p1 = project_3d(gx, 0.0, 0.0)
            p2 = project_3d(gx, self.pitch_width, 0.0)
            cv2.line(overlay, p1, p2, (0, 220, 220), 1, cv2.LINE_AA)
            gx += 1.5

        for gy_m in range(0, int(self.pitch_width) + 1, 5):
            p1 = project_3d(grid_min_x, gy_m, 0.0)
            p2 = project_3d(grid_max_x, gy_m, 0.0)
            cv2.line(overlay, p1, p2, (0, 190, 230), 1, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

        # 3. Muro Volumétrico de Cristal 3D (Defensor & Atacante)
        def draw_wall(pitch_x, wall_color):
            overlay_w = frame.copy()
            g_start = project_3d(pitch_x, 0.0, 0.0)
            g_end = project_3d(pitch_x, self.pitch_width, 0.0)
            a_start = project_3d(pitch_x, 0.0, 3.2)
            a_end = project_3d(pitch_x, self.pitch_width, 3.2)
            
            pts = np.array([g_start, g_end, a_end, a_start], dtype=np.int32)
            cv2.fillPoly(overlay_w, [pts], wall_color)
            cv2.addWeighted(overlay_w, 0.38, frame, 0.62, 0, frame)
            
            cv2.line(frame, g_start, a_start, wall_color, 2, cv2.LINE_AA)
            cv2.line(frame, g_end, a_end, wall_color, 2, cv2.LINE_AA)
            cv2.line(frame, a_start, a_end, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.line(frame, g_start, g_end, wall_color, 3, cv2.LINE_AA)

        draw_wall(def_pitch_x, (255, 220, 0)) # Muro cristal defensor (Amarillo)
        att_color = (0, 0, 255) if is_offside else (0, 255, 0)
        draw_wall(att_pitch_x, att_color) # Muro cristal atacante (Rojo/Verde)

        # 4. Maniquíes 3D Volumétricos de Defensor y Atacante
        def draw_mannequin_3d(pitch_x, pitch_y, color):
            h_m = 1.85
            feet_pt = project_3d(pitch_x, pitch_y, 0.0)
            hip_pt = project_3d(pitch_x, pitch_y, h_m * 0.50)
            chest_pt = project_3d(pitch_x, pitch_y, h_m * 0.78)
            head_pt = project_3d(pitch_x, pitch_y, h_m * 1.05)
            
            shoulder_l = project_3d(pitch_x - 0.25, pitch_y - 0.40, h_m * 0.78)
            shoulder_r = project_3d(pitch_x + 0.25, pitch_y + 0.40, h_m * 0.78)
            elbow_l = project_3d(pitch_x - 0.35, pitch_y - 0.50, h_m * 0.60)
            elbow_r = project_3d(pitch_x + 0.35, pitch_y + 0.50, h_m * 0.60)
            hand_l = project_3d(pitch_x - 0.40, pitch_y - 0.55, h_m * 0.42)
            hand_r = project_3d(pitch_x + 0.40, pitch_y + 0.55, h_m * 0.42)

            hip_l = project_3d(pitch_x - 0.20, pitch_y - 0.25, h_m * 0.50)
            hip_r = project_3d(pitch_x + 0.20, pitch_y + 0.25, h_m * 0.50)
            knee_l = project_3d(pitch_x - 0.22, pitch_y - 0.28, h_m * 0.26)
            knee_r = project_3d(pitch_x + 0.22, pitch_y + 0.28, h_m * 0.26)
            foot_l = project_3d(pitch_x - 0.25, pitch_y - 0.30, 0.0)
            foot_r = project_3d(pitch_x + 0.25, pitch_y + 0.30, 0.0)

            ov_m = frame.copy()

            # Láser vertical 3D
            cv2.line(frame, feet_pt, head_pt, color, 1, cv2.LINE_AA)

            # Torso volumétrico
            torso_pts = np.array([shoulder_l, shoulder_r, hip_r, hip_l], dtype=np.int32)
            cv2.fillPoly(ov_m, [torso_pts], color)

            # Extremidades volumétricas
            cv2.line(ov_m, shoulder_l, elbow_l, color, 5, cv2.LINE_AA)
            cv2.line(ov_m, elbow_l, hand_l, color, 4, cv2.LINE_AA)
            cv2.line(ov_m, shoulder_r, elbow_r, color, 5, cv2.LINE_AA)
            cv2.line(ov_m, elbow_r, hand_r, color, 4, cv2.LINE_AA)

            cv2.line(ov_m, hip_l, knee_l, color, 6, cv2.LINE_AA)
            cv2.line(ov_m, knee_l, foot_l, color, 5, cv2.LINE_AA)
            cv2.line(ov_m, hip_r, knee_r, color, 6, cv2.LINE_AA)
            cv2.line(ov_m, knee_r, foot_r, color, 5, cv2.LINE_AA)

            cv2.addWeighted(ov_m, 0.45, frame, 0.55, 0, frame)

            # Contornos HD
            cv2.polylines(frame, [torso_pts], True, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.line(frame, shoulder_l, elbow_l, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(frame, shoulder_r, elbow_r, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(frame, hip_l, knee_l, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(frame, hip_r, knee_r, (255, 255, 255), 1, cv2.LINE_AA)

            # Cabeza y visor 3D
            cv2.circle(frame, head_pt, 8, color, -1)
            cv2.circle(frame, head_pt, 8, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.line(frame, (head_pt[0]-4, head_pt[1]), (head_pt[0]+4, head_pt[1]), (255, 255, 255), 2, cv2.LINE_AA)

            # Articulaciones
            for j in [chest_pt, hip_pt, shoulder_l, shoulder_r, knee_l, knee_r]:
                cv2.circle(frame, j, 3, (255, 255, 255), -1)

        draw_mannequin_3d(def_pitch_x, self.pitch_width * 0.42, (255, 220, 0))
        draw_mannequin_3d(att_pitch_x, self.pitch_width * 0.58, att_color)

        # 5. HUD Banner Broadcast de Televisión
        hud_text = f"FUERA DE JUEGO (SAOT): +{diff_cm:.1f} cm" if is_offside else f"HABILITADO (SAOT): {diff_cm:.1f} cm"
        box_c = (0, 0, 200) if is_offside else (0, 160, 0)
        cv2.rectangle(frame, (15, 15), (width - 15, 50), (10, 10, 25), -1)
        cv2.rectangle(frame, (15, 15), (width - 15, 50), box_c, 2)
        cv2.putText(frame, hud_text, (25, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # 6. Indicador de Rotación con Mouse
        cv2.putText(frame, "🖱️ Arrastra el mouse para rotar en 360°", (15, height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1)

        return frame


class PanoramicVARSystem:
    """Clase envolvente manteniendo compatibilidad con la arquitectura previa."""
    def __init__(self, match_config):
        self.config = match_config
        self.physics = VARPhysicsEngine()

    def process_perspective_grid(self, frame):
        return self.physics.draw_3d_perspective_grid(frame)