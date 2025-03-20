# ใช้ Python 3.9 เป็นฐาน - มีความเข้ากันได้ดีกับไลบรารีส่วนใหญ่
FROM python:3.9-slim

# ตั้งค่า working directory
WORKDIR /app

# ตั้งค่า environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# ติดตั้ง dependencies สำหรับ OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# คัดลอกไฟล์ requirements ก่อนเพื่อใช้ประโยชน์จาก Docker cache
COPY requirements.txt .

# ติดตั้ง Python packages
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดทั้งหมดไปยัง container
COPY . .

# สร้างไดเรกทอรีที่จำเป็น
RUN mkdir -p logs/vehicle_counts logs/system output

# ตั้งค่า permissions
RUN chmod -R 755 /app

# สร้าง volume สำหรับ logs และ output
VOLUME ["/app/logs", "/app/output", "/app/data"]

# Expose port สำหรับ web interface (ถ้ามี)
EXPOSE 8080

# รัน application
CMD ["python", "-m", "src.main"]