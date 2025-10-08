#!/usr/bin/env python3
"""
Comprehensive Backend Test for GreyOak Score CP5 Implementation
Tests Risk Penalty Calculator, Guardrails Engine, and Final Scoring Engine
"""

import sys
import os
import subprocess
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

class CP5BackendTester:
    """Comprehensive tester for CP5 modules"""
    
    def __init__(self):
        self.test_results = []
        
    def log_test(self, test_name, passed, details=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        print(f"{status}: {test_name}")
        if details and not passed:
            print(f"   Details: {details}")
    
    def run_unit_tests(self):
        """Run all CP5 unit tests"""
        print("\n🧪 Running CP5 Unit Tests...")
        
        try:
            # Change to backend directory
            os.chdir(backend_path)
            
            # Run unit tests for CP5 modules
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/unit/test_risk_penalty.py",
                "tests/unit/test_guardrails.py", 
                "tests/unit/test_scoring.py",
                "-v", "--tb=short"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Count passed tests
                lines = result.stdout.split('\n')
                passed_count = sum(1 for line in lines if " PASSED " in line)
                self.log_test(f"Unit Tests ({passed_count} tests)", True, f"All {passed_count} unit tests passed")
            else:
                self.log_test("Unit Tests", False, f"Exit code: {result.returncode}\n{result.stdout}\n{result.stderr}")
                
        except Exception as e:
            self.log_test("Unit Tests", False, f"Exception: {str(e)}")
    
    def test_module_imports(self):
        """Test that all CP5 modules can be imported"""
        print("\n📦 Testing Module Imports...")
        
        try:
            from greyoak_score.core.risk_penalty import calculate_risk_penalty
            self.log_test("Risk Penalty Import", True, "Successfully imported calculate_risk_penalty")
        except Exception as e:
            self.log_test("Risk Penalty Import", False, f"Import failed: {str(e)}")
        
        try:
            from greyoak_score.core.guardrails import apply_guardrails
            self.log_test("Guardrails Import", True, "Successfully imported apply_guardrails")
        except Exception as e:
            self.log_test("Guardrails Import", False, f"Import failed: {str(e)}")
        
        try:
            from greyoak_score.core.scoring import calculate_greyoak_score
            self.log_test("Scoring Import", True, "Successfully imported calculate_greyoak_score")
        except Exception as e:
            self.log_test("Scoring Import", False, f"Import failed: {str(e)}")
        
        try:
            from greyoak_score.core.config_manager import ConfigManager
            from pathlib import Path
            config_dir = Path(__file__).parent / "backend" / "configs"
            config = ConfigManager(config_dir)
            self.log_test("Config Manager", True, "Successfully created ConfigManager instance")
        except Exception as e:
            self.log_test("Config Manager", False, f"Config creation failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting CP5 Backend Testing...")
        print("=" * 60)
        
        # Run all test categories
        self.run_unit_tests()
        self.test_module_imports()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            print(f"{status} {result['test']}")
        
        print(f"\n🎯 OVERALL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! CP5 implementation is working correctly.")
            return True
        else:
            print(f"⚠️  {total-passed} tests failed. Review the issues above.")
            return False

def main():
    """Main test runner"""
    tester = CP5BackendTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ CP5 Backend Testing Complete - All systems operational!")
        sys.exit(0)
    else:
        print("\n❌ CP5 Backend Testing Complete - Issues found!")
        sys.exit(1)

if __name__ == "__main__":
    main()