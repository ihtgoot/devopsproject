import json
import pytest
from fastapi.testclient import TestClient
from trainer.app import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "up"

def test_train_endpoint_creates_job():
    payload = {"dataset_path": "fake_path", "epochs": 1, "lr": 0.0001}
    response = client.post("/train", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    # Check that status endpoint returns the same job_id and queued status
    job_id = data["job_id"]
    status_resp = client.get(f"/status/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "queued"
    assert status_data["job_id"] == job_id

def test_inference_endpoint_mock(monkeypatch):
    # Mock FastLanguageModel.from_pretrained to avoid heavy model load
    class MockModel:
        def generate(self, **kwargs):
            class Out:
                def __getitem__(self, idx):
                    return b"### Response:\nMocked answer"
            return Out()
    class MockTokenizer:
        def __call__(self, prompt, return_tensors=None):
            return {"input_ids": []}
        def decode(self, *args, **kwargs):
            return "### Response:\nMocked answer"
    def mock_from_pretrained(*args, **kwargs):
        return MockModel(), MockTokenizer()
    monkeypatch.setattr("trainer.app.FastLanguageModel.from_pretrained", mock_from_pretrained)
    payload = {"model_id": "any", "instruction": "test"}
    response = client.post("/inference", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["response"].strip() == "Mocked answer"
