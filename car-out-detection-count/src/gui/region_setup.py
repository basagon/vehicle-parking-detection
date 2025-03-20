#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Region Setup GUI Module
โมดูลสำหรับการตั้งค่าพื้นที่ตรวจจับผ่าน GUI
"""

import cv2
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from loguru import logger

class RegionSetupWidget(QWidget):
    """Widget for setting up region of interest (ROI)"""
    
    # Define signals
    region_updated = pyqtSignal(list)  # จุดของพื้นที่ [[x1, y1], [x2, y2], ...]
    
    def __init__(self, config_manager, video_processor, parent=None):
        """
        Initialize RegionSetupWidget
        
        Args:
            config_manager: ConfigManager instance
            video_processor: VideoProcessor instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.video_processor = video_processor
        self.config = config_manager.get_config()
        
        # Region drawing state
        self.drawing_region = False
        self.region_points = []
        self.current_frame = None
        
        # Setup UI
        self.init_ui()
        
        # Initialize with current config
        self.init_from_config()
    
    def init_ui(self):
        """Initialize user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        main_layout.addWidget(self.video_label)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Enable/disable region
        self.enable_region_checkbox = QCheckBox("เปิดใช้งานการจำกัดพื้นที่ตรวจจับ")
        self.enable_region_checkbox.setChecked(self.config["detection"]["region_of_interest"]["enabled"])
        self.enable_region_checkbox.stateChanged.connect(self.on_enable_region_changed)
        controls_layout.addWidget(self.enable_region_checkbox)
        
        # Buttons
        self.draw_region_button = QPushButton("วาดพื้นที่ใหม่")
        self.draw_region_button.clicked.connect(self.on_draw_region_clicked)
        self.draw_region_button.setEnabled(self.config["detection"]["region_of_interest"]["enabled"])
        controls_layout.addWidget(self.draw_region_button)
        
        self.clear_points_button = QPushButton("ล้างจุดทั้งหมด")
        self.clear_points_button.clicked.connect(self.on_clear_points_clicked)
        self.clear_points_button.setEnabled(self.config["detection"]["region_of_interest"]["enabled"])
        controls_layout.addWidget(self.clear_points_button)
        
        self.save_button = QPushButton("บันทึกการตั้งค่า")
        self.save_button.clicked.connect(self.on_save_clicked)
        controls_layout.addWidget(self.save_button)
        
        # Add controls to main layout
        main_layout.addLayout(controls_layout)
        
        # Instructions
        instructions = QLabel("คำแนะนำ: กดปุ่ม 'วาดพื้นที่ใหม่' แล้วคลิกเพื่อกำหนดพื้นที่ จากนั้นกด 'บันทึกการตั้งค่า'. คลิกซ้ายเพื่อเพิ่มจุด, คลิกขวาเพื่อปิดพื้นที่")
        instructions.setWordWrap(True)
        main_layout.addWidget(instructions)
        
        # Setup timer for video updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_video)
        self.timer.start(30)  # Update every 30ms (approx. 33 FPS)
    
    def init_from_config(self):
        """Initialize widget with current configuration"""
        region_config = self.config["detection"]["region_of_interest"]
        
        # Set region points
        self.region_points = region_config["points"].copy() if region_config["points"] else []
        
        # Set enabled state
        self.enable_region_checkbox.setChecked(region_config["enabled"])
    
    def update_video(self):
        """Update video display with current frame"""
        if self.video_processor.cap is None or not self.video_processor.cap.isOpened():
            return
        
        ret, frame = self.video_processor.read_frame()
        if not ret:
            return
        
        self.current_frame = frame.copy()
        
        # Draw current region if it exists
        if len(self.region_points) > 0:
            # Convert points to numpy array
            points = np.array(self.region_points, np.int32)
            
            # Draw polygon
            cv2.polylines(frame, [points], 
                         True if len(self.region_points) > 2 else False, 
                         (0, 255, 0), 2)
            
            # Fill polygon with semi-transparent color if it's closed
            if len(self.region_points) > 2:
                overlay = frame.copy()
                cv2.fillPoly(overlay, [points], (0, 255, 0, 128))
                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            
            # Draw points
            for i, point in enumerate(self.region_points):
                cv2.circle(frame, tuple(point), 5, (0, 0, 255), -1)
                cv2.putText(frame, str(i+1), (point[0]+10, point[1]), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Convert to QImage and display
        # OpenCV uses BGR format, so we need to convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        image = QImage(rgb_frame.data, w, h, w * ch, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio))
    
    def mousePressEvent(self, event):
        """Handle mouse press events for region drawing"""
        if not self.drawing_region:
            return
        
        # Convert Qt coordinates to OpenCV coordinates
        video_label_rect = self.video_label.geometry()
        pixmap_size = self.video_label.pixmap().size()
        
        # Calculate scaling factor
        scale_x = pixmap_size.width() / self.current_frame.shape[1]
        scale_y = pixmap_size.height() / self.current_frame.shape[0]
        scale = min(scale_x, scale_y)
        
        # Calculate offset for centered image
        offset_x = (video_label_rect.width() - self.current_frame.shape[1] * scale) / 2
        offset_y = (video_label_rect.height() - self.current_frame.shape[0] * scale) / 2
        
        # Calculate image position in widget
        pos_x = (event.x() - video_label_rect.x() - offset_x) / scale
        pos_y = (event.y() - video_label_rect.y() - offset_y) / scale
        
        # Bounds checking
        if (pos_x < 0 or pos_x >= self.current_frame.shape[1] or
            pos_y < 0 or pos_y >= self.current_frame.shape[0]):
            return
        
        # Left click to add point
        if event.button() == Qt.LeftButton:
            self.region_points.append([int(pos_x), int(pos_y)])
        
        # Right click to close polygon
        elif event.button() == Qt.RightButton and len(self.region_points) > 2:
            self.drawing_region = False
            self.draw_region_button.setText("วาดพื้นที่ใหม่")
            self.emit_region_updated()
    
    def on_draw_region_clicked(self):
        """Handle draw region button click"""
        if self.drawing_region:
            self.drawing_region = False
            self.draw_region_button.setText("วาดพื้นที่ใหม่")
        else:
            self.drawing_region = True
            self.region_points = []
            self.draw_region_button.setText("กำลังวาด... (คลิกเพื่อเพิ่มจุด, คลิกขวาเพื่อปิด)")
    
    def on_clear_points_clicked(self):
        """Handle clear points button click"""
        self.region_points = []
        self.drawing_region = False
        self.draw_region_button.setText("วาดพื้นที่ใหม่")
    
    def on_enable_region_changed(self, state):
        """Handle enable region checkbox change"""
        enabled = state == Qt.Checked
        self.draw_region_button.setEnabled(enabled)
        self.clear_points_button.setEnabled(enabled)
    
    def on_save_clicked(self):
        """Handle save button click"""
        if self.enable_region_checkbox.isChecked() and len(self.region_points) < 3:
            QMessageBox.warning(self, "ข้อผิดพลาด", "กรุณาวาดพื้นที่อย่างน้อย 3 จุดก่อนบันทึก")
            return
        
        # Update config
        updates = {
            "detection": {
                "region_of_interest": {
                    "enabled": self.enable_region_checkbox.isChecked(),
                    "points": self.region_points
                }
            }
        }
        
        # Save to config
        if self.config_manager.update_config(updates):
            QMessageBox.information(self, "สำเร็จ", "บันทึกการตั้งค่าเรียบร้อยแล้ว")
            self.config = self.config_manager.get_config()
        else:
            QMessageBox.critical(self, "ข้อผิดพลาด", "ไม่สามารถบันทึกการตั้งค่าได้")
    
    def emit_region_updated(self):
        """Emit region_updated signal"""
        if len(self.region_points) >= 3:
            self.region_updated.emit(self.region_points)
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.timer.stop()
        event.accept()