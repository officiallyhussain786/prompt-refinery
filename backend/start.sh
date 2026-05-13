#!/bin/bash
pip install -r requirements.txt
uvicorn app.api.main:app --host 0.0.0.0 --port $PORT
