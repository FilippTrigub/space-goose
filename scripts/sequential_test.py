#!/usr/bin/env python3
"""
Sequential Project Performance Test

Tests project creation and deletion in sequence, repeating N times.
Tracks timing and success rates for create/delete operations.

Usage: python sequential_test.py --iterations 10 --base-url http://localhost:8000
"""

import asyncio
import aiohttp
import argparse
import time
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional

class PerformanceMetrics:
    def __init__(self):
        self.iterations = []
        self.total_successes = 0
        self.total_failures = 0
        self.create_successes = 0
        self.create_failures = 0
        self.delete_successes = 0
        self.delete_failures = 0
        self.create_timeouts = 0
        self.delete_timeouts = 0
    
    def add_iteration(self, iteration_data: Dict):
        self.iterations.append(iteration_data)
        
        if iteration_data['create_success']:
            self.create_successes += 1
        else:
            self.create_failures += 1
            if iteration_data.get('create_timeout', False):
                self.create_timeouts += 1
        
        if iteration_data['delete_success']:
            self.delete_successes += 1
        else:
            self.delete_failures += 1
            if iteration_data.get('delete_timeout', False):
                self.delete_timeouts += 1
        
        if iteration_data['create_success'] and iteration_data['delete_success']:
            self.total_successes += 1
        else:
            self.total_failures += 1
    
    def get_summary(self) -> Dict:
        total_iterations = len(self.iterations)
        if total_iterations == 0:
            return {"error": "No iterations completed"}
        
        create_times = [i['create_time'] for i in self.iterations if i['create_success']]
        delete_times = [i['delete_time'] for i in self.iterations if i['delete_success']]
        total_times = [i['total_time'] for i in self.iterations]
        
        return {
            "total_iterations": total_iterations,
            "overall_success_rate": (self.total_successes / total_iterations) * 100,
            "create_success_rate": (self.create_successes / total_iterations) * 100,
            "delete_success_rate": (self.delete_successes / total_iterations) * 100,
            "create_timeout_rate": (self.create_timeouts / total_iterations) * 100,
            "delete_timeout_rate": (self.delete_timeouts / total_iterations) * 100,
            "timing": {
                "avg_create_time": sum(create_times) / len(create_times) if create_times else 0,
                "max_create_time": max(create_times) if create_times else 0,
                "min_create_time": min(create_times) if create_times else 0,
                "avg_delete_time": sum(delete_times) / len(delete_times) if delete_times else 0,
                "max_delete_time": max(delete_times) if delete_times else 0,
                "min_delete_time": min(delete_times) if delete_times else 0,
                "avg_total_time": sum(total_times) / len(total_times),
                "max_total_time": max(total_times),
                "min_total_time": min(total_times)
            }
        }

