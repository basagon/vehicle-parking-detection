#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Client Module
โมดูลสำหรับส่งข้อมูลไปยัง API ภายนอก
"""

import os
import json
import time
import requests
from datetime import datetime
from loguru import logger

class ApiClient:
    """Class for sending data to external API"""
    
    def __init__(self, config):
        """
        Initialize ApiClient
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.api_enabled = config["api"]["enabled"]
        self.api_endpoint = config["api"]["endpoint"]
        self.retry_attempts = config["api"]["retry_attempts"]
        self.timeout = config["api"]["timeout"]
        
        # ข้อมูลการยืนยันตัวตน
        self.api_key = os.getenv("API_KEY", "")
        self.api_secret = os.getenv("API_SECRET", "")
        
        # ข้อมูลระบุตำแหน่ง
        self.location_id = os.getenv("LOCATION_ID", "unknown")
        self.camera_id = os.getenv("CAMERA_ID", "unknown")
        
        if self.api_enabled:
            logger.info(f"ApiClient initialized to send data to {self.api_endpoint}")
        else:
            logger.info("ApiClient initialized but API is disabled")
    
    def send_data(self, data):
        """
        ส่งข้อมูลไปยัง API ภายนอก
        
        Args:
            data (list): รายการข้อมูลที่ต้องการส่ง
        
        Returns:
            bool: True ถ้าส่งสำเร็จ, False ถ้าล้มเหลว
        """
        if not self.api_enabled or not data:
            return False
        
        # เตรียมข้อมูลที่จะส่ง
        payload = {
            "location_id": self.location_id,
            "camera_id": self.camera_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": data
        }
        
        # ส่งข้อมูลไปยัง API
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"Sending data to API (attempt {attempt+1}/{self.retry_attempts})")
                
                # ส่งข้อมูลโดยใช้ POST request
                response = requests.post(
                    self.api_endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": self.api_key,
                        "X-API-Secret": self.api_secret
                    },
                    data=json.dumps(payload),
                    timeout=self.timeout
                )
                
                # ตรวจสอบสถานะการตอบกลับ
                if response.status_code == 200:
                    logger.info(f"Data sent successfully: {len(data)} records")
                    return True
                else:
                    logger.warning(f"API returned status code {response.status_code}: {response.text}")
            
            except requests.RequestException as e:
                logger.error(f"Error sending data to API: {e}")
            
            # รออีกครั้งก่อนลองใหม่ (ยกเว้นครั้งสุดท้าย)
            if attempt < self.retry_attempts - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.debug(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        logger.error(f"Failed to send data to API after {self.retry_attempts} attempts")
        return False
    
    def send_health_check(self):
        """
        ส่งข้อมูลการตรวจสอบสถานะไปยัง API
        
        Returns:
            bool: True ถ้าส่งสำเร็จ, False ถ้าล้มเหลว
        """
        if not self.api_enabled:
            return False
        
        # เตรียมข้อมูลที่จะส่ง
        payload = {
            "location_id": self.location_id,
            "camera_id": self.camera_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "running"
        }
        
        try:
            # ส่งข้อมูลโดยใช้ POST request
            response = requests.post(
                f"{self.api_endpoint}/health",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                    "X-API-Secret": self.api_secret
                },
                data=json.dumps(payload),
                timeout=self.timeout
            )
            
            # ตรวจสอบสถานะการตอบกลับ
            if response.status_code == 200:
                logger.debug("Health check sent successfully")
                return True
            else:
                logger.warning(f"Health check API returned status code {response.status_code}: {response.text}")
                return False
        
        except requests.RequestException as e:
            logger.error(f"Error sending health check to API: {e}")
            return False
    
    def test_connection(self):
        """
        ทดสอบการเชื่อมต่อกับ API
        
        Returns:
            bool: True ถ้าเชื่อมต่อสำเร็จ, False ถ้าล้มเหลว
        """
        if not self.api_enabled:
            logger.warning("API is disabled, cannot test connection")
            return False
        
        try:
            # ส่ง request ไปยัง API เพื่อทดสอบการเชื่อมต่อ
            response = requests.get(
                f"{self.api_endpoint}/status",
                headers={
                    "X-API-Key": self.api_key,
                    "X-API-Secret": self.api_secret
                },
                timeout=self.timeout
            )
            
            # ตรวจสอบสถานะการตอบกลับ
            if response.status_code == 200:
                logger.info("API connection test successful")
                return True
            else:
                logger.warning(f"API connection test failed with status code {response.status_code}: {response.text}")
                return False
        
        except requests.RequestException as e:
            logger.error(f"API connection test failed: {e}")
            return False