# car-out-detection-count
# โครงสร้างโปรเจค
│
├── .env                     # ไฟล์สำหรับเก็บข้อมูลที่สำคัญ (รหัสผ่าน, API keys, URLs)
├── config.yaml              # ไฟล์การตั้งค่าหลักของระบบ
├── requirements.txt         # รายการ dependencies
├── docker-compose.yml       # สำหรับการรัน container
├── Dockerfile               # สำหรับการสร้าง image
│
├── src/                     # โค้ดหลักของระบบ
│   ├── main.py              # จุดเริ่มต้นของโปรแกรม
│   ├── config_manager.py    # จัดการการตั้งค่าจาก config.yaml และ .env
│   ├── video_processor.py   # ประมวลผลวิดีโอจาก RTSP และไฟล์วิดีโอ
│   ├── vehicle_detector.py  # โมดูลตรวจจับรถยนต์
│   ├── line_counter.py      # โมดูลสำหรับนับรถยนต์ที่ข้ามเส้น
│   ├── data_logger.py       # บันทึกข้อมูลลงไฟล์ log
│   ├── api_client.py        # ส่งข้อมูลไปยัง API ภายนอก
│   └── gui/                 # โมดูลสำหรับ GUI
│       ├── __init__.py
│       ├── line_setup.py    # สำหรับตั้งค่าเส้นตรวจจับ
│       └── region_setup.py  # สำหรับตั้งค่าพื้นที่ตรวจจับ
│
├── tests/                   # ชุดทดสอบ
│   ├── __init__.py
│   ├── test_video_processor.py
│   ├── test_vehicle_detector.py
│   └── test_line_counter.py
│
├── models/                  # โมเดลที่ผ่านการเทรนแล้ว
│   └── yolov5s.pt           # โมเดล YOLOv5s pre-trained
│
├── data/                    # ข้อมูลสำหรับการทดสอบและ calibration
│   ├── test_videos/
│   │   └── sample.mp4       # วิดีโอตัวอย่างสำหรับทดสอบ
│   └── camera_configs/      # การตั้งค่าเฉพาะของแต่ละกล้อง
│       └── camera1.yaml     # การตั้งค่าสำหรับกล้องตัวที่ 1
│
└── logs/                    # บันทึกการทำงานของระบบ
    ├── vehicle_counts/      # บันทึกการนับรถยนต์
    └── system/              # บันทึกการทำงานของระบบ