"""Vertex AI Vector Search configuration.

These are resource identifiers, not secrets. Access is controlled by IAM credentials.
"""

import os

VERTEX_AI_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "medanki-481307")
VERTEX_AI_LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")

TAXONOMY_INDEX_ID = "projects/767583014352/locations/us-central1/indexes/3263361506355445760"
TAXONOMY_ENDPOINT_ID = "projects/767583014352/locations/us-central1/indexEndpoints/7866928730923335680"
TAXONOMY_DEPLOYED_INDEX_ID = "taxonomy_deployed"

TAXONOMY_ENDPOINT_DOMAIN = "710483493.us-central1-767583014352.vdb.vertexai.goog"

TRAINING_BUCKET = os.getenv("MEDANKI_TRAINING_BUCKET", "medanki-training")
TRAINING_DATA_PREFIX = "training_data/"
MODELS_PREFIX = "models/"
FEEDBACK_DATA_PREFIX = "feedback/"
