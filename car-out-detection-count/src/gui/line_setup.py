#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Line Setup GUI Module
โมดูลสำหรับการตั้งค่าเส้นตรวจจับผ่าน GUI
"""

import cv2
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QComboBox, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from loguru import logger

class LineSetupWidget(QWidget):
    """Widget for setting up detection line"""
    
    # Define signals
    line_updated = pyqtSignal(list)  # จุดของเส้น [[x1, y1], [x2, y2]]
    direction_updated = pyqtSignal(str)  # ทิศทาง ("up", "down", "both")
    
    def __init__(self, config_manager, video_processor, parent=None):
        """
        Initialize LineSetupWidget
        
        Args:
            config_manager: ConfigManager instance
            video_processor: VideoProcessor instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.video_processor = video_processor
        self.config = config_manager.get_config()
        
        # Line drawing state
        self.drawing_line = False
        self.line_points = []
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
        
        # Direction selection
        direction_layout = QVBoxLayout()
        direction_label = QLabel("เลือกทิศทางการนับ:")
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["นับรถขาขึ้น (Up)", "นับรถขาลง (Down)", "นับทั้งสองทิศทาง (Both)"])
        self.direction_combo.currentIndexChanged.connect(self.on_direction_changed)
        direction_layout.addWidget(direction_label)
        direction_layout.addWidget(self.direction_combo)
        controls_layout.addLayout(direction_layout)
        
        # Enable/disable line
        self.enable_line_checkbox = QCheckBox("เปิดใช้งานการนับรถตามเส้น")
        self.enable_line_checkbox.setChecked(True)
        self.enable_line_checkbox.stateChanged.connect(self.on_enable_line_changed)
        controls_layout.addWidget(self.enable_line_checkbox)
        
        # Buttons
        buttons_layout = QVBoxLayout()
        self.draw_line_button = QPushButton("วาดเส้นใหม่")
        self.draw_line_button.clicked.connect(self.on_draw_line_clicked)
        buttons_layout.addWidget(self.draw_line_button)
        
        self.save_button = QPushButton("บันทึกการตั้งค่า")
        self.save_button.clicked.connect(self.on_save_clicked)
        buttons_layout.addWidget(self.save_button)
        controls_layout.addLayout(buttons_layout)
        
        # Add controls to main layout
        main_layout.addLayout(controls_layout)
        
        # Instructions
        instructions = QLabel("คำแนะนำ: กดปุ่ม 'วาดเส้นใหม่' แล้วคลิกสองจุดบนภาพเพื่อกำหนดเส้น จากนั้นกด 'บันทึกการตั้งค่า'")
        instructions.setWordWrap(True)
        main_layout.addWidget(instructions)
        
        # Setup timer for video updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_video)
        self.timer.start(30)  # Update every 30ms (approx. 33 FPS)
    
    def init_from_config(self):
        """Initialize widget with current configuration"""
        line_config = self.config["detection"]["line_crossing"]
        
        # Set line points
        self.line_points = line_config["line_position"].copy()
        
        # Set direction
        direction = line_config["direction"]
        if direction == "up":
            self.direction_combo.setCurrentIndex(0)
        elif direction == "down":
            self.direction_combo.setCurrentIndex(1)
        else:  # "both"
            self.direction_combo.setCurrentIndex(2)
        
        # Set enabled state
        self.enable_line_checkbox.setChecked(line_config["enabled"])
    
    def update_video(self):
        """Update video display with current frame"""
        if self.video_processor.cap is None or not self.video_processor.cap.isOpened():
            return
        
        ret, frame = self.video_processor.read_frame()
        if not ret:
            return
        
        self.current_frame = frame.copy()
        
        # Draw current line if it exists
        if len(self.line_points) == 2:
            cv2.line(frame, tuple(self.line_points[0]), tuple(self.line_points[1]), (0, 255, 255), 2)
            
            # Draw direction arrow
            if self.direction_combo.currentIndex() != 2:  # Not "both"
                # Calculate midpoint of the line
                mid_x = (self.line_points[0][0] + self.line_points[1][0]) // 2
                mid_y = (self.line_points[0][1] + self.line_points[1][1]) // 2
                
                # Direction vector perpendicular to line
                dx = self.line_points[1][1] - self.line_points[0][1]  # Perpendicular direction
                dy = self.line_points[0][0] - self.line_points[1][0]  # Perpendicular direction
                
                # Normalize vector
                import math
                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    dx = dx / length * 30  # Arrow length
                    dy = dy / length * 30  # Arrow length
                
                # Adjust direction based on setting
                if self.direction_combo.currentIndex() == 1:  # "down"
                    dx = -dx
                    dy = -dy
                
                # Draw arrow
                arrow_x = int(mid_x + dx)
                arrow_y = int(mid_y + dy)
                cv2.arrowedLine(frame, (mid_x, mid_y), (arrow_x, arrow_y), (0, 255, 255), 2)
        
        # Draw points being placed if in drawing mode
        if self.drawing_line and len(self.line_points) == 1:
            cv2.circle(frame, tuple(self.line_points[0]), 5, (0, 0, 255), -1)
        
        # Convert to QImage and display
        # OpenCV uses BGR format, so we need to convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        image = QImage(rgb_frame.data, w, h, w * ch, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio))
    
    def mousePressEvent(self, event):
        """Handle mouse press events for line drawing"""
        if not self.drawing_line:
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
        
        # Add point
        self.line_points.append([int(pos_x), int(pos_y)])
        
        # If we have two points, exit drawing mode
        if len(self.line_points) >= 2:
            self.drawing_line = False
            self.draw_line_button.setText("วาดเส้นใหม่")
            self.emit_line_updated()
    
    def on_draw_line_clicked(self):
        """Handle draw line button click"""
        if self.drawing_line:
            self.drawing_line = False
            self.draw_line_button.setText("วาดเส้นใหม่")
        else:
            self.drawing_line = True
            self.line_points = []
            self.draw_line_button.setText("กำลังวาด... (คลิก 2 จุด)")
    
    def on_direction_changed(self, index):
        """Handle direction combo box change"""
        direction_map = ["up", "down", "both"]
        self.emit_direction_updated(direction_map[index])
    
    def on_enable_line_changed(self, state):
        """Handle enable line checkbox change"""
        enabled = state == Qt.Checked
        self.draw_line_button.setEnabled(enabled)
        self.direction_combo.setEnabled(enabled)
    
    def on_save_clicked(self):
        """Handle save button click"""
        if len(self.line_points) != 2:
            QMessageBox.warning(self, "ข้อผิดพลาด", "กรุณาวาดเส้นก่อนบันทึก")
            return
        
        # Update config
        updates = {
            "detection": {
                "line_crossing": {
                    "enabled": self.enable_line_checkbox.isChecked(),
                    "line_position": self.line_points,
                    "direction": ["up", "down", "both"][self.direction_combo.currentIndex()]
                }
            }
        }
        
        # Save to config
        if self.config_manager.update_config(updates):
            QMessageBox.information(self, "สำเร็จ", "บันทึกการตั้งค่าเรียบร้อยแล้ว")
            self.config = self.config_manager.get_config()
        else:
            QMessageBox.critical(self, "ข้อผิดพลาด", "ไม่สามารถบันทึกการตั้งค่าได้")
    
    def emit_line_updated(self):
        """Emit line_updated signal"""
        if len(self.line_points) == 2:
            self.line_updated.emit(self.line_points)
    
    def emit_direction_updated(self, direction):
        """Emit direction_updated signal"""
        self.direction_updated.emit(direction)
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.timer.stop()
        event.accept()