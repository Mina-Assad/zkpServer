from fastapi import FastAPI, HTTPException, Request, Form
from pydantic import BaseModel
import math
import random
from datetime import datetime, timezone
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://zkpserver-uejf.onrender.com/"],   # for dev, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="app/templates")

KEY_LENGTH = 4  # Shorter for demo; use 17+ in real use

def time_seed(offset: int = 0) -> int:
    now_utc = datetime.now(timezone.utc)
    return now_utc.day * 100 + now_utc.hour + offset

def round_sig(x, sig=3):
    if x == 0:
        return 0
    order = int(math.floor(math.log10(abs(x))))
    decimals = sig - order - 1
    return round(x, decimals)

def tokenize(key1: int, key2: int, seed: int) -> float:
    l1 = [int(d) for d in str(key1)]
    l2 = [int(d) for d in str(key2)]
    if len(l1) != len(l2):
        raise ValueError("Keys must be the same length.")
    result = 0
    for i in range(len(l1)):
        try:
            tval = l1[i] * (seed ** l2[i])
            if tval == 0:
                val = 0
            else:
                val = 10 ** ((math.log(tval, 10)) % 1)
            temp = math.sin(val) if i % 2 == 0 else math.tan(val)
            result += temp
        except OverflowError:
            result += 0
    return round_sig(result, KEY_LENGTH)

class ZKUser:
    def __init__(self, name, key1):
        self.name = name
        self.key1 = key1
        self.key2 = None
        self.stime = None
        self.locked = False

    def get_challenge_key(self):
        self.key2 = random.randint(10**(KEY_LENGTH - 1), 10**KEY_LENGTH - 1)
        self.stime = time_seed()
        return self.key2

    def verify(self, token):
        if self.locked and self.stime == time_seed():
            return False
        self.locked = True
        proof = tokenize(self.key1, self.key2, time_seed())
        print("The Real Token Value = ", proof)
        return proof == token

class ZKServer:
    def __init__(self):
        self.users = {}

    def register_user(self, username):
        if username in self.users:
            return self.users[username].key1
        key1 = random.randint(10**(KEY_LENGTH - 1), 10**KEY_LENGTH - 1)
        self.users[username] = ZKUser(username, key1)
        return key1

    def issue_challenge(self, username):
        if username not in self.users:
            return None
        return self.users[username].get_challenge_key()

    def verify_token(self, username, token):
        if username not in self.users:
            return False
        user = self.users[username]
        return user.verify(token)

# Initialize server
zk_server = ZKServer()

# === API Models ===
class RegisterRequest(BaseModel):
    username: str

class ChallengeRequest(BaseModel):
    username: str

class VerifyRequest(BaseModel):
    username: str
    token: float

@app.get("/")
def read_root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "templates/index.html"))

@app.post("/register")
def register_user(data: RegisterRequest):
    key1 = zk_server.register_user(data.username)
    return {"username": data.username, "key1": key1}

@app.post("/challenge")
def issue_challenge(data: ChallengeRequest):
    key2 = zk_server.issue_challenge(data.username)
    if key2 is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": data.username, "key2": key2, "seed": time_seed()}

@app.post("/verify")
def verify_token(data: VerifyRequest):
    success = zk_server.verify_token(data.username, data.token)
    if not success:
        raise HTTPException(status_code=401, detail="Authentication failed")
    return {"status": "Authentication successful"}

# --- New Pages ---
@app.get("/explain", response_class=HTMLResponse)
async def explain_page(request: Request):
    #return FileResponse(os.path.join(os.path.dirname(__file__), "templates/explain.html"))
    return templates.TemplateResponse("explain.html", {"request": request})

@app.get("/tokenized", response_class=HTMLResponse)
async def tokenized_page(request: Request):
    #return FileResponse(os.path.join(os.path.dirname(__file__), "templates/tokenized.html"))
    return templates.TemplateResponse("tokenized.html", {"request": request})

@app.post("/calculate-tokenized")
async def calculate_tokenized(request: Request, key1: str = Form(...), key2: str = Form(...), seed: str = Form(...)):
    try:
        k1 = int(key1)
        k2 = int(key2)
        s = int(seed)
        token = tokenize(k1, k2, s)
    except ValueError as e:
        return {"error": str(e)}    
    return templates.TemplateResponse("tokenized.html", {"request": request, "result": token})




