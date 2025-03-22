#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI Module for Vehicle Detection System
โมดูล GUI สำหรับระบบตรวจจับรถยนต์
"""

import os
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                              QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from loguru import logger
import cv2

# Import sub-modules
from src.video_processor import VideoProcessor
from src.vehicle_detector import VehicleDetector
from src.line_counter import LineCounter
from src.data_logger import DataLogger
from src.detection_window import DetectionWindow

# Import GUI components
from src.gui.line_setup import LineSetupWidget
from src.gui.region_setup import RegionSetupWidget

def create_gui_app(config_manager):
    """
    Create and initialize GUI application
    
    Args:
        config_manager: ConfigManager instance
    
    Returns:
        QApplication: The QApplication instance
    """
    # Create application
    app = QApplication(sys.argv)
    
    # Create main window
    main_window = VehicleDetectionGUI(config_manager)
    main_window.show()
    
    return app

class VehicleDetectionGUI(QMainWindow):
    """Main window for Vehicle Detection System GUI"""
    
    def __init__(self, config_manager):
        """
        Initialize main window
        
        Args:
            config_manager: ConfigManager instance
        """
        super().__init__()
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
        # สร้าง central widget ก่อน
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Initialize components
        self.video_processor = VideoProcessor(self.config)
        self.vehicle_detector = VehicleDetector(self.config)
        
        # Setup UI
        self.init_ui()
        
        logger.info("GUI initialized")
    
    def init_ui(self):
        """Initialize user interface"""
        # Set window properties
        self.setWindowTitle(f"{self.config['general']['app_name']} - Configuration")
        self.setGeometry(100, 100, 800, 600)
        
        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_source_tab()
        self.create_line_setup_tab()
        self.create_region_setup_tab()
        self.create_settings_tab()
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("บันทึกการตั้งค่าทั้งหมด")
        self.save_button.clicked.connect(self.on_save_all_clicked)
        button_layout.addWidget(self.save_button)
        
        self.start_button = QPushButton("เริ่มระบบตรวจจับ")
        self.start_button.clicked.connect(self.on_start_clicked)
        button_layout.addWidget(self.start_button)
        
        self.exit_button = QPushButton("ออกจากโปรแกรม")
        self.exit_button.clicked.connect(self.close)
        button_layout.addWidget(self.exit_button)
        
        main_layout.addLayout(button_layout)
    
    def create_source_tab(self):
        """Create video source tab"""
        source_tab = QWidget()
        self.tab_widget.addTab(source_tab, "แหล่งที่มาของวิดีโอ")
        
        layout = QVBoxLayout(source_tab)
        
        # Mode selection
        mode_layout = QHBoxLayout()
        mode_label = QLabel("โหมดการทำงาน:")
        mode_layout.addWidget(mode_label)
        
        self.test_mode_button = QPushButton("โหมดทดสอบ (ไฟล์วิดีโอ)")
        self.test_mode_button.setCheckable(True)
        self.test_mode_button.setChecked(self.config["general"]["test_mode"])
        self.test_mode_button.clicked.connect(lambda: self.on_mode_clicked(True))
        mode_layout.addWidget(self.test_mode_button)
        
        self.production_mode_button = QPushButton("โหมดใช้งานจริง (RTSP)")
        self.production_mode_button.setCheckable(True)
        self.production_mode_button.setChecked(not self.config["general"]["test_mode"])
        self.production_mode_button.clicked.connect(lambda: self.on_mode_clicked(False))
        mode_layout.addWidget(self.production_mode_button)
        
        layout.addLayout(mode_layout)
        
        # Test video selection
        test_video_layout = QHBoxLayout()
        test_video_label = QLabel("ไฟล์วิดีโอสำหรับทดสอบ:")
        test_video_layout.addWidget(test_video_label)
        
        self.test_video_path = QLabel(self.config["video_source"]["test_video"])
        test_video_layout.addWidget(self.test_video_path)
        
        self.browse_button = QPushButton("เลือกไฟล์")
        self.browse_button.clicked.connect(self.on_browse_clicked)
        test_video_layout.addWidget(self.browse_button)
        
        layout.addLayout(test_video_layout)
        
        # RTSP info (read-only)
        layout.addWidget(QLabel("ข้อมูล RTSP (กำหนดใน .env):"))
        
        rtsp_layout = QVBoxLayout()
        rtsp_layout.addWidget(QLabel(f"Username: {os.getenv('RTSP_USERNAME', '')}"))
        rtsp_layout.addWidget(QLabel(f"IP: {os.getenv('RTSP_IP', '')}"))
        rtsp_layout.addWidget(QLabel(f"Port: {os.getenv('RTSP_PORT', '554')}"))
        rtsp_layout.addWidget(QLabel(f"Path: {os.getenv('RTSP_PATH', '/stream1')}"))
        
        # Build complete RTSP URL (mask password)
        rtsp_username = os.getenv("RTSP_USERNAME", "")
        rtsp_password = "********" if os.getenv("RTSP_PASSWORD", "") else ""
        rtsp_ip = os.getenv("RTSP_IP", "")
        rtsp_port = os.getenv("RTSP_PORT", "554")
        rtsp_path = os.getenv("RTSP_PATH", "/stream1")
        
        auth = f"{rtsp_username}:{rtsp_password}@" if rtsp_username and rtsp_password else ""
        rtsp_url = f"rtsp://{auth}{rtsp_ip}:{rtsp_port}{rtsp_path}"
        
        rtsp_layout.addWidget(QLabel(f"RTSP URL: {rtsp_url}"))
        layout.addLayout(rtsp_layout)
        
        # Test connection button
        self.test_connection_button = QPushButton("ทดสอบการเชื่อมต่อ")
        self.test_connection_button.clicked.connect(self.on_test_connection_clicked)
        layout.addWidget(self.test_connection_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def create_line_setup_tab(self):
        """Create line setup tab"""
        # Create line setup widget
        self.line_setup_widget = LineSetupWidget(self.config_manager, self.video_processor)
        
        # Add to tab widget
        self.tab_widget.addTab(self.line_setup_widget, "ตั้งค่าเส้นตรวจจับ")
    
    def create_settings_tab(self):
        """Create general settings tab"""
        settings_tab = QWidget()
        self.tab_widget.addTab(settings_tab, "ตั้งค่าทั่วไป")
        
        # TODO: Add more settings as needed
        layout = QVBoxLayout(settings_tab)
        layout.addWidget(QLabel("การตั้งค่าทั่วไปจะถูกเพิ่มในอนาคต"))
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def on_mode_clicked(self, test_mode):
        """
        Handle mode selection
        
        Args:
            test_mode (bool): True for test mode, False for production mode
        """
        # Update button states
        self.test_mode_button.setChecked(test_mode)
        self.production_mode_button.setChecked(not test_mode)
        
        # Update config
        updates = {
            "general": {
                "test_mode": test_mode
            }
        }
        
        self.config_manager.update_config(updates)
        self.config = self.config_manager.get_config()
    
    def on_browse_clicked(self):
        """Handle browse button click"""
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "เลือกไฟล์วิดีโอ", "", "Video Files (*.mp4 *.avi *.mkv)"
        )
        
        if file_path:
            # Update UI
            self.test_video_path.setText(file_path)
            
            # Update config
            updates = {
                "video_source": {
                    "test_video": file_path
                }
            }
            
            self.config_manager.update_config(updates)
            self.config = self.config_manager.get_config()
    
    def on_test_connection_clicked(self):
        """Handle test connection button click"""
        if self.config["general"]["test_mode"]:
            # Test video file
            video_path = self.config["video_source"]["test_video"]
            
            if not os.path.exists(video_path):
                QMessageBox.warning(self, "ข้อผิดพลาด", f"ไม่พบไฟล์วิดีโอ: {video_path}")
                return
            
            if self.video_processor.open_video_source(video_path):
                QMessageBox.information(self, "สำเร็จ", 
                                      f"สามารถเปิดไฟล์วิดีโอได้: {video_path}\n"
                                      f"ขนาด: {self.video_processor.frame_width}x{self.video_processor.frame_height}\n"
                                      f"FPS: {self.video_processor.fps}")
                self.video_processor.release()
            else:
                QMessageBox.critical(self, "ข้อผิดพลาด", f"ไม่สามารถเปิดไฟล์วิดีโอได้: {video_path}")
        else:
            # Test RTSP connection
            rtsp_url = self.video_processor.build_rtsp_url()
            
            QMessageBox.information(self, "กำลังทดสอบ", 
                                 f"กำลังทดสอบการเชื่อมต่อไปยัง:\n{rtsp_url}\n\n"
                                 "อาจใช้เวลาสักครู่...")
            
            if self.video_processor.open_video_source(rtsp_url):
                QMessageBox.information(self, "สำเร็จ", 
                                      f"เชื่อมต่อ RTSP สำเร็จ\n"
                                      f"ขนาด: {self.video_processor.frame_width}x{self.video_processor.frame_height}\n"
                                      f"FPS: {self.video_processor.fps}")
                self.video_processor.release()
            else:
                QMessageBox.critical(self, "ข้อผิดพลาด", f"ไม่สามารถเชื่อมต่อ RTSP ได้: {rtsp_url}")
    
    def on_save_all_clicked(self):
        """Handle save all button click"""
        if self.config_manager.save_config():
            QMessageBox.information(self, "สำเร็จ", "บันทึกการตั้งค่าทั้งหมดเรียบร้อยแล้ว")
        else:
            QMessageBox.critical(self, "ข้อผิดพลาด", "ไม่สามารถบันทึกการตั้งค่าได้")
    
    def on_start_clicked(self):
        """Handle start button click"""
        # Confirm save before starting
        reply = QMessageBox.question(self, "ยืนยัน", 
                                "ต้องการบันทึกการตั้งค่าและเริ่มระบบตรวจจับหรือไม่?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        
        if reply == QMessageBox.Yes:
            # Save config
            if not self.config_manager.save_config():
                QMessageBox.critical(self, "ข้อผิดพลาด", "ไม่สามารถบันทึกการตั้งค่าได้")
                return
            
            # Import detection window here to avoid circular imports
            from src.detection_window import DetectionWindow
            
            # Create and show detection window
            try:
                self.detection_window = DetectionWindow(self.config_manager)
                self.detection_window.show()
            except Exception as e:
                QMessageBox.critical(self, "ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการเริ่มระบบตรวจจับ: {str(e)}")
                logger.exception(f"Error starting detection: {e}")
    
    def start_detection_view(self):
        """Start detection and show live view"""
        # สร้าง widget ใหม่แทนที่จะใช้ central widget เดิม
        new_central_widget = QWidget()
        self.setCentralWidget(new_central_widget)
        
        # สร้าง layout ใหม่
        layout = QVBoxLayout(new_central_widget)
        
        # สร้าง video display
        self.detection_view = QLabel("กำลังเริ่มการตรวจจับ...")
        self.detection_view.setAlignment(Qt.AlignCenter)
        self.detection_view.setMinimumSize(800, 600)
        layout.addWidget(self.detection_view)
        
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
        
        layout.addLayout(controls_layout)
        
        # เตรียมการเริ่มต้นตรวจจับ
        try:
            # กำหนดแหล่งวิดีโอ
            if self.config["general"]["test_mode"]:
                video_source = self.config["video_source"]["test_video"]
                logger.info(f"Using test video: {video_source}")
            else:
                video_source = self.video_processor.build_rtsp_url()
                logger.info(f"Using RTSP stream: {video_source}")
            
            # เปิดแหล่งวิดีโอ
            if not self.video_processor.open_video_source(video_source):
                raise Exception(f"ไม่สามารถเปิดแหล่งวิดีโอได้: {video_source}")
            
            # สร้าง line counter
            self.line_counter = LineCounter(self.config)
            
            # สร้าง data logger
            self.data_logger = DataLogger(self.config)
            
            # เริ่ม timer สำหรับประมวลผลเฟรม
            self.detection_timer = QTimer(self)
            self.detection_timer.timeout.connect(self.process_frame)
            self.detection_timer.start(30)  # 30ms ~ 33fps
            
            # อัพเดทชื่อหน้าต่าง
            self.setWindowTitle(f"{self.config['general']['app_name']} - การตรวจจับกำลังทำงาน")
            
            # อัพเดทสถานะ
            self.total_count = 0
            
        except Exception as e:
            logger.exception(f"Error in start_detection_view: {e}")
            self.video_processor.release()
            raise Exception(f"ไม่สามารถเริ่มระบบตรวจจับได้: {str(e)}")
    
    def process_frame(self):
        """Process a single frame for detection"""
        try:
            # อ่านเฟรม
            ret, frame = self.video_processor.read_frame()
            if not ret:
                self.count_label.setText("สิ้นสุดวิดีโอ หรือมีปัญหาในการอ่านเฟรม")
                self.detection_timer.stop()
                return
            
            # ตรวจจับรถยนต์
            detections = self.vehicle_detector.detect(frame)
            
            # วาดกรอบการตรวจจับ
            frame = self.vehicle_detector.draw_detections(frame, detections)
            
            # นับรถยนต์ที่ตัดผ่านเส้น
            counts = self.line_counter.update(frame, detections)
            
            # อัพเดทการแสดงผลจำนวนนับ
            if counts["new_counts"] > 0:
                self.total_count += counts["new_counts"]
                self.count_label.setText(f"จำนวนรถที่นับได้: {self.total_count}")
                
                # บันทึกข้อมูล
                self.data_logger.log_vehicle_count({"total_count": self.total_count, "new_counts": counts["new_counts"]})
            
            # แสดงเฟรม
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.detection_view.setPixmap(QPixmap.fromImage(image))
            
        except Exception as e:
            logger.exception(f"Error in process_frame: {e}")
            self.count_label.setText(f"เกิดข้อผิดพลาด: {str(e)}")
    
    def on_stop_clicked(self):
        """Handle stop button click"""
        # หยุด timer
        if hasattr(self, 'detection_timer'):
            self.detection_timer.stop()
        
        # คืนทรัพยากรวิดีโอ
        self.video_processor.release()
        
        # แสดง dialog ยืนยัน
        QMessageBox.information(self, "การตรวจจับสิ้นสุด", 
                              f"สิ้นสุดการตรวจจับ\nจำนวนรถที่นับได้ทั้งหมด: {self.total_count}")
        
        # กลับไปที่หน้าตั้งค่า
        self.recreate_ui()
    
    def recreate_ui(self):
        """Recreate the original UI"""
        # สร้าง widget ใหม่
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # สร้าง UI ใหม่
        self.init_ui()
        
        # อัพเดทชื่อหน้าต่าง
        self.setWindowTitle(f"{self.config['general']['app_name']} - Configuration")
        
    # เพิ่มแท็บสำหรับการตั้งค่าพื้นที่
    def create_region_setup_tab(self):
        """Create region of interest setup tab"""
        # ใช้ RegionSetupWidget ที่มีอยู่แล้ว
        self.region_setup_widget = RegionSetupWidget(self.config_manager, self.video_processor)
        self.tab_widget.addTab(self.region_setup_widget, "ตั้งค่าพื้นที่ตรวจจับ")