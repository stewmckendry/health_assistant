"""
Pre-download cross-encoder model to avoid timeout during evaluation.
"""
import logging
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model_name = "BAAI/bge-reranker-v2-m3"

logger.info(f"Downloading {model_name}...")
logger.info("This may take a few minutes (model is ~1.2GB)")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

logger.info("Download complete!")
logger.info(f"Model cached at: ~/.cache/huggingface/hub/")
