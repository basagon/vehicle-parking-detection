#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Video Processor Module
โมดูลสำหรับประมวลผลวิดีโอจาก RTSP และไฟล์วิดีโอ
"""

import os
import cv2
import time
import numpy as np
from loguru import logger

class VideoProcessor:
    """Class for processing video from files or RTSP streams"""
    
    def __init__(self, config):
        """
        Initialize VideoProcessor
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.cap = None
        self.writer = None
        self.frame_width = 0
        self.frame_height = 0
        self.fps = 0
        
        # Try to get environment variables for RTSP
        self.rtsp_username = os.getenv("RTSP_USERNAME", "")
        self.rtsp_password = os.getenv("RTSP_PASSWORD", "")
        self.rtsp_ip = os.getenv("RTSP_IP", "")
        self.rtsp_port = os.getenv("RTSP_PORT", "554")
        self.rtsp_path = os.getenv("RTSP_PATH", "/stream1")
        
        logger.debug("VideoProcessor initialized")
    
    def build_rtsp_url(self):
        """
        สร้าง URL สำหรับการเชื่อมต่อกับกล้อง RTSP
        
        Returns:
            str: RTSP URL
        """
        # ถ้ามีทั้ง username และ password
        if self.rtsp_username and self.rtsp_password:
            auth = f"{self.rtsp_username}:{self.rtsp_password}@"
        else:
            auth = ""
        
        # สร้าง URL
        rtsp_url = f"rtsp://{auth}{self.rtsp_ip}:{self.rtsp_port}{self.rtsp_path}"
        return rtsp_url
    
    def open_video_source(self, source):
        """
        เปิดวิดีโอจากไฟล์หรือ RTSP stream
        
        Args:
            source (str): Path to video file or RTSP URL
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Close existing video source if open
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        # Try to open the video source
        try:
            logger.info(f"Opening video source: {source}")
            
            # ถ้าเป็น RTSP stream ให้ใช้ FFMPEG backend
            if source.startswith("rtsp://"):
                logger.debug("Using FFMPEG backend for RTSP stream")
                # ตั้งค่า FFMPEG parameters เพื่อลดความหน่วง
                self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # ลดขนาด buffer
                # ลดความหน่วงของการถ่ายทอดสด
                self.cap.set(cv2.CAP_PROP_RTSP_TCP, True)
            else:
                # สำหรับไฟล์วิดีโอปกติ
                self.cap = cv2.VideoCapture(source)
            
            # ตรวจสอบว่าเปิดได้หรือไม่
            if not self.cap.isOpened():
                logger.error(f"Failed to open video source: {source}")
                return False
            
            # อ่านค่า properties ของวิดีโอ
            self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Video resolution: {self.frame_width}x{self.frame_height}, FPS: {self.fps}")
            
            # ถ้าต้องการบันทึกวิดีโอผลลัพธ์
            if self.config["general"]["save_output_video"]:
                self._setup_video_writer()
            
            return True
        
        except Exception as e:
            logger.error(f"Error opening video source: {e}")
            return False
    
    def _setup_video_writer(self):
        """Set up video writer for saving output video"""
        try:
            # สร้างไดเรกทอรีสำหรับเก็บวิดีโอผลลัพธ์
            output_dir = self.config["general"]["output_path"]
            os.makedirs(output_dir, exist_ok=True)
            
            # กำหนดชื่อไฟล์ผลลัพธ์
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"output_{timestamp}.mp4")
            
            # สร้าง video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # หรือ 'XVID'
            self.writer = cv2.VideoWriter(
                output_file, fourcc, self.fps, 
                (self.frame_width, self.frame_height)
            )
            
            logger.info(f"Video writer initialized. Output file: {output_file}")
        
        except Exception as e:
            logger.error(f"Error setting up video writer: {e}")
            self.writer = None
    
    def read_frame(self):
        """
        อ่านเฟรมถัดไปจากวิดีโอ
        
        Returns:
            tuple: (success, frame)
        """
        if self.cap is None:
            logger.error("Video source not opened")
            return False, None
        
        return self.cap.read()
    
    def display_frame(self, frame):
        """
        แสดงเฟรมในหน้าต่าง
        
        Args:
            frame (numpy.ndarray): Frame to display
        """
        cv2.imshow('Vehicle Detection', frame)
    
    def write_frame(self, frame):
        """
        เขียนเฟรมลงในไฟล์วิดีโอผลลัพธ์
        
        Args:
            frame (numpy.ndarray): Frame to write
        """
        if self.writer is not None:
            self.writer.write(frame)
    
    def check_exit_key(self, wait_ms=1):
        """
        ตรวจสอบปุ่มกดเพื่อออกจากโปรแกรม
        
        Args:
            wait_ms (int, optional): Wait time in milliseconds. Defaults to 1.
        
        Returns:
            bool: True if exit key (q) is pressed, False otherwise
        """
        key = cv2.waitKey(wait_ms) & 0xFF
        return key == ord('q') or key == 27  # q or ESC
    
    def resize_frame(self, frame, width=None, height=None):
        """
        ปรับขนาดเฟรม
        
        Args:
            frame (numpy.ndarray): Frame to resize
            width (int, optional): Target width. Defaults to None.
            height (int, optional): Target height. Defaults to None.
        
        Returns:
            numpy.ndarray: Resized frame
        """
        if width is None and height is None:
            return frame
        
        h, w = frame.shape[:2]
        
        if width is None:
            # คำนวณ width จาก height เพื่อรักษาอัตราส่วน
            aspect = w / h
            width = int(height * aspect)
        elif height is None:
            # คำนวณ height จาก width เพื่อรักษาอัตราส่วน
            aspect = h / w
            height = int(width * aspect)
        
        return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    
    def apply_text_overlay(self, frame, text, position, font_scale=0.8, thickness=2, 
                           font=cv2.FONT_HERSHEY_SIMPLEX, color=(255, 255, 255), 
                           bg_color=(0, 0, 0), padding=5):
        """
        เพิ่มข้อความลงบนเฟรมพร้อมพื้นหลัง
        
        Args:
            frame (numpy.ndarray): Frame to add text overlay
            text (str): Text to display
            position (tuple): (x, y) position for text
            font_scale (float, optional): Font scale. Defaults to 0.8.
            thickness (int, optional): Text thickness. Defaults to 2.
            font: Font type. Defaults to cv2.FONT_HERSHEY_SIMPLEX.
            color (tuple, optional): Text color (BGR). Defaults to (255, 255, 255).
            bg_color (tuple, optional): Background color (BGR). Defaults to (0, 0, 0).
            padding (int, optional): Padding around text. Defaults to 5.
        
        Returns:
            numpy.ndarray: Frame with text overlay
        """
        # คำนวณขนาดของข้อความ
        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
        
        # คำนวณพิกัดของกล่องพื้นหลัง
        x, y = position
        bg_rect = [
            (x - padding, y - text_height - padding),
            (x + text_width + padding, y + padding)
        ]
        
        # วาดพื้นหลัง
        cv2.rectangle(frame, bg_rect[0], bg_rect[1], bg_color, -1)
        
        # เพิ่มข้อความ
        cv2.putText(frame, text, position, font, font_scale, color, thickness)
        
        return frame
    
    def release(self):
        """Release video resources"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        if self.writer is not None:
            self.writer.release()
            self.writer = None
        
        cv2.destroyAllWindows()
        logger.debug("Video resources released")