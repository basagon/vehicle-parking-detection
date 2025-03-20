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
        
        # Process each detection
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            
            # Create an ID for this vehicle (use the center point for now)
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # In a real application, you would use a tracking algorithm to assign
            # a persistent ID to each vehicle. For simplicity, we're using the
            # detection coordinates as an ID.
            vehicle_id = f"{int(center_x)}_{int(center_y)}_{int(cls)}"
            
            # Determine which side of the line the vehicle is on
            side = self.point_side_of_line((center_x, center_y))
            
            if vehicle_id in self.tracked_vehicles:
                # Get previous position and side
                prev_center_x, prev_center_y = self.tracked_vehicles[vehicle_id]["position"]
                prev_side = self.point_side_of_line((prev_center_x, prev_center_y))
                
                # Check if vehicle has crossed the line
                if side != prev_side and side != 0 and not self.tracked_vehicles[vehicle_id]["crossed"]:
                    # Determine if the crossing direction matches our counting direction
                    crossing_up = prev_side > side  # Moving from positive to negative (crossing upward)
                    
                    count_crossing = False
                    if self.direction == "up" and crossing_up:
                        count_crossing = True
                    elif self.direction == "down" and not crossing_up:
                        count_crossing = True
                    elif self.direction == "both":
                        count_crossing = True
                    
                    if count_crossing:
                        # Mark as crossed
                        self.tracked_vehicles[vehicle_id]["crossed"] = True
                        self.tracked_vehicles[vehicle_id]["cross_time"] = current_time
                        
                        if vehicle_id not in self.crossed_ids:
                            self.crossed_ids.add(vehicle_id)
                            new_crossed_ids.add(vehicle_id)
                            self.total_count += 1
                
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
        
        return {
            "total_count": self.total_count,
            "new_counts": len(new_crossed_ids),
            "new_vehicles": list(new_crossed_ids)
        }
    
    def draw_line(self, frame):
        """
        Draw counting line on the frame
        
        Args:
            frame (numpy.ndarray): Frame to draw on
        """
        # Draw the line
        cv2.line(frame, tuple(self.line[0]), tuple(self.line[1]), (0, 255, 255), 2)
        
        # Draw direction arrow
        if self.direction != "both":
            # Calculate midpoint of the line
            mid_x = (self.line[0][0] + self.line[1][0]) // 2
            mid_y = (self.line[0][1] + self.line[1][1]) // 2
            
            # Direction vector perpendicular to line
            dx = self.line[1][1] - self.line[0][1]  # Perpendicular direction
            dy = self.line[0][0] - self.line[1][0]  # Perpendicular direction
            
            # Normalize vector
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                dx = dx / length * 30  # Arrow length
                dy = dy / length * 30  # Arrow length
            
            # Adjust direction based on setting
            if self.direction == "down":
                dx = -dx
                dy = -dy
            
            # Draw arrow
            arrow_x = int(mid_x + dx)
            arrow_y = int(mid_y + dy)
            cv2.arrowedLine(frame, (mid_x, mid_y), (arrow_x, arrow_y), (0, 255, 255), 2)
    
    def draw_count(self, frame):
        """
        Draw count information on the frame
        
        Args:
            frame (numpy.ndarray): Frame to draw on
        """
        # Prepare count text
        direction_text = "↑" if self.direction == "up" else "↓" if self.direction == "down" else "↕"
        count_text = f"Count {direction_text}: {self.total_count}"
        
        # Draw count text
        cv2.rectangle(frame, (10, 10), (200, 50), (0, 0, 0), -1)
        cv2.putText(frame, count_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
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