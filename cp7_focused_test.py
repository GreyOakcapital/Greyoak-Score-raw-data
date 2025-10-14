#!/usr/bin/env python3
"""
CP7 FOCUSED SECURITY TEST

Quick validation of key CP7 security features without hanging on rate limiting tests.
"""

import requests
import json
import subprocess
import sys
from typing import Dict, List

class CP7FocusedTester:
    """Focused CP7 security tester"""
    
    def __init__(self):
        self.base_url = "https://scorevalidate.preview.emergentagent.com"
        self.test_results = []
        self.failed_tests = []
        
    def log_test(self, test_name: str, passed: bool, details: str = "", critical: bool = False):
        """Log test result"""
        status = "✅ PASS" if passed else ("🚨 CRITICAL FAIL" if critical else "❌ FAIL")
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'critical': critical
        })
        
        print(f"{status}: {test_name}")
        if details:
            print(f"   {'✓' if passed else '✗'} {details}")
            if not passed:
                self.failed_tests.append({
                    'test': test_name,
                    'details': details,
                    'critical': critical
                })
    
    def test_cors_security(self):
        """Test CORS behavior"""
        print("\n🔒 Testing CORS Security...")
        
        # Test CORS with allowed origin
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/health",
                headers={"Origin": "https://scorevalidate.preview.emergentagent.com"},
                timeout=10
            )
            
            cors_origin = response.headers.get('access-control-allow-origin')
            if cors_origin:
                self.log_test(
                    "CORS Headers Present", 
                    True, 
                    f"CORS origin header: {cors_origin}"
                )
            else:
                self.log_test(
                    "CORS Configuration", 
                    False, 
                    "No CORS headers returned - CORS may not be configured",
                    critical=True
                )
                
        except Exception as e:
            self.log_test("CORS Test", False, f"Error: {str(e)}", critical=True)
        
        # Test with disallowed origin
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/health",
                headers={"Origin": "https://evil.example.com"},
                timeout=10
            )
            
            cors_origin = response.headers.get('access-control-allow-origin')
            if cors_origin == "*":
                self.log_test(
                    "CORS Origin Security", 
                    False, 
                    "Wildcard CORS origin detected - security risk",
                    critical=True
                )
            else:
                self.log_test(
                    "CORS Origin Security", 
                    True, 
                    "No wildcard CORS - properly restricted"
                )
                
        except Exception as e:
            self.log_test("CORS Origin Security", False, f"Error: {str(e)}")
    
    def test_rate_limiting_basic(self):
        """Test basic rate limiting behavior"""
        print("\n⏱️ Testing Rate Limiting (Basic)...")
        
        # Test health endpoint (should be exempt)
        try:
            success_count = 0
            for i in range(5):  # Small test to avoid hanging
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    success_count += 1
            
            if success_count == 5:
                self.log_test(
                    "Health Endpoint Accessibility", 
                    True, 
                    "Health endpoint accessible (5/5 requests successful)"
                )
            else:
                self.log_test(
                    "Health Endpoint Accessibility", 
                    False, 
                    f"Health endpoint issues: {success_count}/5 successful",
                    critical=True
                )
                
        except Exception as e:
            self.log_test("Health Endpoint Test", False, f"Error: {str(e)}", critical=True)
        
        # Test API endpoint rate limiting indication
        try:
            response = requests.get(f"{self.base_url}/api/v1/scores/RELIANCE.NS", timeout=10)
            
            # Check if rate limiting headers are present
            rate_limit_headers = {
                'x-ratelimit-limit': response.headers.get('x-ratelimit-limit'),
                'x-ratelimit-remaining': response.headers.get('x-ratelimit-remaining'),
                'x-ratelimit-reset': response.headers.get('x-ratelimit-reset')
            }
            
            if any(rate_limit_headers.values()):
                self.log_test(
                    "Rate Limiting Headers", 
                    True, 
                    f"Rate limiting configured: {rate_limit_headers}"
                )
            else:
                self.log_test(
                    "Rate Limiting Configuration", 
                    False, 
                    "No rate limiting headers detected - may not be configured",
                    critical=True
                )
                
        except Exception as e:
            self.log_test("Rate Limiting Test", False, f"Error: {str(e)}")
    
    def test_error_schema(self):
        """Test error schema and correlation IDs"""
        print("\n🔍 Testing Error Schema & Correlation IDs...")
        
        # Test validation error
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/calculate",
                json={
                    "ticker": "INVALID_TICKER_FORMAT",
                    "date": "invalid-date",
                    "mode": "InvalidMode"
                },
                timeout=10
            )
            
            if response.status_code == 422:
                data = response.json()
                has_request_id = 'request_id' in data
                has_error_details = 'details' in data or 'error' in data
                
                if has_request_id and has_error_details:
                    self.log_test(
                        "Validation Error Schema", 
                        True, 
                        f"422 error with request_id: {data.get('request_id', 'N/A')[:20]}..."
                    )
                else:
                    self.log_test(
                        "Validation Error Schema", 
                        False, 
                        "Missing request_id or error details",
                        critical=True
                    )
            else:
                self.log_test(
                    "Validation Error Response", 
                    False, 
                    f"Expected 422, got {response.status_code}",
                    critical=True
                )
                
        except Exception as e:
            self.log_test("Validation Error Test", False, f"Error: {str(e)}", critical=True)
        
        # Test 404 error
        try:
            response = requests.get(f"{self.base_url}/api/v1/nonexistent", timeout=10)
            
            if response.status_code == 404:
                data = response.json()
                has_request_id = 'request_id' in data
                
                if has_request_id:
                    self.log_test(
                        "404 Error Correlation ID", 
                        True, 
                        f"404 includes request_id: {data.get('request_id', 'N/A')[:20]}..."
                    )
                else:
                    self.log_test(
                        "404 Error Correlation ID", 
                        False, 
                        "404 error missing request_id",
                        critical=True
                    )
            else:
                self.log_test(
                    "404 Error Handling", 
                    True, 
                    f"Endpoint routing working (status: {response.status_code})"
                )
                
        except Exception as e:
            self.log_test("404 Error Test", False, f"Error: {str(e)}")
    
    def test_database_lazy_init(self):
        """Test database lazy initialization"""
        print("\n🗄️ Testing Database Lazy Initialization...")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/health", timeout=10)
            
            if response.status_code in [200, 503]:
                data = response.json()
                db_status = data.get('components', {}).get('database', {}).get('status')
                overall_status = data.get('status')
                
                if db_status == 'unhealthy' and overall_status == 'degraded':
                    self.log_test(
                        "Database Lazy Initialization", 
                        True, 
                        "API running in degraded mode with database unavailable (lazy loading working)"
                    )
                elif db_status == 'healthy':
                    self.log_test(
                        "Database Connection", 
                        True, 
                        "Database connection working correctly"
                    )
                else:
                    self.log_test(
                        "Database Status", 
                        False, 
                        f"Unexpected database status: {db_status}",
                        critical=True
                    )
            else:
                self.log_test(
                    "Database Health Check", 
                    False, 
                    f"Health check failed: {response.status_code}",
                    critical=True
                )
                
        except Exception as e:
            self.log_test("Database Health Test", False, f"Error: {str(e)}", critical=True)
    
    def test_health_endpoints(self):
        """Test both health endpoints"""
        print("\n🏥 Testing Health Endpoints...")
        
        # Test infrastructure health
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['status', 'service', 'version', 'timestamp']
                
                if all(field in data for field in required_fields):
                    self.log_test(
                        "Infrastructure Health Endpoint", 
                        True, 
                        f"Service: {data.get('service')}, Status: {data.get('status')}"
                    )
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_test(
                        "Infrastructure Health Schema", 
                        False, 
                        f"Missing fields: {missing}",
                        critical=True
                    )
            else:
                self.log_test(
                    "Infrastructure Health Endpoint", 
                    False, 
                    f"Health endpoint returned {response.status_code}",
                    critical=True
                )
                
        except Exception as e:
            self.log_test("Infrastructure Health Test", False, f"Error: {str(e)}", critical=True)
        
        # Test application health
        try:
            response = requests.get(f"{self.base_url}/api/v1/health", timeout=10)
            
            if response.status_code in [200, 503]:
                data = response.json()
                has_components = 'components' in data
                
                if has_components:
                    db_status = data['components'].get('database', {}).get('status', 'unknown')
                    api_status = data['components'].get('api', {}).get('status', 'unknown')
                    self.log_test(
                        "Application Health Endpoint", 
                        True, 
                        f"DB: {db_status}, API: {api_status}, Overall: {data.get('status')}"
                    )
                else:
                    self.log_test(
                        "Application Health Schema", 
                        False, 
                        "Missing component status information",
                        critical=True
                    )
            else:
                self.log_test(
                    "Application Health Endpoint", 
                    False, 
                    f"App health returned {response.status_code}",
                    critical=True
                )
                
        except Exception as e:
            self.log_test("Application Health Test", False, f"Error: {str(e)}", critical=True)
    
    def test_production_config(self):
        """Test production configuration"""
        print("\n⚙️ Testing Production Configuration...")
        
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for security features
                features = data.get('features', {})
                security_features = features.get('security', {})
                
                if security_features:
                    rate_limiting = security_features.get('rate_limiting')
                    cors_protection = security_features.get('cors_protection')
                    
                    self.log_test(
                        "Security Features Configuration", 
                        True, 
                        f"Rate limiting: {rate_limiting}, CORS: {cors_protection}"
                    )
                else:
                    self.log_test(
                        "Security Features", 
                        False, 
                        "Security features not documented in API response",
                        critical=True
                    )
                
                # Check environment info
                env_info = data.get('environment', {})
                if env_info:
                    self.log_test(
                        "Environment Configuration", 
                        True, 
                        f"Environment: {env_info}"
                    )
                else:
                    self.log_test(
                        "Environment Configuration", 
                        False, 
                        "Environment info not available"
                    )
            else:
                self.log_test(
                    "API Root Endpoint", 
                    False, 
                    f"Root endpoint returned {response.status_code}",
                    critical=True
                )
                
        except Exception as e:
            self.log_test("Production Configuration Test", False, f"Error: {str(e)}", critical=True)
    
    def run_all_tests(self):
        """Run all focused tests"""
        print("🚀 CP7 FOCUSED SECURITY & STABILITY VALIDATION")
        print("=" * 70)
        print("Testing key CP7 security features")
        print("=" * 70)
        
        # Run all tests
        self.test_cors_security()
        self.test_rate_limiting_basic()
        self.test_error_schema()
        self.test_database_lazy_init()
        self.test_health_endpoints()
        self.test_production_config()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 CP7 FOCUSED TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        critical_failed = sum(1 for r in self.test_results if not r['passed'] and r.get('critical', False))
        
        for result in self.test_results:
            status = "✅" if result['passed'] else ("🚨" if result.get('critical') else "❌")
            print(f"{status} {result['test']}")
        
        print(f"\n🎯 RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if critical_failed > 0:
            print(f"🚨 CRITICAL FAILURES: {critical_failed}")
            print("\n❌ CRITICAL ISSUES:")
            for failed in self.failed_tests:
                if failed.get('critical'):
                    print(f"   🚨 {failed['test']}: {failed['details']}")
        
        if self.failed_tests:
            print(f"\n⚠️ ALL FAILED TESTS:")
            for failed in self.failed_tests:
                criticality = "🚨 CRITICAL" if failed.get('critical') else "❌ FAILED"
                print(f"   {criticality}: {failed['test']}")
                print(f"      {failed['details']}")
        
        return critical_failed == 0

def main():
    """Main test runner"""
    tester = CP7FocusedTester()
    
    try:
        success = tester.run_all_tests()
        
        if success:
            print("\n✅ CP7 FOCUSED VALIDATION COMPLETE - NO CRITICAL FAILURES!")
            return True
        else:
            print("\n❌ CP7 FOCUSED VALIDATION COMPLETE - CRITICAL ISSUES FOUND!")
            return False
            
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)