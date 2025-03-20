#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Config Manager Module
โมดูลสำหรับจัดการการตั้งค่าจากไฟล์ config.yaml และ .env
"""

import os
import re
import yaml
import json
from dotenv import load_dotenv

class ConfigManager:
    """Class for managing configuration from YAML file and .env file"""
    
    def __init__(self, config_path="config.yaml"):
        """
        Initialize ConfigManager
        
        Args:
            config_path (str): Path to the configuration file
        """
        self.config_path = config_path
        self.config = {}
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Load configuration
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            
            # Replace environment variables in config
            self.replace_env_vars(self.config)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            # Use default configuration
            self.config = self._get_default_config()
    
    def get_config(self):
        """Get the current configuration"""
        return self.config
    
    def save_config(self, config=None):
        """
        Save configuration to YAML file
        
        Args:
            config (dict, optional): Configuration to save. If None, use current config.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if config:
            self.config = config
        
        try:
            # Create backup of existing config
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.bak"
                try:
                    os.replace(self.config_path, backup_path)
                except Exception as e:
                    print(f"Warning: Failed to create backup of config file: {e}")
            
            # Save new config
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.config, file, default_flow_style=False, sort_keys=False)
            
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def update_config(self, updates):
        """
        Update configuration with new values
        
        Args:
            updates (dict): Dictionary with configuration updates
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Deep update the config
        self._deep_update(self.config, updates)
        
        # Save the updated config
        return self.save_config()
    
    def replace_env_vars(self, obj):
        """
        Recursively replace environment variables in configuration
        Format: ${ENV_VAR}
        
        Args:
            obj: Object to process (dict, list, str, etc.)
        
        Returns:
            The processed object with environment variables replaced
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = self.replace_env_vars(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                obj[i] = self.replace_env_vars(item)
        elif isinstance(obj, str):
            # Find environment variables in the string
            pattern = r'\$\{([^}^{]+)\}'
            matches = re.finditer(pattern, obj)
            for match in matches:
                env_var = match.group(1)
                env_value = os.getenv(env_var, '')
                obj = obj.replace(f"${{{env_var}}}", env_value)
        return obj
    
    def _deep_update(self, source, updates):
        """
        Deep update a nested dictionary
        
        Args:
            source (dict): Source dictionary to update
            updates (dict): Updates to apply
        """
        for key, value in updates.items():
            if key in source and isinstance(source[key], dict) and isinstance(value, dict):
                self._deep_update(source[key], value)
            else:
                source[key] = value
    
    def _get_default_config(self):
        """Get default configuration if config file cannot be loaded"""
        return {
            "general": {
                "app_name": "Vehicle Detection System",
                "version": "1.0.0",
                "test_mode": True,
                "debug": True,
                "display_output": True,
                "save_output_video": False,
                "output_path": "./output"
            },
            "video_source": {
                "test_video": "./data/test_videos/sample.mp4",
                "rtsp": {
                    "main_camera": {}
                }
            },
            "model": {
                "type": "yolov5",
                "model_path": "./models/yolov5s.pt",
                "confidence_threshold": 0.5,
                "classes": [2, 5, 7],
                "device": "cpu"
            },
            "detection": {
                "line_crossing": {
                    "enabled": True,
                    "line_position": [[400, 600], [1200, 600]],
                    "direction": "up"
                },
                "region_of_interest": {
                    "enabled": False,
                    "points": [[100, 100], [1500, 100], [1500, 900], [100, 900]]
                }
            },
            "logging": {
                "enabled": True,
                "log_level": "INFO",
                "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "log_file": "./logs/vehicle_counts/vehicle_counts.log"
            },
            "api": {
                "enabled": False,
                "endpoint": "",
                "send_interval": 60,
                "retry_attempts": 3,
                "timeout": 10
            },
            "gui": {
                "enabled": False,
                "theme": "dark",
                "window_size": [1280, 720],
                "fullscreen": False
            }
        }