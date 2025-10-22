#!/usr/bin/env python3
"""
CP7 QUICK VALIDATION TEST - POST FIXES

Focused validation of the specific CP7 security fixes that were just implemented:
1. CORS Headers Fix (dotenv loading, middleware configuration)
2. Rate Limiting Headers Fix (SlowAPI headers_enabled=True)
3. Error Schema & Correlation IDs (should still work)
4. Health Endpoints (should return JSON, not HTML)

This test validates the critical fixes made to resolve the previously failing CP7 features.
"""

import asyncio
import httpx
import time
import json
from typing import Dict, List, Any

class CP7SecurityTester:
    """Focused CP7 security fixes validator"""
    
    def __init__(self):
        self.base_url = "https://greyoak-score-3.preview.emergentagent.com"
        self.test_origin = "https://greyoak-score-3.preview.emergentagent.com"
        self.test_results = []
        self.failed_tests = []
        
    def log_test(self, test_name: str, passed: bool, details: str = "", critical: bool = False):
        """Log test result with criticality flag"""
        status = "✅ PASS" if passed else "❌ FAIL"
        if critical and not passed:
            status = "🚨 CRITICAL FAIL"
            
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'critical': critical
        })
        
        print(f"{status}: {test_name}")
        if details:
            if passed:
                print(f"   ✓ {details}")
            else:
                print(f"   ✗ {details}")
                if not passed:
                    self.failed_tests.append({
                        'test': test_name,
                        'details': details,
                        'critical': critical
                    })
    
    async def test_cors_preflight_fix(self):
        """Test CORS preflight (OPTIONS) - should now return 200, not 405"""
        print("\n🔒 Testing CORS Preflight Fix...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.options(
                    f"{self.base_url}/api/v1/health",
                    headers={
                        "Origin": self.test_origin,
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Content-Type"
                    }
                )
                
                if response.status_code == 200:
                    self.log_test(
                        "CORS Preflight (OPTIONS)", 
                        True, 
                        f"HTTP 200 - Preflight working correctly",
                        critical=True
                    )
                elif response.status_code == 405:
                    self.log_test(
                        "CORS Preflight (OPTIONS)", 
                        False, 
                        f"HTTP 405 - Preflight still failing (not fixed)",
                        critical=True
                    )
                else:
                    self.log_test(
                        "CORS Preflight (OPTIONS)", 
                        False, 
                        f"HTTP {response.status_code} - Unexpected response",
                        critical=True
                    )
                    
            except Exception as e:
                self.log_test("CORS Preflight (OPTIONS)", False, f"Error: {str(e)}", critical=True)
    
    async def test_cors_headers_fix(self):
        """Test CORS headers in regular requests"""
        print("\n🔒 Testing CORS Headers Fix...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/health",
                    headers={"Origin": self.test_origin}
                )
                
                cors_header = response.headers.get("access-control-allow-origin")
                if cors_header:
                    if cors_header == self.test_origin or cors_header == "*":
                        self.log_test(
                            "CORS Headers Present", 
                            True, 
                            f"Access-Control-Allow-Origin: {cors_header}",
                            critical=True
                        )
                    else:
                        self.log_test(
                            "CORS Headers Present", 
                            False, 
                            f"Wrong origin: {cors_header}",
                            critical=True
                        )
                else:
                    self.log_test(
                        "CORS Headers Present", 
                        False, 
                        "No Access-Control-Allow-Origin header found",
                        critical=True
                    )
                    
            except Exception as e:
                self.log_test("CORS Headers Present", False, f"Error: {str(e)}", critical=True)
    
    async def test_rate_limiting_headers_fix(self):
        """Test rate limiting headers - should now be present with SlowAPI headers_enabled=True"""
        print("\n⏱️ Testing Rate Limiting Headers Fix...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.base_url}/api/v1/scores/RELIANCE.NS")
                
                rate_limit_headers = {
                    'x-ratelimit-limit': response.headers.get('x-ratelimit-limit'),
                    'x-ratelimit-remaining': response.headers.get('x-ratelimit-remaining'),
                    'x-ratelimit-reset': response.headers.get('x-ratelimit-reset')
                }
                
                present_headers = {k: v for k, v in rate_limit_headers.items() if v is not None}
                
                if len(present_headers) >= 2:  # At least limit and remaining
                    self.log_test(
                        "Rate Limiting Headers", 
                        True, 
                        f"Headers present: {present_headers}",
                        critical=True
                    )
                else:
                    self.log_test(
                        "Rate Limiting Headers", 
                        False, 
                        f"Missing headers. Found: {present_headers}",
                        critical=True
                    )
                    
            except Exception as e:
                self.log_test("Rate Limiting Headers", False, f"Error: {str(e)}", critical=True)
    
    async def test_error_schema_correlation_ids(self):
        """Test error schema with correlation IDs - should still work"""
        print("\n🆔 Testing Error Schema & Correlation IDs...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Test validation error (422)
                invalid_payload = {
                    "ticker": "INVALID",
                    "date": "bad-date",
                    "mode": "BadMode"
                }
                response = await client.post(
                    f"{self.base_url}/api/v1/calculate",
                    json=invalid_payload
                )
                
                if response.status_code == 422:
                    try:
                        data = response.json()
                        request_id = data.get("request_id")
                        if request_id and request_id.startswith("req_"):
                            self.log_test(
                                "Error Schema (422)", 
                                True, 
                                f"Validation error with request_id: {request_id}"
                            )
                        else:
                            self.log_test(
                                "Error Schema (422)", 
                                False, 
                                f"Missing or invalid request_id: {request_id}"
                            )
                    except json.JSONDecodeError:
                        self.log_test("Error Schema (422)", False, "Response not valid JSON")
                else:
                    self.log_test("Error Schema (422)", False, f"Expected 422, got {response.status_code}")
                
                # Test 404 error
                response = await client.get(f"{self.base_url}/api/v1/nonexistent")
                if response.status_code == 404:
                    try:
                        data = response.json()
                        request_id = data.get("request_id")
                        if request_id and request_id.startswith("req_"):
                            self.log_test(
                                "Error Schema (404)", 
                                True, 
                                f"404 error with request_id: {request_id}"
                            )
                        else:
                            self.log_test(
                                "Error Schema (404)", 
                                False, 
                                f"Missing or invalid request_id: {request_id}"
                            )
                    except json.JSONDecodeError:
                        self.log_test("Error Schema (404)", False, "Response not valid JSON")
                else:
                    self.log_test("Error Schema (404)", False, f"Expected 404, got {response.status_code}")
                    
            except Exception as e:
                self.log_test("Error Schema & Correlation IDs", False, f"Error: {str(e)}")
    
    async def test_health_endpoints_fix(self):
        """Test health endpoints - should return proper JSON, not HTML"""
        print("\n🏥 Testing Health Endpoints Fix...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Test infrastructure health endpoint
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("status") and data.get("service"):
                            self.log_test(
                                "Infrastructure Health (/health)", 
                                True, 
                                f"Status: {data.get('status')}, Service: {data.get('service')}",
                                critical=True
                            )
                        else:
                            self.log_test(
                                "Infrastructure Health (/health)", 
                                False, 
                                f"Missing required fields in response: {data}",
                                critical=True
                            )
                    except json.JSONDecodeError:
                        # Check if it's HTML (the old problem)
                        content = response.text
                        if "<html" in content.lower():
                            self.log_test(
                                "Infrastructure Health (/health)", 
                                False, 
                                "Returns HTML instead of JSON (routing issue)",
                                critical=True
                            )
                        else:
                            self.log_test(
                                "Infrastructure Health (/health)", 
                                False, 
                                "Response not valid JSON",
                                critical=True
                            )
                else:
                    self.log_test(
                        "Infrastructure Health (/health)", 
                        False, 
                        f"HTTP {response.status_code}",
                        critical=True
                    )
                
                # Test application health endpoint
                response = await client.get(f"{self.base_url}/api/v1/health")
                
                if response.status_code in [200, 503]:  # 503 acceptable if DB down
                    try:
                        data = response.json()
                        overall_status = data.get("status")
                        components = data.get("components", {})
                        if overall_status and components:
                            db_status = components.get("database", {}).get("status", "unknown")
                            api_status = components.get("api", {}).get("status", "unknown")
                            self.log_test(
                                "Application Health (/api/v1/health)", 
                                True, 
                                f"Overall: {overall_status}, DB: {db_status}, API: {api_status}"
                            )
                        else:
                            self.log_test(
                                "Application Health (/api/v1/health)", 
                                False, 
                                f"Missing required fields: {data}"
                            )
                    except json.JSONDecodeError:
                        self.log_test(
                            "Application Health (/api/v1/health)", 
                            False, 
                            "Response not valid JSON"
                        )
                else:
                    self.log_test(
                        "Application Health (/api/v1/health)", 
                        False, 
                        f"HTTP {response.status_code}"
                    )
                    
            except Exception as e:
                self.log_test("Health Endpoints", False, f"Error: {str(e)}")
    
    async def test_root_endpoint_fix(self):
        """Test root endpoint - should return backend JSON, not frontend HTML"""
        print("\n🏠 Testing Root Endpoint Fix...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.base_url}/")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("service") and "GreyOak Score API" in data.get("service", ""):
                            self.log_test(
                                "Root Endpoint (/)", 
                                True, 
                                f"Service: {data.get('service')}, Version: {data.get('version')}"
                            )
                        else:
                            self.log_test(
                                "Root Endpoint (/)", 
                                False, 
                                f"Unexpected JSON response: {data}"
                            )
                    except json.JSONDecodeError:
                        # Check if it's HTML (the old problem)
                        content = response.text
                        if "<html" in content.lower():
                            self.log_test(
                                "Root Endpoint (/)", 
                                False, 
                                "Returns frontend HTML instead of backend JSON (routing issue)"
                            )
                        else:
                            self.log_test(
                                "Root Endpoint (/)", 
                                False, 
                                "Response not valid JSON"
                            )
                else:
                    self.log_test(
                        "Root Endpoint (/)", 
                        False, 
                        f"HTTP {response.status_code}"
                    )
                    
            except Exception as e:
                self.log_test("Root Endpoint (/)", False, f"Error: {str(e)}")
    
    async def run_all_tests(self):
        """Run all CP7 security validation tests"""
        print("🔒 CP7 QUICK VALIDATION TEST - POST FIXES")
        print("=" * 70)
        print("Testing specific fixes made to resolve CP7 security issues:")
        print("• CORS Headers Fix (dotenv loading, middleware config)")
        print("• Rate Limiting Headers Fix (SlowAPI headers_enabled=True)")
        print("• Error Schema & Correlation IDs (should still work)")
        print("• Health Endpoints (should return JSON, not HTML)")
        print("=" * 70)
        print(f"Backend URL: {self.base_url}")
        print(f"Test Origin: {self.test_origin}")
        print()
        
        # Run all test categories in order of priority
        await self.test_cors_preflight_fix()
        await self.test_cors_headers_fix()
        await self.test_rate_limiting_headers_fix()
        await self.test_error_schema_correlation_ids()
        await self.test_health_endpoints_fix()
        await self.test_root_endpoint_fix()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 CP7 SECURITY VALIDATION SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        critical_passed = sum(1 for r in self.test_results if r['passed'] and r['critical'])
        critical_total = sum(1 for r in self.test_results if r['critical'])
        
        # Show results grouped by status
        print("\n✅ SUCCESSFUL FIXES:")
        for result in self.test_results:
            if result['passed']:
                critical_marker = " (CRITICAL)" if result['critical'] else ""
                print(f"   • {result['test']}{critical_marker}")
                if result['details']:
                    print(f"     {result['details']}")
        
        if self.failed_tests:
            print("\n❌ REMAINING ISSUES:")
            for failure in self.failed_tests:
                critical_marker = " (CRITICAL)" if failure['critical'] else ""
                print(f"   • {failure['test']}{critical_marker}")
                print(f"     {failure['details']}")
        
        print(f"\n🎯 OVERALL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        print(f"🚨 CRITICAL: {critical_passed}/{critical_total} critical fixes working ({critical_passed/critical_total*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 ALL CP7 SECURITY FIXES VALIDATED!")
            print("\n✅ Key Security Features Now Working:")
            print("   • CORS preflight (OPTIONS) returning 200")
            print("   • CORS headers present in responses")
            print("   • Rate limiting headers visible (X-RateLimit-*)")
            print("   • Error schema with correlation IDs functioning")
            print("   • Health endpoints returning proper JSON")
            print("\n🚀 CP7 READY FOR DOCUMENTATION PHASE!")
            return True
        else:
            print(f"\n⚠️  {total-passed} issues still need fixing:")
            
            if critical_passed < critical_total:
                print(f"🚨 {critical_total-critical_passed} CRITICAL issues must be resolved before approval")
            
            print("\n🔧 Additional fixes needed before proceeding to documentation.")
            return False

async def main():
    """Main test runner"""
    tester = CP7SecurityTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ CP7 Security Validation Complete - All fixes working!")
        print("Ready for documentation phase!")
        return 0
    else:
        print("\n❌ CP7 Security Validation Complete - Issues found!")
        print("Additional fixes needed before proceeding.")
        return 1

if __name__ == "__main__":
    import sys
    result = asyncio.run(main())
    sys.exit(result)