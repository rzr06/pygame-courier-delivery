import pygame
import random
import math
import heapq

pygame.init()

WIDTH, HEIGHT = 1440, 900

GRAY_RANGE = [(120, 120, 120)]
GREEN_BORDER = (16, 172, 58)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Smart Courier Simulation")

# Variabel global
map_image = None
map_loaded = False
map_files = ["assets/map1.png", "assets/map2.png", "assets/map3.png", "assets/map4.png", "assets/map5.png"]
last_map = None
collision_map = []
gray_pixels = []
corridor_horizontal = True
valid_y_range = (0, HEIGHT)
valid_x_range = (0, WIDTH)

def smooth_path(path):
    if len(path) < 3:
        return path
    
    smoothed = [path[0]]
    for point in path[1:-1]:
        last = smoothed[-1]
        dx = point[0] - last[0]
        dy = point[1] - last[1]
        if abs(dx) + abs(dy) > 20:
            smoothed.append(point)
    smoothed.append(path[-1])
    return smoothed

def find_centroid(points):
    if not points:
        return None
    total_x = sum(x for x, y in points)
    total_y = sum(y for x, y in points)
    return (total_x // len(points), total_y // len(points))

def find_nearest_point(target, points):
    min_dist = float('inf')
    nearest = points[0]
    for (x, y) in points:
        dist = (x - target[0])**2 + (y - target[1])**2
        if dist < min_dist:
            min_dist = dist
            nearest = (x, y)
    return nearest

def heuristic(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def a_star(start, goal, collision_map):
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while open_set:
        current = heapq.heappop(open_set)[1]

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return smooth_path(path)

        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1), (-1,-1),(-1,1),(1,-1),(1,1)]:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < WIDTH and 0 <= neighbor[1] < HEIGHT:
                if collision_map[neighbor[0]][neighbor[1]]:
                    move_cost = 1.4 if abs(dx)+abs(dy)==2 else 1
                    tentative_g = g_score[current] + move_cost
                    
                    if neighbor not in g_score or tentative_g < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g
                        f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return None

def load_map():
    global map_image, map_loaded, last_map, collision_map, gray_pixels, corridor_horizontal, valid_y_range, valid_x_range
    
    if len(map_files) == 0:
        print("Tidak ada peta tersedia!")
        return

    available_maps = [m for m in map_files if m != last_map]
    if not available_maps:
        available_maps = map_files

    image_path = random.choice(available_maps)
    
    try:
        map_image = pygame.image.load(image_path)
        map_image = pygame.transform.scale(map_image, (WIDTH, HEIGHT))
        map_loaded = True  
        last_map = image_path
        
        green_pixels = []
        gray_pixels_temp = []
        for x in range(WIDTH):
            for y in range(HEIGHT):
                color = map_image.get_at((x, y))
                rgb = (color.r, color.g, color.b)
                if rgb == GREEN_BORDER:
                    green_pixels.append((x, y))
                elif rgb in GRAY_RANGE:
                    gray_pixels_temp.append((x, y))
        
        forbidden_surface = pygame.Surface((WIDTH, HEIGHT))
        forbidden_surface.fill(BLACK)
        for (gx, gy) in green_pixels:
            pygame.draw.circle(forbidden_surface, WHITE, (gx, gy), 28)
        
        gray_pixels = []
        for (x, y) in gray_pixels_temp:
            if forbidden_surface.get_at((x, y))[:3] == (0, 0, 0):
                gray_pixels.append((x, y))
        
        if not gray_pixels:
            print("Tidak ada area abu-abu valid yang tersedia!")
            map_loaded = False
            return
        
        min_x = min(p[0] for p in gray_pixels)
        max_x = max(p[0] for p in gray_pixels)
        min_y = min(p[1] for p in gray_pixels)
        max_y = max(p[1] for p in gray_pixels)
        width = max_x - min_x
        height = max_y - min_y
        corridor_horizontal = width > height
        
        if corridor_horizontal:
            corridor_height = height
            top_margin = (HEIGHT - corridor_height) // 2
            valid_y_range = (top_margin, HEIGHT - top_margin)
            gray_pixels = [ (x, y) for (x, y) in gray_pixels if valid_y_range[0] <= y <= valid_y_range[1] ]
        else:
            corridor_width = width
            left_margin = (WIDTH - corridor_width) // 2
            valid_x_range = (left_margin, WIDTH - left_margin)
            gray_pixels = [ (x, y) for (x, y) in gray_pixels if valid_x_range[0] <= x <= valid_x_range[1] ]
        
        collision_map = [[False for _ in range(HEIGHT)] for _ in range(WIDTH)]
        for (x, y) in gray_pixels:
            collision_map[x][y] = True
        
        print(f"Peta {image_path} dimuat!")
        print(f"Jumlah pixel abu-abu valid: {len(gray_pixels)}")
        print(f"Orientasi koridor: {'Horizontal' if corridor_horizontal else 'Vertical'}")
        print(f"Area valid: {valid_y_range if corridor_horizontal else valid_x_range}")

        # Reset posisi kurir setelah load map
        randomize_positions()
        
    except Exception as e:
        print(f"Error: Tidak bisa memuat {image_path}")
        print(e)

