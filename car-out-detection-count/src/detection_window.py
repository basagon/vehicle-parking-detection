#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Detection Window Module
หน้าต่างแสดงผลการตรวจจับและนับรถยนต์
"""

import os
import sys
import cv2
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QLabel, QPushButton, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from loguru import logger

from src.video_processor import VideoProcessor
from src.vehicle_detector import VehicleDetector
from src.line_counter import LineCounter
from src.data_logger import DataLogger

class DetectionWindow(QMainWindow):
    """Window for vehicle detection and counting"""
    
    def __init__(self, config_manager):
        """
        Initialize detection window
        
        Args:
            config_manager: ConfigManager instance
        """
        super().__init__()
        
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
        # Initialize components
        self.video_processor = VideoProcessor(self.config)
        self.vehicle_detector = VehicleDetector(self.config)
        self.line_counter = LineCounter(self.config)
        self.data_logger = DataLogger(self.config)
        
        # Initialize UI
        self.init_ui()
        
        # Open video source
        self.open_video_source()
        
        # Start detection
        self.total_count = 0
        self.start_detection()
    
    def init_ui(self):
        """Initialize user interface"""
        # Set window properties
        self.setWindowTitle(f"{self.config['general']['app_name']} - การตรวจจับรถยนต์")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Video display
        self.video_label = QLabel("กำลังเริ่มต้นระบบตรวจจับ...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(800, 600)
        main_layout.addWidget(self.video_label)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Count display
        self.count_label = QLabel("จำนวนรถที่นับได้: 0")
        self.count_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        controls_layout.addWidget(self.count_label)
        
        # Stop button
        self.stop_button = QPushButton("หยุดการตรวจจับ")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        controls_layout.addWidget(self.stop_button)
        
        main_layout.addLayout(controls_layout)
    
    def open_video_source(self):
        """Open video source based on configuration"""
        try:
            if self.config["general"]["test_mode"]:
                video_source = self.config["video_source"]["test_video"]
                logger.info(f"Using test video: {video_source}")
            else:
                video_source = self.video_processor.build_rtsp_url()
                logger.info(f"Using RTSP stream: {video_source}")
            
            if not self.video_processor.open_video_source(video_source):
                QMessageBox.critical(self, "ข้อผิดพลาด", f"ไม่สามารถเปิดแหล่งวิดีโอได้: {video_source}")
                self.close()
        except Exception as e:
            logger.exception(f"Error opening video source: {e}")
            QMessageBox.critical(self, "ข้อผิดพลาด", f"เกิดข้อผิดพลาด: {str(e)}")
            self.close()
    
    def start_detection(self):
        """Start the detection process"""
        # Create timer for processing frames
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(30)  # 30ms ~ 33fps
    
    def process_frame(self):
        """Process a single frame and update the display"""
        try:
            # Read frame
            ret, frame = self.video_processor.read_frame()
            if not ret:
                self.count_label.setText("สิ้นสุดวิดีโอ หรือมีปัญหาในการอ่านเฟรม")
                self.timer.stop()
                return
            
            # Process frame (only if not None)
            if frame is None:
                return
                
            # Make a copy to avoid modifying the original
            display_frame = frame.copy()
            
            # Detect vehicles
            detections = self.vehicle_detector.detect(frame)
            
            # Draw detections
            if detections is not None:
                display_frame = self.vehicle_detector.draw_detections(display_frame, detections)
            
            # Count vehicles crossing the line
            counts = self.line_counter.update(display_frame, detections if detections is not None else [])
            
            # Update count display
            if counts["new_counts"] > 0:
                self.total_count += counts["new_counts"]
                self.count_label.setText(f"จำนวนรถที่นับได้: {self.total_count}")
                
                # Log data
                self.data_logger.log_vehicle_count({"total_count": self.total_count, "new_counts": counts["new_counts"]})
            
            # Display frame
            self.display_frame(display_frame)
        
        except Exception as e:
            logger.exception(f"Error processing frame: {e}")
            self.count_label.setText(f"เกิดข้อผิดพลาด: {str(e)}")
    
    def display_frame(self, frame):
        """Display a frame on the video label"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create QImage from numpy array
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Create pixmap and set to label
            pixmap = QPixmap.fromImage(image)
            self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio))
        
        except Exception as e:
            logger.exception(f"Error displaying frame: {e}")
    
    def on_stop_clicked(self):
        """Handle stop button click"""
        # Stop timer
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        
        # Release video resources
        self.video_processor.release()
        
        # Show confirmation dialog
        QMessageBox.information(self, "การตรวจจับสิ้นสุด", 
                              f"สิ้นสุดการตรวจจับ\nจำนวนรถที่นับได้ทั้งหมด: {self.total_count}")
        
        # Close window
        self.close()
    
    def closeEvent(self, event):
        """Handle window close event"""