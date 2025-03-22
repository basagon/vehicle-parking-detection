#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vehicle Detection System: Main Module
โมดูลหลักสำหรับการเริ่มต้นระบบตรวจจับรถยนต์
"""

import os
import sys
import time
import signal
import argparse
from loguru import logger

# เพิ่ม path ของโปรเจค
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules
from src.config_manager import ConfigManager
from src.video_processor import VideoProcessor
from src.vehicle_detector import VehicleDetector
from src.line_counter import LineCounter
from src.data_logger import DataLogger
from src.api_client import ApiClient

# ถ้าเปิดใช้งาน GUI
from src.gui import create_gui_app

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """จัดการกับสัญญาณจากระบบปฏิบัติการ (Ctrl+C)"""
    global running
    logger.info("Received signal to shutdown...")
    running = False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Vehicle Detection System")
    parser.add_argument("--config", type=str, default="config.yaml", 
                        help="Path to configuration file")
    parser.add_argument("--gui", action="store_true", 
                        help="Start with GUI for configuration")
    parser.add_argument("--test", action="store_true", 
                        help="Run in test mode (override config)")
    return parser.parse_args()

def setup_logger(config):
    """Setup logger based on configuration"""
    log_level = config["logging"]["log_level"]
    log_file = config["logging"]["log_file"]
    log_format = config["logging"]["log_format"]
    
    # Remove default logger
    logger.remove()
    
    # Add stderr logger
    logger.add(sys.stderr, level=log_level, format=log_format)
    
    # Add file logger
    if config["logging"]["enabled"]:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logger.add(log_file, level=log_level, format=log_format, 
                  rotation="1 day", retention="30 days")
    
    logger.info("Logger configured successfully")

def main():
    """Main function to start the vehicle detection system"""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Load configuration
    config_manager = ConfigManager(args.config)
    config = config_manager.get_config()
    
    # Override config with command line arguments if provided
    if args.test:
        config["general"]["test_mode"] = True
    
    # Setup logger
    setup_logger(config)
    
    logger.info(f"Starting {config['general']['app_name']} v{config['general']['version']}")
    logger.info(f"Running in {'test' if config['general']['test_mode'] else 'production'} mode")
    
    # Start GUI if needed
    if args.gui or config["gui"]["enabled"]:
        logger.info("Starting GUI...")
        app = create_gui_app(config_manager)
        return app.exec()
    
    # Initialize components
    try:
        # Create video processor
        video_processor = VideoProcessor(config)
        
        # Create vehicle detector
        vehicle_detector = VehicleDetector(config)
        
        # Create line counter
        line_counter = LineCounter(config)
        
        # Create data logger
        data_logger = DataLogger(config)
        
        # Create API client if enabled
        api_client = ApiClient(config) if config["api"]["enabled"] else None
        
        # Main processing loop
        logger.info("Starting main processing loop...")
        
        # Set up video source
        if config["general"]["test_mode"]:
            video_source = config["video_source"]["test_video"]
            logger.info(f"Using test video: {video_source}")
        else:
            # Build RTSP URL from environment variables
            rtsp_url = video_processor.build_rtsp_url()
            video_source = rtsp_url
            logger.info(f"Connecting to RTSP stream...")
        
        # Open video source
        if not video_processor.open_video_source(video_source):
            logger.error(f"Failed to open video source: {video_source}")
            return 1
        
        # Process frames
        frame_count = 0
        start_time = time.time()
        last_api_send_time = start_time
        
        while running:
            # Read frame
            ret, frame = video_processor.read_frame()
            if not ret:
                logger.warning("Failed to read frame, retrying...")
                # Wait a bit before retrying
                time.sleep(1)
                # Try to reopen the video source
                video_processor.open_video_source(video_source)
                continue
            
            # Detect vehicles
            detections = vehicle_detector.detect(frame)
            
            # Count vehicles crossing the line
            counts = line_counter.update(frame, detections)
            
            # Log data if counts changed
            if counts["new_counts"] > 0:
                logger.info(f"Detected {counts['new_counts']} new vehicle(s) crossing the line")
                data_logger.log_vehicle_count(counts)
                
                # Send data to API if enabled
                if api_client and time.time() - last_api_send_time >= config["api"]["send_interval"]:
                    api_client.send_data(data_logger.get_recent_counts())
                    last_api_send_time = time.time()
            
            # Display result
            if config["general"]["display_output"]:
                video_processor.display_frame(frame)
                
                # Check for exit key (q)
                if video_processor.check_exit_key():
                    logger.info("Exit key pressed, stopping...")
                    break
            
            # Save output video if enabled
            if config["general"]["save_output_video"]:
                video_processor.write_frame(frame)
            
            # Calculate FPS and log every 100 frames
            frame_count += 1
            if frame_count % 100 == 0:
                elapsed_time = time.time() - start_time
                fps = frame_count / elapsed_time
                logger.debug(f"Processing at {fps:.2f} FPS")
        
        # Cleanup
        logger.info("Cleaning up resources...")
        video_processor.release()
        
        # Send final data to API if enabled
        if api_client:
            api_client.send_data(data_logger.get_recent_counts())
        
        logger.info("Vehicle detection system stopped successfully")
        return 0
    
    except Exception as e:
        logger.exception(f"Error in main loop: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())