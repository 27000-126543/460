#!/bin/bash
export PYTHONPATH=/Users/mac/Desktop/6.15项目/460
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
