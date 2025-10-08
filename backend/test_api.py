"""
Simple test script for GreyOak Score API endpoints.

This script tests the API without requiring Docker or database connectivity.
It starts the FastAPI server and makes HTTP requests to verify functionality.
"""

import asyncio
import httpx
import uvicorn
import threading
import time
from pathlib import Path
import sys

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from greyoak_score.api.main import app


def start_server():
    """Start the FastAPI server in a separate thread."""
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")


async def test_endpoints():
    """Test API endpoints."""
    base_url = "http://127.0.0.1:8001"
    
    async with httpx.AsyncClient() as client:
        print("Testing GreyOak Score API endpoints...\n")
        
        # Test 1: Root endpoint
        print("1. Testing root endpoint (GET /)...")
        try:
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                print("   ✅ Root endpoint working")
                data = response.json()
                print(f"   Service: {data['service']}")
                print(f"   Version: {data['version']}")
            else:
                print(f"   ❌ Root endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Root endpoint error: {e}")
        
        print()
        
        # Test 2: Simple health check
        print("2. Testing simple health endpoint (GET /health)...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("   ✅ Simple health check working")
                data = response.json()
                print(f"   Status: {data['status']}")
            else:
                print(f"   ❌ Simple health check failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Simple health check error: {e}")
        
        print()
        
        # Test 3: Detailed health check
        print("3. Testing detailed health endpoint (GET /api/v1/health)...")
        try:
            response = await client.get(f"{base_url}/api/v1/health")
            if response.status_code in [200, 503]:  # 503 is acceptable if database is down
                print(f"   ✅ Detailed health check working (status: {response.status_code})")
                data = response.json()
                print(f"   Overall status: {data.get('status', 'unknown')}")
                if 'components' in data:
                    db_status = data['components'].get('database', {}).get('status', 'unknown')
                    print(f"   Database status: {db_status}")
            else:
                print(f"   ❌ Detailed health check failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Detailed health check error: {e}")
        
        print()
        
        # Test 4: Calculate score endpoint
        print("4. Testing calculate score endpoint (POST /api/v1/calculate)...")
        try:
            payload = {
                "ticker": "RELIANCE.NS",
                "date": "2024-10-08",
                "mode": "Investor"
            }
            response = await client.post(f"{base_url}/api/v1/calculate", json=payload)
            if response.status_code == 200:
                print("   ✅ Calculate score working")
                data = response.json()
                print(f"   Score: {data['score']:.2f}")
                print(f"   Band: {data['band']}")
                print(f"   Risk Penalty: {data['risk_penalty']:.1f}")
            else:
                print(f"   ❌ Calculate score failed: {response.status_code}")
                if response.status_code == 422:
                    print(f"   Validation error: {response.json()}")
        except Exception as e:
            print(f"   ❌ Calculate score error: {e}")
        
        print()
        
        # Test 5: Get scores endpoint (will fail without database data, but should validate)
        print("5. Testing get scores endpoint (GET /api/v1/scores/RELIANCE.NS)...")
        try:
            response = await client.get(f"{base_url}/api/v1/scores/RELIANCE.NS")
            if response.status_code == 404:
                print("   ✅ Get scores endpoint working (404 expected without data)")
            elif response.status_code == 200:
                print("   ✅ Get scores endpoint working (data found)")
                data = response.json()
                print(f"   Found {len(data)} scores")
            elif response.status_code == 500:
                print("   ⚠️  Get scores endpoint has database connectivity issue (expected)")
            else:
                print(f"   ❌ Get scores failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Get scores error: {e}")
        
        print()
        
        # Test 6: Get by band endpoint
        print("6. Testing get by band endpoint (GET /api/v1/scores/band/Buy)...")
        try:
            params = {"date": "2024-10-08", "mode": "Investor"}
            response = await client.get(f"{base_url}/api/v1/scores/band/Buy", params=params)
            if response.status_code == 404:
                print("   ✅ Get by band endpoint working (404 expected without data)")
            elif response.status_code == 200:
                print("   ✅ Get by band endpoint working (data found)")
            elif response.status_code == 500:
                print("   ⚠️  Get by band endpoint has database connectivity issue (expected)")
            else:
                print(f"   ❌ Get by band failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Get by band error: {e}")
        
        print()
        
        # Test 7: OpenAPI docs
        print("7. Testing OpenAPI documentation endpoints...")
        try:
            docs_response = await client.get(f"{base_url}/docs")
            openapi_response = await client.get(f"{base_url}/openapi.json")
            
            if docs_response.status_code == 200 and openapi_response.status_code == 200:
                print("   ✅ OpenAPI docs accessible")
                openapi_data = openapi_response.json()
                print(f"   API title: {openapi_data.get('info', {}).get('title', 'Unknown')}")
                paths_count = len(openapi_data.get('paths', {}))
                print(f"   Endpoints defined: {paths_count}")
            else:
                print("   ❌ OpenAPI docs failed")
        except Exception as e:
            print(f"   ❌ OpenAPI docs error: {e}")
        
        print("\n" + "="*50)
        print("API Testing Complete!")
        print("="*50)


async def main():
    """Main test function."""
    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    print("Starting FastAPI server...")
    time.sleep(2)
    
    # Run tests
    await test_endpoints()


if __name__ == "__main__":
    asyncio.run(main())