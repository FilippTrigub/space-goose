#!/usr/bin/env python3
"""
Parallel Project Performance Test

Tests creating and deleting N projects simultaneously.
Tracks timing and success rates for create/delete operations under load.

Usage: python parallel_test.py --projects 5 --base-url http://localhost:8000
"""

import asyncio
import aiohttp
import argparse
import time
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional


class ParallelMetrics:
    def __init__(self):
        self.create_results = []
        self.delete_results = []
        self.create_successes = 0
        self.create_failures = 0
        self.delete_successes = 0
        self.delete_failures = 0
        self.create_timeouts = 0
        self.delete_timeouts = 0

    def add_create_result(self, result: Dict):
        self.create_results.append(result)
        if result["success"]:
            self.create_successes += 1
        else:
            self.create_failures += 1
            if result.get("timeout", False):
                self.create_timeouts += 1

    def add_delete_result(self, result: Dict):
        self.delete_results.append(result)
        if result["success"]:
            self.delete_successes += 1
        else:
            self.delete_failures += 1
            if result.get("timeout", False):
                self.delete_timeouts += 1

    def get_summary(self) -> Dict:
        total_projects = len(self.create_results)
        if total_projects == 0:
            return {"error": "No projects tested"}

        successful_creates = [r for r in self.create_results if r["success"]]
        successful_deletes = [r for r in self.delete_results if r["success"]]

        create_times = [r["time_taken"] for r in successful_creates]
        delete_times = [r["time_taken"] for r in successful_deletes]

        # Overall success rate (both create and delete must succeed)
        successful_project_ids = {r["project_id"] for r in successful_creates}
        deleted_project_ids = {
            r["project_id"] for r in successful_deletes if r.get("project_id")
        }
        overall_successes = len(
            successful_project_ids.intersection(deleted_project_ids)
        )

        return {
            "total_projects": total_projects,
            "overall_success_rate": (overall_successes / total_projects) * 100,
            "create_success_rate": (self.create_successes / total_projects) * 100,
            "delete_success_rate": (
                (self.delete_successes / len(self.delete_results)) * 100
                if self.delete_results
                else 0
            ),
            "create_timeout_rate": (self.create_timeouts / total_projects) * 100,
            "delete_timeout_rate": (
                (self.delete_timeouts / len(self.delete_results)) * 100
                if self.delete_results
                else 0
            ),
            "timing": {
                "create": {
                    "avg": sum(create_times) / len(create_times) if create_times else 0,
                    "max": max(create_times) if create_times else 0,
                    "min": min(create_times) if create_times else 0,
                    "count": len(create_times),
                },
                "delete": {
                    "avg": sum(delete_times) / len(delete_times) if delete_times else 0,
                    "max": max(delete_times) if delete_times else 0,
                    "min": min(delete_times) if delete_times else 0,
                    "count": len(delete_times),
                },
            },
            "concurrency": {
                "successful_creates": len(successful_creates),
                "successful_deletes": len(successful_deletes),
                "failed_creates": self.create_failures,
                "failed_deletes": self.delete_failures,
            },
        }


