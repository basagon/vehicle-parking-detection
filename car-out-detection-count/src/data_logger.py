#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data Logger Module
โมดูลสำหรับบันทึกข้อมูลการนับรถยนต์
"""

import os
import csv
import json
import time
from datetime import datetime
from loguru import logger
from collections import deque

class DataLogger:
    """Class for logging vehicle count data"""
    
    def __init__(self, config):
        """
        Initialize DataLogger
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.log_enabled = config["logging"]["enabled"]
        self.log_file = config["logging"]["log_file"]
        
        # ข้อมูลระบุตำแหน่งของกล้อง
        self.location_id = os.getenv("LOCATION_ID", "unknown")
        self.camera_id = os.getenv("CAMERA_ID", "unknown")
        
        # คิวสำหรับเก็บข้อมูลล่าสุด (เก็บข้อมูล 100 รายการล่าสุด)
        self.recent_counts = deque(maxlen=100)
        
        # สร้างไดเรกทอรีสำหรับไฟล์ log (ถ้ายังไม่มี)
        if self.log_enabled:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            
            # ตรวจสอบว่าไฟล์ log มีอยู่แล้วหรือไม่
            file_exists = os.path.isfile(self.log_file)
            
            # เขียนหัวคอลัมน์ถ้าเป็นไฟล์ใหม่
            if not file_exists:
                with open(self.log_file, 'w', newline='') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(['timestamp', 'date', 'time', 'location_id', 'camera_id', 'count', 'total_count'])
                    
                logger.info(f"Created new log file: {self.log_file}")
            
            logger.info(f"DataLogger initialized to log to {self.log_file}")
    
    def log_vehicle_count(self, count_data):
        """
        บันทึกข้อมูลการนับรถยนต์
        
        Args:
            count_data (dict): ข้อมูลการนับ {'total_count': int, 'new_counts': int}
        """
        if not self.log_enabled:
            print("Logging is disabled")
            return
        
        # สร้างข้อมูล timestamp
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        date = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        # Debug
        print(f"Logging count data: {count_data}")
        
        # บันทึกลง CSV
        try:
            # ตรวจสอบว่าไดเร็กทอรีมีอยู่หรือไม่
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            
            # ตรวจสอบว่าไฟล์มีอยู่แล้วหรือไม่
            file_exists = os.path.isfile(self.log_file)
            
            with open(self.log_file, 'a', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                
                # เขียนหัวคอลัมน์ถ้าเป็นไฟล์ใหม่
                if not file_exists:
                    csv_writer.writerow(['timestamp', 'date', 'time', 'location_id', 'camera_id', 'count', 'total_count'])
                    
                # เขียนข้อมูล
                csv_writer.writerow([
                    timestamp,
                    date,
                    time_str,
                    self.location_id,
                    self.camera_id,
                    count_data['new_counts'],
                    count_data['total_count']
                ])
            
            # เก็บข้อมูลล่าสุดในคิว
            for _ in range(count_data['new_counts']):
                self.recent_counts.append({
                    'timestamp': timestamp,
                    'date': date,
                    'time': time_str,
                    'location_id': self.location_id,
                    'camera_id': self.camera_id,
                    'count': 1,
                    'total_count': count_data['total_count']
                })
            
            print(f"Successfully logged: {count_data['new_counts']} new, {count_data['total_count']} total")
            logger.debug(f"Logged vehicle count: {count_data['new_counts']} new, {count_data['total_count']} total")
        
        except Exception as e:
            print(f"Error logging vehicle count: {e}")
            logger.error(f"Error logging vehicle count: {e}")
    
    def get_recent_counts(self, max_entries=None):
        """
        ดึงข้อมูลการนับล่าสุด
        
        Args:
            max_entries (int, optional): จำนวนข้อมูลล่าสุดที่ต้องการ. ถ้าไม่ระบุจะดึงทั้งหมดที่มีในคิว.
        
        Returns:
            list: รายการข้อมูลการนับล่าสุด
        """
        if max_entries is None:
            return list(self.recent_counts)
        else:
            return list(self.recent_counts)[-max_entries:]
    
    def get_daily_summary(self, date=None):
        """
        ดึงข้อมูลสรุปรายวัน
        
        Args:
            date (str, optional): วันที่ต้องการสรุป ในรูปแบบ "YYYY-MM-DD". ถ้าไม่ระบุจะใช้วันปัจจุบัน.
        
        Returns:
            dict: ข้อมูลสรุปรายวัน
        """
        if not self.log_enabled:
            return {"date": None, "total_count": 0, "hourly_counts": {}}
        
        # ใช้วันปัจจุบันถ้าไม่ได้ระบุ
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # สรุปข้อมูล
        summary = {
            "date": date,
            "total_count": 0,
            "hourly_counts": {}
        }
        
        try:
            with open(self.log_file, 'r', newline='') as csvfile:
                csv_reader = csv.DictReader(csvfile)
                for row in csv_reader:
                    # ข้ามข้อมูลที่ไม่ตรงกับวันที่ต้องการ
                    if row['date'] != date:
                        continue
                    
                    # เพิ่มจำนวนรวม
                    count = int(row['count'])
                    summary["total_count"] += count
                    
                    # เพิ่มจำนวนตามชั่วโมง
                    hour = row['time'].split(':')[0]
                    if hour in summary["hourly_counts"]:
                        summary["hourly_counts"][hour] += count
                    else:
                        summary["hourly_counts"][hour] = count
            
            return summary
        
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return summary
    
    def export_data(self, output_file, start_date=None, end_date=None, format="csv"):
        """
        ส่งออกข้อมูลการนับในช่วงเวลาที่กำหนด
        
        Args:
            output_file (str): ชื่อไฟล์สำหรับส่งออก
            start_date (str, optional): วันที่เริ่มต้น ในรูปแบบ "YYYY-MM-DD". ถ้าไม่ระบุจะใช้ข้อมูลทั้งหมด.
            end_date (str, optional): วันที่สิ้นสุด ในรูปแบบ "YYYY-MM-DD". ถ้าไม่ระบุจะใช้วันปัจจุบัน.
            format (str, optional): รูปแบบการส่งออก ("csv" หรือ "json"). ค่าเริ่มต้นเป็น "csv".
        
        Returns:
            bool: True ถ้าสำเร็จ, False ถ้าล้มเหลว
        """
        if not self.log_enabled:
            logger.error("Logging is disabled, cannot export data")
            return False
        
        # กำหนดวันที่สิ้นสุดเป็นวันปัจจุบันถ้าไม่ได้ระบุ
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # อ่านข้อมูลจากไฟล์ log
            data = []
            with open(self.log_file, 'r', newline='') as csvfile:
                csv_reader = csv.DictReader(csvfile)
                for row in csv_reader:
                    # กรองตามช่วงวันที่
                    if start_date and row['date'] < start_date:
                        continue
                    if end_date and row['date'] > end_date:
                        continue
                    
                    # แปลงประเภทข้อมูล
                    row['count'] = int(row['count'])
                    row['total_count'] = int(row['total_count'])
                    
                    data.append(row)
            
            # ส่งออกข้อมูลตามรูปแบบที่กำหนด
            if format.lower() == "csv":
                with open(output_file, 'w', newline='') as csvfile:
                    fieldnames = ['timestamp', 'date', 'time', 'location_id', 'camera_id', 'count', 'total_count']
                    csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    csv_writer.writeheader()
                    for row in data:
                        csv_writer.writerow(row)
            
            elif format.lower() == "json":
                with open(output_file, 'w') as jsonfile:
                    json.dump(data, jsonfile, indent=4)
            
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
            
            logger.info(f"Data exported to {output_file} in {format} format")
            return True
        
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False