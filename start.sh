#!/usr/bin/env bash
uvicorn zpk_api:app --host 0.0.0.0 --port $PORT
