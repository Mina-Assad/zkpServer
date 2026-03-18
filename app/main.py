from fastapi import FastAPI, HTTPException, Request, Form
from pydantic import BaseModel
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

KEY_LENGTH = 4  # Shorter for demo; use 9+ in real use

def tokenize(key1: int, key2: int) -> int:
    l1 = [int(d) for d in str(key1)]
    l2 = [int(d) for d in str(key2)]
    if len(l1) != len(l2):
        raise ValueError("Keys must be the same length.")
    result = []
    for i in l1:
        s = 0
        p1 = 0
        p2 = i % len(l2)
        head = -1
        arr = {0: [], 1: []}
        while head not in arr[s]:
            arr[s].append(head)
            if s == 0:
                if head != -1:
                    p2 = (p2 + head) % len(l2)
                s = (s + 1) % 2
                head = l2[p2]
            else:
                p1 = (p1 + head) % len(l2)
                s = (s + 1) % 2
                head = l1[p1]
        result.append(arr[(s + 1) % 2][-1])
    return int(''.join(map(str, result)))

class ZKUser:
    def __init__(self, name, key1):
        self.name = name
        self.key1 = key1
        self.key2 = None

    def get_challenge_key(self):
        self.key2 = random.randint(10**(KEY_LENGTH - 1), 10**KEY_LENGTH - 1)
        return self.key2

    def verify(self, token):
        proof = tokenize(self.key1, self.key2)
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
    token: int

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
    return {"username": data.username, "key2": key2}

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
async def calculate_tokenized(request: Request, key1: str = Form(...), key2: str = Form(...)):
    try:
        k1 = int(key1)
        k2 = int(key2)
        token = tokenize(k1, k2)
    except ValueError as e:
        return {"error": str(e)}    
    return templates.TemplateResponse("tokenized.html", {"request": request, "result": token})




