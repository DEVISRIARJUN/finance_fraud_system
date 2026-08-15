import os
import sys
import uvicorn

if __name__ == "__main__":
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    os.chdir(backend_dir)
    sys.path.insert(0, backend_dir)
    
    print("==================================================")
    print("🚀 Starting Sentinel AI Wealth & Fraud Shield...")
    print("👉 Open your browser at: http://127.0.0.1:8000")
    print("==================================================")
    
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
