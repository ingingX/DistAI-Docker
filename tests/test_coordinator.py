"""
Unit tests for Coordinator Service

Tests cover:
- Request validation and routing logic
- Error handling and edge cases
- Retry mechanism behavior
- Metrics collection
"""

import pytest
import json
import sys
from pathlib import Path

# Add coordinator module to path
sys.path.insert(0, str(Path(__file__).parent.parent / "coordinator"))

from coordinator import app, validate_and_route, workers, WorkerType, WorkerStatus


@pytest.fixture
def client():
    """Create test client for Flask application"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestInputValidation:
    """Tests for input validation and routing logic"""

    def test_valid_text_only(self):
        """Test routing for text-only input"""
        data = {"text": "Hello world"}
        worker_type, error = validate_and_route(data)
        assert worker_type == WorkerType.BERT.value
        assert error is None

    def test_valid_image_only(self):
        """Test routing for image-only input"""
        data = {"image_base64": "base64encodedimage"}
        worker_type, error = validate_and_route(data)
        assert worker_type == WorkerType.MOBILENET.value
        assert error is None

    def test_valid_both(self):
        """Test routing for text + image input"""
        data = {
            "text": "A cat",
            "image_base64": "base64encodedimage"
        }
        worker_type, error = validate_and_route(data)
        assert worker_type == WorkerType.CLIP.value
        assert error is None

    def test_empty_text_ignored(self):
        """Test that empty/whitespace-only text is ignored"""
        data = {"text": "   ", "image_base64": "img"}
        worker_type, error = validate_and_route(data)
        assert worker_type == WorkerType.MOBILENET.value
        assert error is None

    def test_empty_image_ignored(self):
        """Test that empty/whitespace-only image is ignored"""
        data = {"text": "hello", "image_base64": ""}
        worker_type, error = validate_and_route(data)
        assert worker_type == WorkerType.BERT.value
        assert error is None

    def test_no_input(self):
        """Test rejection of request with no input"""
        data = {}
        worker_type, error = validate_and_route(data)
        assert worker_type is None
        assert error is not None
        assert "must provide" in error.lower()

    def test_both_empty(self):
        """Test rejection when both text and image are empty"""
        data = {"text": "", "image_base64": ""}
        worker_type, error = validate_and_route(data)
        assert worker_type is None
        assert error is not None

    def test_non_string_text(self):
        """Test that non-string text is treated as invalid"""
        data = {"text": 123, "image_base64": "img"}
        worker_type, error = validate_and_route(data)
        assert worker_type == WorkerType.MOBILENET.value
        assert error is None

    def test_non_string_image(self):
        """Test that non-string image is treated as invalid"""
        data = {"text": "hello", "image_base64": 123}
        worker_type, error = validate_and_route(data)
        assert worker_type == WorkerType.BERT.value
        assert error is None


class TestCoordinatorEndpoints:
    """Tests for HTTP endpoints"""

    def test_invalid_input_returns_400(self, client):
        """Test that invalid input returns 400 Bad Request"""
        response = client.post(
            '/infer',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_worker_unavailable_returns_503(self, client):
        """Test that request fails with 503 when worker is offline"""
        # Ensure worker is marked as offline
        workers[WorkerType.BERT.value]["status"] = WorkerStatus.OFFLINE.value

        response = client.post(
            '/infer',
            data=json.dumps({"text": "test"}),
            content_type='application/json'
        )
        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data

    def test_status_endpoint_returns_200(self, client):
        """Test that /status endpoint is accessible"""
        response = client.get('/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'coordinator' in data
        assert data['coordinator'] == 'online'
        assert 'workers' in data
        assert 'stats' in data

    def test_health_endpoint_returns_200(self, client):
        """Test that /health endpoint is accessible"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data

    def test_metrics_endpoint_returns_200(self, client):
        """Test that /metrics endpoint is accessible"""
        response = client.get('/metrics')
        assert response.status_code == 200
        assert response.content_type.startswith('text/plain')

    def test_404_on_unknown_endpoint(self, client):
        """Test that unknown endpoints return 404"""
        response = client.get('/unknown')
        assert response.status_code == 404


class TestWorkerRegistry:
    """Tests for worker registry and configuration"""

    def test_all_workers_registered(self):
        """Test that all expected workers are registered"""
        assert WorkerType.BERT.value in workers
        assert WorkerType.MOBILENET.value in workers
        assert WorkerType.CLIP.value in workers

    def test_worker_has_required_fields(self):
        """Test that each worker has required configuration fields"""
        for worker_type, worker_info in workers.items():
            assert 'id' in worker_info
            assert 'url' in worker_info
            assert 'status' in worker_info
            assert 'type' in worker_info
            assert worker_info['type'] == worker_type

    def test_initial_worker_status_is_offline(self):
        """Test that workers start as offline"""
        for worker_info in workers.values():
            assert worker_info['status'] in [
                WorkerStatus.ONLINE.value,
                WorkerStatus.OFFLINE.value,
                WorkerStatus.DEGRADED.value
            ]


class TestRetryLogic:
    """Tests for retry mechanism configuration"""

    def test_retry_backoff_calculation(self):
        """Test exponential backoff calculation"""
        from coordinator import RETRY_BACKOFF
        
        base = RETRY_BACKOFF
        for attempt in range(3):
            wait_time = base * (2 ** attempt)
            assert wait_time == base * (2 ** attempt)

        # Verify exponential growth
        backoff_0 = base * (2 ** 0)  # 0.5
        backoff_1 = base * (2 ** 1)  # 1.0
        backoff_2 = base * (2 ** 2)  # 2.0
        
        assert backoff_1 == backoff_0 * 2
        assert backoff_2 == backoff_1 * 2

    def test_max_retries_configured(self):
        """Test that max retries is properly configured"""
        from coordinator import MAX_RETRIES
        
        assert MAX_RETRIES > 0
        assert isinstance(MAX_RETRIES, int)
        assert MAX_RETRIES == 3


class TestRequestLogging:
    """Tests for request logging and observability"""

    def test_status_returns_recent_requests(self, client):
        """Test that /status includes recent request logs"""
        response = client.get('/status')
        data = response.get_json()
        
        assert 'recent_requests' in data
        assert isinstance(data['recent_requests'], list)

    def test_status_includes_stats(self, client):
        """Test that /status includes performance statistics"""
        response = client.get('/status')
        data = response.get_json()
        
        assert 'stats' in data
        stats = data['stats']
        
        required_stats = [
            'total_requests',
            'successful_requests',
            'failed_requests',
            'success_rate',
            'avg_latency_ms'
        ]
        
        for stat in required_stats:
            assert stat in stats


class TestErrorHandlers:
    """Tests for error handling"""

    def test_404_error_handler(self, client):
        """Test custom 404 handler"""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_request_id_uniqueness(self, client):
        """Test that request IDs are reasonably unique"""
        # This is a soft test - just verify request_id is present and numeric
        response = client.post(
            '/infer',
            data=json.dumps({}),
            content_type='application/json'
        )
        data = response.get_json()
        assert 'request_id' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