class Courier:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 3
        self.path = []
        self.current_target_index = 0
        self.moving = False
        self.angle = 0
        self.target_angle = 0
        
        # Buat surface lebih besar untuk kualitas rotasi yang lebih baik
        self.image = pygame.Surface((60, 40), pygame.SRCALPHA)
        
        # Gambar segitiga dengan anti-aliasing
        points = [
            (5, 5),
            (5, 35),
            (55, 20)
        ]
        pygame.draw.polygon(self.image, BLACK, points)
        pygame.draw.aalines(self.image, BLACK, True, points)  # Anti-aliased outline
        
    def draw(self, surface):
        # Gunakan rotozoom untuk kualitas rotasi lebih baik
        rotated_image = pygame.transform.rotozoom(self.image, self.angle, 0.5)  # Scale down 50%
        rect = rotated_image.get_rect(center=(self.x, self.y))
        surface.blit(rotated_image, rect.topleft)
        
    def move_towards(self):
        if not self.moving or self.current_target_index >= len(self.path):
            return

        target = self.path[self.current_target_index]
        
        dx = target[0] - self.x
        dy = target[1] - self.y
        distance = math.hypot(dx, dy)
        
        if distance > 0:
            move_x = (dx/distance) * self.speed
            move_y = (dy/distance) * self.speed
            
            new_x = self.x + move_x
            new_y = self.y + move_y
            
            # Smooth rotation dengan interpolasi sudut
            target_angle = math.degrees(math.atan2(-dy, dx)) % 360
            angle_diff = (target_angle - self.angle) % 360
            if angle_diff > 180:
                angle_diff -= 360
            self.angle += angle_diff * 0.15  # Lebih halus
            
            # Snap progresif dengan interpolasi lebih smooth
            if not collision_map[int(new_x)][int(new_y)]:
                nearest = find_nearest_point((new_x, new_y), gray_pixels)
                new_x = new_x * 0.85 + nearest[0] * 0.15
                new_y = new_y * 0.85 + nearest[1] * 0.15
                
            self.x, self.y = new_x, new_y
        
        if distance < 5:
            self.current_target_index += 1
            if self.current_target_index >= len(self.path):
                self.moving = False
                self.x, self.y = int(round(self.x)), int(round(self.y))

def bresenham_line(start, end):
    """Menghasilkan titik-titik integer di sepanjang garis dari start ke end menggunakan algoritma Bresenham."""
    x0, y0 = start
    x1, y1 = end
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return points

def get_valid_directions(source):
    valid_angles = []
    for angle in range(0, 360, 5):  # Cek setiap 5 derajat
        rad = math.radians(angle)
        dx = math.cos(rad)
        dy = -math.sin(rad)  # Penyesuaian untuk sistem koordinat pygame
        
        end_x = int(source[0] + dx * 50)
        end_y = int(source[1] + dy * 50)
        
        line_points = bresenham_line(source, (end_x, end_y))
        
        if len(line_points) < 50:
            continue
            
        valid = True
        for point in line_points[:50]:  # Cek 50 titik pertama
            x, y = point
            if x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
                valid = False
                break
            if not collision_map[x][y]:
                valid = False
                break
                
        if valid:
            valid_angles.append(angle)
            
    return valid_angles

def get_valid_directions(source):
    """Mendapatkan arah valid berdasarkan orientasi koridor dan posisi source"""
    valid_directions = []
    
    # Cek orientasi koridor
    if corridor_horizontal:
        # Untuk koridor horizontal, hanya boleh hadap kiri (180) atau kanan (0)
        directions = [0, 180]
    else:
        # Untuk koridor vertical, hanya boleh hadap atas (90) atau bawah (270)
        directions = [90, 270]
    
    # Cek setiap arah yang memungkinkan
    for angle in directions:
        valid = True
        rad = math.radians(angle)
        dx = math.cos(rad)
        dy = -math.sin(rad)  # Adjust for pygame coordinate system
        
        # Cek 50 pixel ke depan
        for i in range(1, 50):
            x = int(source[0] + dx * i)
            y = int(source[1] + dy * i)
            
            # Jika keluar dari area valid atau masuk green border
            if not (0 <= x < WIDTH and 0 <= y < HEIGHT) or not collision_map[x][y]:
                valid = False
                break
                
        if valid:
            valid_directions.append(angle)
            
    return valid_directions

