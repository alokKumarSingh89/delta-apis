import threading

from fastapi import FastAPI

from src.routers.algo.avg_option_selling import loopConfig, run_algo

app = FastAPI()
running = False
thread = None


@app.on_event("startup")
def start_trading():
    global running, thread
    if not running:
        running = True
        thread = threading.Thread(target=run_algo)
        thread.start()
        print("Running Thread")


@app.on_event("shutdown")
def stop_trading():
    global running, thread
    running = False
    loopConfig["isRunning"] = False
    if thread:
        thread.join()


@app.get("/")
def home_page():
    return {"message": "Hello ALok!"}