class SequentialTester:
    def __init__(self, base_url: str, user_id: str = "user1"):
        self.base_url = base_url.rstrip('/')
        self.user_id = user_id
        self.metrics = PerformanceMetrics()
    
    async def create_project(self, session: aiohttp.ClientSession, project_name: str, timeout: int = 150) -> tuple[bool, Optional[str], float, bool]:
        """
        Create a project and return (success, project_id, time_taken, timed_out)
        """
        url = f"{self.base_url}/users/{self.user_id}/projects"
        payload = {
            "name": project_name,
            "github_key": None,
            "repo_url": None
        }
        
        start_time = time.time()
        timed_out = False
        
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                end_time = time.time()
                time_taken = end_time - start_time
                
                if response.status == 200:
                    data = await response.json()
                    project_id = data.get('project_id')
                    return True, project_id, time_taken, False
                else:
                    error_text = await response.text()
                    print(f"❌ Create failed with status {response.status}: {error_text}")
                    return False, None, time_taken, False
                    
        except asyncio.TimeoutError:
            end_time = time.time()
            time_taken = end_time - start_time
            print(f"⏰ Create timed out after {timeout}s")
            return False, None, time_taken, True
        except Exception as e:
            end_time = time.time()
            time_taken = end_time - start_time
            print(f"❌ Create failed with error: {e}")
            return False, None, time_taken, False
    
    async def delete_project(self, session: aiohttp.ClientSession, project_id: str, timeout: int = 30) -> tuple[bool, float, bool]:
        """
        Delete a project and return (success, time_taken, timed_out)
        """
        url = f"{self.base_url}/users/{self.user_id}/projects/{project_id}"
        
        start_time = time.time()
        
        try:
            async with session.delete(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                end_time = time.time()
                time_taken = end_time - start_time
                
                if response.status == 200:
                    return True, time_taken, False
                else:
                    error_text = await response.text()
                    print(f"❌ Delete failed with status {response.status}: {error_text}")
                    return False, time_taken, False
                    
        except asyncio.TimeoutError:
            end_time = time.time()
            time_taken = end_time - start_time
            print(f"⏰ Delete timed out after {timeout}s")
            return False, time_taken, True
        except Exception as e:
            end_time = time.time()
            time_taken = end_time - start_time
            print(f"❌ Delete failed with error: {e}")
            return False, time_taken, False
    
    async def run_iteration(self, session: aiohttp.ClientSession, iteration: int, create_timeout: int, delete_timeout: int) -> Dict:
        """
        Run a single iteration of create->delete
        """
        iteration_start = time.time()
        project_name = f"perf-test-seq-{iteration}-{int(time.time())}"
        
        print(f"\n🔄 Iteration {iteration}: Creating project '{project_name}'...")
        
        # Create project
        create_success, project_id, create_time, create_timeout_occurred = await self.create_project(
            session, project_name, create_timeout
        )
        
        delete_success = False
        delete_time = 0.0
        delete_timeout_occurred = False
        
        # Delete project if creation succeeded
        if create_success and project_id:
            print(f"✅ Created in {create_time:.1f}s, deleting project {project_id}...")
            delete_success, delete_time, delete_timeout_occurred = await self.delete_project(
                session, project_id, delete_timeout
            )
            if delete_success:
                print(f"✅ Deleted in {delete_time:.1f}s")
            else:
                print(f"❌ Delete failed after {delete_time:.1f}s")
        else:
            print(f"❌ Create failed after {create_time:.1f}s, skipping delete")
        
        iteration_end = time.time()
        total_time = iteration_end - iteration_start
        
        result = {
            'iteration': iteration,
            'project_name': project_name,
            'project_id': project_id,
            'create_success': create_success,
            'delete_success': delete_success,
            'create_time': create_time,
            'delete_time': delete_time,
            'total_time': total_time,
            'create_timeout': create_timeout_occurred,
            'delete_timeout': delete_timeout_occurred,
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    
    async def run_test(self, iterations: int, create_timeout: int = 150, delete_timeout: int = 30):
        """
        Run the sequential test for N iterations
        """
        print(f"🚀 Starting sequential performance test")
        print(f"📊 Iterations: {iterations}")
        print(f"⏰ Create timeout: {create_timeout}s, Delete timeout: {delete_timeout}s")
        print(f"🌐 Base URL: {self.base_url}")
        print(f"👤 User ID: {self.user_id}")
        
        test_start = time.time()
        
        async with aiohttp.ClientSession() as session:
            for i in range(1, iterations + 1):
                try:
                    result = await self.run_iteration(session, i, create_timeout, delete_timeout)
                    self.metrics.add_iteration(result)
                    
                    # Progress update
                    success_rate = (self.metrics.total_successes / i) * 100
                    print(f"📈 Progress: {i}/{iterations} ({success_rate:.1f}% success rate)")
                    
                except Exception as e:
                    print(f"❌ Iteration {i} failed with unexpected error: {e}")
                    # Add failed iteration
                    failed_result = {
                        'iteration': i,
                        'create_success': False,
                        'delete_success': False,
                        'create_time': 0.0,
                        'delete_time': 0.0,
                        'total_time': 0.0,
                        'create_timeout': False,
                        'delete_timeout': False,
                        'error': str(e)
                    }
                    self.metrics.add_iteration(failed_result)
        
        test_end = time.time()
        total_test_time = test_end - test_start
        
        # Generate report
        summary = self.metrics.get_summary()
        summary['test_duration'] = total_test_time
        summary['test_type'] = 'sequential'
        
        print(f"\n🏁 Sequential test completed in {total_test_time:.1f}s")
        self.print_summary(summary)
        
        return summary
    
    def print_summary(self, summary: Dict):
        """
        Print a formatted test summary
        """
        print(f"\n" + "="*60)
        print(f"📋 SEQUENTIAL TEST SUMMARY")
        print(f"="*60)
        print(f"📊 Total Iterations: {summary['total_iterations']}")
        print(f"✅ Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"📈 Create Success Rate: {summary['create_success_rate']:.1f}%")
        print(f"🗑️  Delete Success Rate: {summary['delete_success_rate']:.1f}%")
        print(f"⏰ Create Timeout Rate: {summary['create_timeout_rate']:.1f}%")
        print(f"⏰ Delete Timeout Rate: {summary['delete_timeout_rate']:.1f}%")
        print(f"🕒 Test Duration: {summary['test_duration']:.1f}s")
        
        timing = summary['timing']
        print(f"\n⏱️  TIMING ANALYSIS")
        print(f"-"*30)
        print(f"Create Times: avg={timing['avg_create_time']:.1f}s, max={timing['max_create_time']:.1f}s, min={timing['min_create_time']:.1f}s")
        print(f"Delete Times: avg={timing['avg_delete_time']:.1f}s, max={timing['max_delete_time']:.1f}s, min={timing['min_delete_time']:.1f}s")
        print(f"Total Times:  avg={timing['avg_total_time']:.1f}s, max={timing['max_total_time']:.1f}s, min={timing['min_total_time']:.1f}s")

def main():
    parser = argparse.ArgumentParser(description='Sequential Project Performance Test')
    parser.add_argument('--iterations', '-n', type=int, default=5, 
                       help='Number of iterations to run (default: 5)')
    parser.add_argument('--base-url', '-u', type=str, default='http://localhost:8000',
                       help='Base URL of the API (default: http://localhost:8000)')
    parser.add_argument('--user-id', type=str, default='user1',
                       help='User ID to use for tests (default: user1)')
    parser.add_argument('--create-timeout', type=int, default=150,
                       help='Create operation timeout in seconds (default: 150)')
    parser.add_argument('--delete-timeout', type=int, default=30,
                       help='Delete operation timeout in seconds (default: 30)')
    parser.add_argument('--output', '-o', type=str,
                       help='Output file to save results as JSON')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.iterations <= 0:
        print("❌ Error: iterations must be positive")
        sys.exit(1)
    
    tester = SequentialTester(args.base_url, args.user_id)
    
    try:
        summary = asyncio.run(tester.run_test(
            args.iterations, 
            args.create_timeout, 
            args.delete_timeout
        ))
        
        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump({
                    'summary': summary,
                    'iterations': tester.metrics.iterations
                }, f, indent=2)
            print(f"💾 Results saved to {args.output}")
        
    except KeyboardInterrupt:
        print("\n⛔ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()