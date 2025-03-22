#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Line Counter Module
โมดูลสำหรับนับรถยนต์ที่ตัดผ่านเส้น
"""

import cv2
import math
import numpy as np
from datetime import datetime
from loguru import logger
from collections import defaultdict

class LineCounter:
    """Class for counting vehicles crossing a line"""
    
    def __init__(self, config):
        """
        Initialize LineCounter
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        
        # Load line crossing configuration
        self.line_enabled = config["detection"]["line_crossing"]["enabled"]
        self.line_position = config["detection"]["line_crossing"]["line_position"]
        self.direction = config["detection"]["line_crossing"]["direction"]
        
        # โหลดพิกัดแบบร้อยละ (ถ้ามี)
        if "line_position_percent" in config["detection"]["line_crossing"]:
            self.line_percent = config["detection"]["line_crossing"]["line_position_percent"]
        else:
            # คำนวณจากพิกัดพิกเซลเดิม (ใช้ขนาดมาตรฐาน 1280x720 ถ้าไม่มีการกำหนด)
            self.line_percent = [
                [self.line_position[0][0] / 1280, self.line_position[0][1] / 720],
                [self.line_position[1][0] / 1280, self.line_position[1][1] / 720]
            ]
        
        # Convert line points to numpy array for easier processing
        self.line = np.array(self.line_position, dtype=np.int32)
        
        # Calculate line equation for detection: ax + by + c = 0
        # For a line from (x1, y1) to (x2, y2):
        # a = y2 - y1
        # b = x1 - x2
        # c = x2*y1 - x1*y2
        x1, y1 = self.line[0]
        x2, y2 = self.line[1]
        self.line_params = {
            'a': y2 - y1,
            'b': x1 - x2,
            'c': x2*y1 - x1*y2
        }
        
        # Vehicle tracking for line crossing detection
        # Format: {vehicle_id: {"position": (x, y), "crossed": bool, "time": datetime}}
        self.tracked_vehicles = {}
        
        # Counter for vehicles
        self.total_count = 0
        self.crossed_ids = set()  # Set of vehicle IDs that have crossed the line
        
        logger.info(f"LineCounter initialized with line at {self.line_position}")
    
    def point_side_of_line(self, point):
        """
        Determine which side of the line a point is on
        
        Args:
            point (tuple): (x, y) coordinates of the point
        
        Returns:
            int: 1 if point is on one side, -1 if on the other side, 0 if on the line
        """
        x, y = point
        a, b, c = self.line_params['a'], self.line_params['b'], self.line_params['c']
        
        # Calculate signed distance from point to line
        # d = (ax + by + c) / sqrt(a² + b²)
        distance = (a * x + b * y + c) / math.sqrt(a**2 + b**2)
        
        # Debug
        print(f"Point: ({x}, {y}), Distance to line: {distance}")
        
        if abs(distance) < 1e-9:  # If distance is very close to zero
            return 0
        elif distance > 0:
            return 1
        else:
            return -1
    
    def update(self, frame, detections):
        """
        Update vehicle tracking and count vehicles crossing the line
        
        Args:
            frame (numpy.ndarray): Current frame
            detections (list): List of detections [x1, y1, x2, y2, conf, class]
        
        Returns:
            dict: Count information including total_count and new_counts
        """
        if not self.line_enabled:
            return {"total_count": 0, "new_counts": 0}
        
        # Draw the line on the frame
        self.draw_line(frame)
        
        # Current timestamp
        current_time = datetime.now()
        
        # Set to track new crossings in this update
        new_crossed_ids = set()
        
        # Debug
        print(f"จำนวนวัตถุที่ตรวจพบในเฟรม: {len(detections)}")
        
        # Process each detection
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            
            # Create an ID for this vehicle (use center point and downscaled coordinates for stability)
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # ใช้ ID ที่เสถียรกว่าโดยใช้พิกัดที่มีการปัดเศษลง
            vehicle_id = f"{int(cls)}_{int(center_x//20)}_{int(center_y//20)}"
            
            # Determine which side of the line the vehicle is on
            side = self.point_side_of_line((center_x, center_y))
            
            # Debug
            print(f"Vehicle ID: {vehicle_id}, Side: {side}, Position: ({center_x}, {center_y})")
            
            if vehicle_id in self.tracked_vehicles:
                # Get previous position and side
                prev_center_x, prev_center_y = self.tracked_vehicles[vehicle_id]["position"]
                prev_side = self.point_side_of_line((prev_center_x, prev_center_y))
                
                # Debug
                print(f"Previous side: {prev_side}, Current side: {side}")
                
                # ตรวจสอบการข้ามเส้นแบบเข้มงวดน้อยลง
                if side != prev_side:
                    # Debug info
                    print(f"CROSSING DETECTED! Vehicle {vehicle_id} moved from side {prev_side} to {side}")
                    
                    # คำนวณทิศทางการข้าม
                    crossing_up = prev_side > side
                    
                    # Debug
                    print(f"Direction: {'UP' if crossing_up else 'DOWN'}, Config direction: {self.direction}")
                    
                    count_crossing = False
                    if (self.direction == "up" and crossing_up) or (self.direction == "down" and not crossing_up) or (self.direction == "both"):
                        count_crossing = True
                        print(f"COUNT ACCEPTED! Direction match: {self.direction}")
                    
                    if count_crossing and not self.tracked_vehicles[vehicle_id]["crossed"]:
                        # นับรถ
                        self.tracked_vehicles[vehicle_id]["crossed"] = True
                        self.crossed_ids.add(vehicle_id)
                        self.total_count += 1
                        print(f"*** VEHICLE COUNTED! ID: {vehicle_id}, Total count: {self.total_count} ***")
                        new_crossed_ids.add(vehicle_id)
                        
                        # บันทึกข้อมูลสำคัญ
                        class_names = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}
                        logger.info(f"Vehicle counted: ID={vehicle_id}, Type={class_names.get(int(cls), 'Vehicle')}, Total={self.total_count}")
                
                # Update position
                self.tracked_vehicles[vehicle_id]["position"] = (center_x, center_y)
                self.tracked_vehicles[vehicle_id]["last_seen"] = current_time
            else:
                # New vehicle, add to tracking
                self.tracked_vehicles[vehicle_id] = {
                    "position": (center_x, center_y),
                    "crossed": False,
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "class": int(cls)
                }
                print(f"New vehicle added: {vehicle_id}")
        
        # Clean up tracked vehicles that haven't been seen recently (5 seconds)
        vehicles_to_remove = []
        for vehicle_id, vehicle_data in self.tracked_vehicles.items():
            if (current_time - vehicle_data["last_seen"]).total_seconds() > 5:
                vehicles_to_remove.append(vehicle_id)
        
        for vehicle_id in vehicles_to_remove:
            del self.tracked_vehicles[vehicle_id]
        
        # Draw count information on the frame
        self.draw_count(frame)
        
        # Draw recently crossed vehicles
        for vehicle_id in new_crossed_ids:
            vehicle_data = self.tracked_vehicles[vehicle_id]
            pos = vehicle_data["position"]
            cls = vehicle_data["class"]
            
            # Get class name
            class_names = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}
            class_name = class_names.get(cls, f"Vehicle")
            
            # Draw a circle at the crossing point
            cv2.circle(frame, pos, 10, (0, 0, 255), -1)
            
            # Draw a label
            label = f"{class_name} crossed"
            cv2.putText(frame, label, (pos[0] - 50, pos[1] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        result = {
            "total_count": self.total_count,
            "new_counts": len(new_crossed_ids),
            "new_vehicles": list(new_crossed_ids)
        }
        
        print(f"Update result: {result}")
        return result
    
    def draw_line(self, frame):
        """
        วาดเส้นนับบนเฟรมโดยคำนวณพิกัดตามสัดส่วนของขนาดเฟรม
        
        Args:
            frame (numpy.ndarray): เฟรมที่จะวาด
        """
        h, w = frame.shape[:2]
        # คำนวณพิกัดจริงตามสัดส่วนของภาพปัจจุบัน
        line_start = (int(self.line_percent[0][0] * w), int(self.line_percent[0][1] * h))
        line_end = (int(self.line_percent[1][0] * w), int(self.line_percent[1][1] * h))
        
        # วาดเส้น
        cv2.line(frame, line_start, line_end, (0, 255, 255), 2)
        
        # วาดลูกศรบอกทิศทาง
        if self.direction != "both":
            # คำนวณจุดกึ่งกลางเส้น
            mid_x = (line_start[0] + line_end[0]) // 2
            mid_y = (line_start[1] + line_end[1]) // 2
            
            # เวกเตอร์แนวตั้งฉากกับเส้น
            dx = line_end[1] - line_start[1]  # สลับแกน y เป็นแนวนอน
            dy = line_start[0] - line_end[0]  # สลับแกน x เป็นแนวตั้ง
            
            # ปรับความยาวลูกศร
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                dx = dx / length * 30  # ความยาวลูกศร
                dy = dy / length * 30
            
            # ปรับทิศทางตามการตั้งค่า
            if self.direction == "down":
                dx = -dx
                dy = -dy
            
            # วาดลูกศร
            arrow_x = int(mid_x + dx)
            arrow_y = int(mid_y + dy)
            cv2.arrowedLine(frame, (mid_x, mid_y), (arrow_x, arrow_y), (0, 255, 255), 2)
    
    def draw_count(self, frame):
        """
        แสดงข้อมูลการนับบนเฟรม
        
        Args:
            frame (numpy.ndarray): เฟรมที่จะวาด
        """
        # เตรียมข้อความสำหรับแสดง
        direction_text = "↑" if self.direction == "up" else "↓" if self.direction == "down" else "↕"
        count_text = f"Count {direction_text}: {self.total_count}"
        
        # วาดกล่องพื้นหลัง
        cv2.rectangle(frame, (10, 10), (200, 50), (0, 0, 0), -1)
        
        # วาดข้อความแสดงจำนวนนับ
        cv2.putText(frame, count_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # แสดงจำนวนรถที่กำลังติดตาม
        tracking_text = f"Tracking: {len(self.tracked_vehicles)}"
        cv2.putText(frame, tracking_text, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    def reset_counter(self):
        """Reset the vehicle counter"""
        self.total_count = 0
        self.crossed_ids = set()
        self.tracked_vehicles = {}
        logger.info("Vehicle counter reset")
    
    def set_line_position(self, line_position):
        """
        Set a new position for the counting line
        
        Args:
            line_position (list): List of two points [[x1, y1], [x2, y2]]
        """
        self.line_position = line_position
        self.line = np.array(line_position, dtype=np.int32)
        
        # Recalculate line equation
        x1, y1 = self.line[0]
        x2, y2 = self.line[1]
        self.line_params = {
            'a': y2 - y1,
            'b': x1 - x2,
            'c': x2*y1 - x1*y2
        }
        
        # Reset counter
        self.reset_counter()
        
        logger.info(f"Line position updated to {line_position}")