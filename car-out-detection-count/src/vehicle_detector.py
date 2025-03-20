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
            
            if model_type == "yolov5":
                # Check if YOLOv5 package is installed
                try:
                    import yolov5
                except ImportError:
                    logger.error("YOLOv5 not installed. Please install it with: pip install -U yolov5")
                    raise ImportError("YOLOv5 not installed")
                
                # Load model
                self.model = yolov5.load(model_path, device=self.device)
                
                # Set model parameters
                self.model.conf = self.conf_threshold  # Detection confidence threshold
                self.model.classes = self.classes      # Filter by class (e.g., cars, trucks)
                self.model.max_det = 50               # Maximum number of detections per image
                
                logger.info(f"YOLOv5 model loaded successfully on {self.device}")
            
            elif model_type == "yolov8":
                # Check if Ultralytics package is installed
                try:
                    from ultralytics import YOLO
                except ImportError:
                    logger.error("Ultralytics not installed. Please install it with: pip install -U ultralytics")
                    raise ImportError("Ultralytics not installed")
                
                # Load model
                self.model = YOLO(model_path)
                
                # Set device
                if self.device != "cpu":
                    self.model.to(self.device)
                
                logger.info(f"YOLOv8 model loaded successfully on {self.device}")
            
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
            
            if model_type == "yolov5":
                # Run inference
                results = self.model(frame)
                
                # Process results
                detections = []
                
                # Convert to numpy array
                predictions = results.pred[0].cpu().numpy()
                
                for prediction in predictions:
                    x1, y1, x2, y2, conf, cls = prediction
                    
                    # Filter by confidence and class
                    if conf >= self.conf_threshold and int(cls) in self.classes:
                        # Add detection in format [x1, y1, x2, y2, confidence, class]
                        detections.append([
                            int(x1), int(y1), int(x2), int(y2), 
                            float(conf), int(cls)
                        ])
                
                return detections
            
            elif model_type == "yolov8":
                # Run inference
                results = self.model(frame, conf=self.conf_threshold, classes=self.classes)
                
                # Process results
                detections = []
                
                for result in results:
                    boxes = result.boxes
                    
                    for i, box in enumerate(boxes):
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        
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