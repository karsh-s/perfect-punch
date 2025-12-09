"""Celery app placeholder for background tasks like video segmentation or batch inference.

This file provides a basic Celery application configuration that can be expanded
when Redis/Broker details are available.
"""
from celery import Celery

# Example broker URL; override with environment variable in production
BROKER_URL = "redis://localhost:6379/0"
backend = Celery("perfectpunch_tasks", broker=BROKER_URL)


@backend.task
def dummy_task(x):
    return x