class ParallelTester:
    def __init__(self, base_url: str, user_id: str = "user1"):
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.metrics = ParallelMetrics()

    async def create_project(
        self,
        session: aiohttp.ClientSession,
        project_name: str,
        project_index: int,
        timeout: int = 150,
    ) -> Dict:
        """
        Create a single project and return detailed results
        """
        url = f"{self.base_url}/users/{self.user_id}/projects"
        payload = {"name": project_name, "github_key": None, "repo_url": None}

        start_time = time.time()

        try:
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                end_time = time.time()
                time_taken = end_time - start_time

                if response.status == 200:
                    data = await response.json()
                    project_id = data.get("project_id")
                    return {
                        "project_index": project_index,
                        "project_name": project_name,
                        "project_id": project_id,
                        "success": True,
                        "time_taken": time_taken,
                        "timeout": False,
                        "status_code": response.status,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    error_text = await response.text()
                    return {
                        "project_index": project_index,
                        "project_name": project_name,
                        "project_id": None,
                        "success": False,
                        "time_taken": time_taken,
                        "timeout": False,
                        "status_code": response.status,
                        "error": error_text,
                        "timestamp": datetime.now().isoformat(),
                    }

        except asyncio.TimeoutError:
            end_time = time.time()
            time_taken = end_time - start_time
            return {
                "project_index": project_index,
                "project_name": project_name,
                "project_id": None,
                "success": False,
                "time_taken": time_taken,
                "timeout": True,
                "error": f"Timed out after {timeout}s",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            end_time = time.time()
            time_taken = end_time - start_time
            return {
                "project_index": project_index,
                "project_name": project_name,
                "project_id": None,
                "success": False,
                "time_taken": time_taken,
                "timeout": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def delete_project(
        self,
        session: aiohttp.ClientSession,
        project_id: str,
        project_name: str,
        timeout: int = 30,
    ) -> Dict:
        """
        Delete a single project and return detailed results
        """
        url = f"{self.base_url}/users/{self.user_id}/projects/{project_id}"

        start_time = time.time()

        try:
            async with session.delete(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                end_time = time.time()
                time_taken = end_time - start_time

                return {
                    "project_id": project_id,
                    "project_name": project_name,
                    "success": response.status == 200,
                    "time_taken": time_taken,
                    "timeout": False,
                    "status_code": response.status,
                    "error": await response.text() if response.status != 200 else None,
                    "timestamp": datetime.now().isoformat(),
                }

        except asyncio.TimeoutError:
            end_time = time.time()
            time_taken = end_time - start_time
            return {
                "project_id": project_id,
                "project_name": project_name,
                "success": False,
                "time_taken": time_taken,
                "timeout": True,
                "error": f"Timed out after {timeout}s",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            end_time = time.time()
            time_taken = end_time - start_time
            return {
                "project_id": project_id,
                "project_name": project_name,
                "success": False,
                "time_taken": time_taken,
                "timeout": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def run_create_phase(
        self, session: aiohttp.ClientSession, num_projects: int, create_timeout: int
    ) -> List[Dict]:
        """
        Create multiple projects simultaneously
        """
        print(f"🚀 Creating {num_projects} projects simultaneously...")
        create_start = time.time()

        # Generate project names
        timestamp = int(time.time())
        project_names = [
            f"perf-test-par-{i}-{timestamp}" for i in range(1, num_projects + 1)
        ]

        # Create tasks for parallel execution
        create_tasks = [
            self.create_project(session, name, i, create_timeout)
            for i, name in enumerate(project_names, 1)
        ]

        # Execute all creates in parallel
        create_results = await asyncio.gather(*create_tasks, return_exceptions=True)

        create_end = time.time()
        create_duration = create_end - create_start

        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(create_results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "project_index": i + 1,
                        "project_name": project_names[i],
                        "project_id": None,
                        "success": False,
                        "time_taken": 0.0,
                        "timeout": False,
                        "error": str(result),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            else:
                processed_results.append(result)

            self.metrics.add_create_result(processed_results[-1])

        successful_creates = [r for r in processed_results if r["success"]]
        failed_creates = [r for r in processed_results if not r["success"]]

        print(f"✅ Create phase completed in {create_duration:.1f}s")
        print(
            f"📊 Success: {len(successful_creates)}/{num_projects} ({len(successful_creates)/num_projects*100:.1f}%)"
        )
        print(f"❌ Failed: {len(failed_creates)} projects")

        return processed_results

    async def run_delete_phase(
        self,
        session: aiohttp.ClientSession,
        create_results: List[Dict],
        delete_timeout: int,
    ) -> List[Dict]:
        """
        Delete all successfully created projects simultaneously
        """
        successful_creates = [
            r for r in create_results if r["success"] and r["project_id"]
        ]

        if not successful_creates:
            print("⚠️  No projects to delete (no successful creates)")
            return []

        print(f"\\n🗑️  Deleting {len(successful_creates)} projects simultaneously...")
        delete_start = time.time()

        # Create tasks for parallel deletion
        delete_tasks = [
            self.delete_project(
                session, r["project_id"], r["project_name"], delete_timeout
            )
            for r in successful_creates
        ]

        # Execute all deletes in parallel
        delete_results = await asyncio.gather(*delete_tasks, return_exceptions=True)

        delete_end = time.time()
        delete_duration = delete_end - delete_start

        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(delete_results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "project_id": successful_creates[i]["project_id"],
                        "project_name": successful_creates[i]["project_name"],
                        "success": False,
                        "time_taken": 0.0,
                        "timeout": False,
                        "error": str(result),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            else:
                processed_results.append(result)

            self.metrics.add_delete_result(processed_results[-1])

        successful_deletes = [r for r in processed_results if r["success"]]
        failed_deletes = [r for r in processed_results if not r["success"]]

        print(f"✅ Delete phase completed in {delete_duration:.1f}s")
        print(
            f"📊 Success: {len(successful_deletes)}/{len(successful_creates)} ({len(successful_deletes)/len(successful_creates)*100:.1f}%)"
        )
        print(f"❌ Failed: {len(failed_deletes)} projects")

        return processed_results

    async def run_test(
        self, num_projects: int, create_timeout: int = 150, delete_timeout: int = 30
    ):
        """
        Run the parallel test for N projects
        """
        print(f"🚀 Starting parallel performance test")
        print(f"📊 Projects: {num_projects}")
        print(
            f"⏰ Create timeout: {create_timeout}s, Delete timeout: {delete_timeout}s"
        )
        print(f"🌐 Base URL: {self.base_url}")
        print(f"👤 User ID: {self.user_id}")

        test_start = time.time()

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=100)
        ) as session:
            # Phase 1: Create projects in parallel
            create_results = await self.run_create_phase(
                session, num_projects, create_timeout
            )

            # Wait a moment between phases
            await asyncio.sleep(1)

            # Phase 2: Delete projects in parallel
            delete_results = await self.run_delete_phase(
                session, create_results, delete_timeout
            )

        test_end = time.time()
        total_test_time = test_end - test_start

        # Generate report
        summary = self.metrics.get_summary()
        summary["test_duration"] = total_test_time
        summary["test_type"] = "parallel"
        summary["concurrency_level"] = num_projects

        print(f"\\n🏁 Parallel test completed in {total_test_time:.1f}s")
        self.print_summary(summary)

        return {
            "summary": summary,
            "create_results": create_results,
            "delete_results": delete_results,
        }

    def print_summary(self, summary: Dict):
        """
        Print a formatted test summary
        """
        print(f"\\n" + "=" * 60)
        print(f"📋 PARALLEL TEST SUMMARY")
        print(f"=" * 60)
        print(f"📊 Total Projects: {summary['total_projects']}")
        print(f"🔄 Concurrency Level: {summary['concurrency_level']}")
        print(f"✅ Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"📈 Create Success Rate: {summary['create_success_rate']:.1f}%")
        print(f"🗑️  Delete Success Rate: {summary['delete_success_rate']:.1f}%")
        print(f"⏰ Create Timeout Rate: {summary['create_timeout_rate']:.1f}%")
        print(f"⏰ Delete Timeout Rate: {summary['delete_timeout_rate']:.1f}%")
        print(f"🕒 Test Duration: {summary['test_duration']:.1f}s")

        create_timing = summary["timing"]["create"]
        delete_timing = summary["timing"]["delete"]
        concurrency = summary["concurrency"]

        print(f"\\n⏱️  TIMING ANALYSIS (Parallel Execution)")
        print(f"-" * 40)
        print(
            f"Create: avg={create_timing['avg']:.1f}s, max={create_timing['max']:.1f}s, min={create_timing['min']:.1f}s ({create_timing['count']} successful)"
        )
        print(
            f"Delete: avg={delete_timing['avg']:.1f}s, max={delete_timing['max']:.1f}s, min={delete_timing['min']:.1f}s ({delete_timing['count']} successful)"
        )

        print(f"\\n📊 CONCURRENCY ANALYSIS")
        print(f"-" * 25)
        print(f"Successful Creates: {concurrency['successful_creates']}")
        print(f"Successful Deletes: {concurrency['successful_deletes']}")
        print(f"Failed Creates: {concurrency['failed_creates']}")
        print(f"Failed Deletes: {concurrency['failed_deletes']}")

        if create_timing["count"] > 0:
            throughput_create = create_timing["count"] / summary["test_duration"]
            print(f"\\n🚀 THROUGHPUT")
            print(f"-" * 12)
            print(f"Create Throughput: {throughput_create:.2f} projects/second")


def main():
    parser = argparse.ArgumentParser(description="Parallel Project Performance Test")
    parser.add_argument(
        "--projects",
        "-n",
        type=int,
        default=5,
        help="Number of projects to create/delete in parallel (default: 5)",
    )
    parser.add_argument(
        "--base-url",
        "-u",
        type=str,
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="user1",
        help="User ID to use for tests (default: user1)",
    )
    parser.add_argument(
        "--create-timeout",
        type=int,
        default=300,
        help="Create operation timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--delete-timeout",
        type=int,
        default=30,
        help="Delete operation timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--output", "-o", type=str, help="Output file to save results as JSON"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.projects <= 0:
        print("❌ Error: projects must be positive")
        sys.exit(1)

    if args.projects > 50:
        print("⚠️  Warning: Testing with >50 parallel projects may overwhelm the system")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            sys.exit(0)

    tester = ParallelTester(args.base_url, args.user_id)

    try:
        results = asyncio.run(
            tester.run_test(args.projects, args.create_timeout, args.delete_timeout)
        )

        # Save results if output file specified
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            print(f"💾 Results saved to {args.output}")

    except KeyboardInterrupt:
        print("\n⛔ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
