FROM python:3.11-slim

WORKDIR /app

# 複製依賴清單並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼
COPY . .

# 暴露健康檢查端口
EXPOSE 8080

# 啟動 Bot
CMD ["python", "main.py"]
