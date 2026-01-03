import uvicorn
from src.web.app import app

if __name__ == "__main__":
    # 启动 Web 服务器 (同时也会触发 lifespan 启动调度器)
    uvicorn.run("src.web.app:app", host="0.0.0.0", port=8000, reload=True)