def randomize_positions():
    global source, destination, courier, running_simulation
    
    if len(gray_pixels) < 2:
        print("Tidak cukup area abu-abu valid untuk memilih posisi!")
        return

    MIN_DISTANCE = 750
    max_attempts = 500

    # Cari pasangan posisi yang valid
    for _ in range(max_attempts):
        source = random.choice(gray_pixels)
        valid_directions = get_valid_directions(source)
        
        if not valid_directions:
            continue
            
        # Cari tujuan yang sesuai
        valid_destinations = []
        for p in gray_pixels:
            if p == source:
                continue
            dx = p[0] - source[0]
            dy = p[1] - source[1]
            if math.hypot(dx, dy) >= MIN_DISTANCE:
                valid_destinations.append(p)
        
        if not valid_destinations:
            continue
            
        destination = random.choice(valid_destinations)
        
        # Hitung sudut ke tujuan
        target_dx = destination[0] - source[0]
        target_dy = destination[1] - source[1]
        target_angle = math.degrees(math.atan2(-target_dy, target_dx)) % 360
        
        # Pilih arah valid yang paling dekat dengan sudut tujuan
        best_angle = min(valid_directions, 
                         key=lambda x: min(abs(x - target_angle), 360 - abs(x - target_angle)))
        
        courier = Courier(*source)
        courier.angle = best_angle
        running_simulation = False
        
        print(f"Posisi diatur! Start: {source}, Finish: {destination}")
        print(f"Jarak: {math.hypot(target_dx, target_dy):.1f} pixel")
        print(f"Arah awal: {best_angle}°")
        return
    
    print("Gagal menemukan posisi yang memenuhi syarat")
    
# GUI Elements
source = (0, 0)
destination = (0, 0)
courier = Courier(*source)
load_map_button = pygame.Rect(0, 0, 115, 40)
random_button = pygame.Rect(0, 55, 115, 40)
start_button = pygame.Rect(0, 110, 115, 40)
stop_button = pygame.Rect(0, 165, 115, 40)
running_simulation = False

def game_loop():
    global running_simulation
    running = True
    while running:
        screen.fill(GREEN_BORDER)

        if map_loaded and map_image:
            screen.blit(map_image, (0, 0))
            pygame.draw.circle(screen, YELLOW, source, 10)
            pygame.draw.circle(screen, RED, destination, 10)
            
            if running_simulation:
                courier.move_towards()
            
            courier.draw(screen)

        pygame.draw.rect(screen, YELLOW, load_map_button)
        pygame.draw.rect(screen, BLUE, random_button)
        pygame.draw.rect(screen, GREEN, start_button)
        pygame.draw.rect(screen, RED, stop_button)
        
        font = pygame.font.Font(None, 28)  # Sesuaikan ukuran font agar proporsional

        def center_text(text, button_rect, color):
            text_surface = font.render(text, True, color)
            text_rect = text_surface.get_rect(center=button_rect.center)
            screen.blit(text_surface, text_rect)

        # Render teks pada tombol dengan posisi yang sesuai
        center_text("Load Map", load_map_button, BLACK)
        center_text("Acak", random_button, WHITE)
        center_text("Start", start_button, BLACK)
        center_text("Stop", stop_button, BLACK)

        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if load_map_button.collidepoint(event.pos):
                    load_map()
                elif random_button.collidepoint(event.pos) and map_loaded:
                    randomize_positions()
                elif start_button.collidepoint(event.pos) and map_loaded:
                    start_pos = (int(courier.x), int(courier.y))
                    goal_pos = destination
                    if collision_map[start_pos[0]][start_pos[1]] and collision_map[goal_pos[0]][goal_pos[1]]:
                        path = a_star(start_pos, goal_pos, collision_map)
                        if path:
                            courier.path = path
                            courier.current_target_index = 0
                            courier.moving = True
                            running_simulation = True
                        else:
                            print("Tidak ada jalur yang tersedia!")
                    else:
                        print("Posisi awal/tujuan tidak valid!")
                elif stop_button.collidepoint(event.pos) and map_loaded:
                    running_simulation = False
                    courier.moving = False
    
    pygame.quit()

game_loop()