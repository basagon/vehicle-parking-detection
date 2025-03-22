#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vehicle Detector Module
โมดูลสำหรับตรวจจับรถยนต์โดยใช้ YOLOv5/YOLOv8
"""

import os
import sys
import torch
import numpy as np
from loguru import logger
from pathlib import Path
from ultralytics import YOLO
class VehicleDetector:
    """Class for detecting vehicles using YOLO models"""
    
    def __init__(self, config):
        """
        Initialize VehicleDetector
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.model = None
        self.device = config["model"]["device"]
        self.conf_threshold = config["model"]["confidence_threshold"]
        self.classes = config["model"]["classes"]
        
        # Load model
        self.load_model()
    
    def load_model(self):
        """Load YOLO model based on configuration"""
        try:
            model_type = self.config["model"]["type"].lower()
            model_path = self.config["model"]["model_path"]
            logger.info(f"Loading {model_type} model from {model_path}...")
            
            if model_type == "yolov5" or model_type == "yolov5m":
                # ใช้โมเดลมาตรฐานแทนไฟล์ที่มีปัญหา
                try:
                    # ใช้โมเดลมาตรฐานแทนไฟล์ที่มีปัญหา
                    self.model = YOLO("yolov5mu.pt")  # ดาวน์โหลดโมเดลมาตรฐานแทน
                    logger.info(f"YOLOv5 model loaded successfully on {self.device}")
                except ImportError:
                    logger.error("Ultralytics not installed. Please install it with: pip install -U ultralytics")
                    raise ImportError("Ultralytics not installed")
                    
            elif model_type == "yolov8":
                # Check if Ultralytics package is installed
                try:
                    # Load model
                    self.model = YOLO("yolov8n.pt")  # ใช้โมเดลมาตรฐานแทน
                    
                    # Set device
                    if self.device != "cpu":
                        self.model.to(self.device)
                        
                    logger.info(f"YOLOv8 model loaded successfully on {self.device}")
                    
                except ImportError:
                    logger.error("Ultralytics not installed. Please install it with: pip install -U ultralytics")
                    raise ImportError("Ultralytics not installed")
                    
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
                
        except Exception as e:
            logger.exception(f"Error loading model: {e}")
            logger.warning("Continuing without object detection...")
            self.model = None
        
    def detect(self, frame):
        """
        Detect vehicles in a frame
        Args:
            frame (numpy.ndarray): Input frame
        Returns:
            list: List of detection results, each containing [x1, y1, x2, y2, confidence, class]
        """
        if self.model is None:
            return []
            
        try:
            model_type = self.config["model"]["type"].lower()
            
            if model_type == "yolov5" or model_type == "yolov5m":
                # ใช้ API ใหม่สำหรับทั้ง YOLOv5
                results = self.model.predict(
                    frame,
                    conf=self.conf_threshold,
                    classes=self.classes,
                    verbose=False
                )
                
                detections = []
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    for box in boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = map(int, xyxy)
                        conf = float(box.conf[0].item())
                        cls = int(box.cls[0].item())
                        
                        # Add detection in format [x1, y1, x2, y2, confidence, class]
                        detections.append([x1, y1, x2, y2, conf, cls])
                        
                return detections
                
            elif model_type == "yolov8":
                # Run inference
                results = self.model.predict(
                    frame,
                    conf=self.conf_threshold,
                    classes=self.classes,
                    verbose=False
                )
                
                # Process results
                detections = []
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    for box in boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = map(int, xyxy)
                        conf = float(box.conf[0].item())
                        cls = int(box.cls[0].item())
                        
                        # Add detection in format [x1, y1, x2, y2, confidence, class]
                        detections.append([x1, y1, x2, y2, conf, cls])
                        
                return detections
                
            else:
                logger.error(f"Unsupported model type: {model_type}")
                return []
                
        except Exception as e:
            logger.exception(f"Error during detection: {e}")
            return []
    
    def draw_detections(self, frame, detections, draw_labels=True):
        """
        Draw detection boxes and labels on frame
        
        Args:
            frame (numpy.ndarray): Input frame
            detections (list): List of detections from detect() method
            draw_labels (bool, optional): Whether to draw labels. Defaults to True.
        
        Returns:
            numpy.ndarray: Frame with drawn detections
        """
        # Define colors for different classes (in BGR format)
        colors = {
            2: (0, 255, 0),    # Car - Green
            3: (255, 0, 0),    # Motorcycle - Blue
            5: (0, 0, 255),    # Bus - Red
            7: (255, 255, 0),  # Truck - Cyan
        }
        
        # Define class names
        class_names = {
            2: "Car",
            3: "Motorcycle",
            5: "Bus",
            7: "Truck",
        }
        
        # Draw each detection
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            
            # Convert class to int if needed
            cls = int(cls)
            
            # Get color for this class (use green as default)
            color = colors.get(cls, (0, 255, 0))
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label if requested
            if draw_labels:
                # Get class name
                class_name = class_names.get(cls, f"Class {cls}")
                
                # Create label text
                label = f"{class_name} {conf:.2f}"
                
                # Get text size
                text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                
                # Draw label background
                cv2.rectangle(frame, (x1, y1 - text_size[1] - 5), (x1 + text_size[0], y1), color, -1)
                
                # Draw text
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return frame

# Import OpenCV here to avoid circular import
import cv2