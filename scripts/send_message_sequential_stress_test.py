#!/usr/bin/env python3
"""
Stress Test for Send Message Endpoint
=====================================

This script performs stress testing on the streaming send_message endpoint of the
Space Goose K8s Manager API. It tests endpoint stability by sending N sequential
follow-up messages and capturing streaming responses.

The test focuses on endpoint reliability, response times, and error handling
rather than AI response quality.

Usage:
    python send_message_sequential_stress_test.py --help
    python send_message_sequential_stress_test.py --host localhost --messages 10
    python send_message_sequential_stress_test.py --config config.json

Requirements:
    pip install httpx asyncio argparse json pathlib datetime statistics
"""

import asyncio
import json
import time
import argparse
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import httpx


@dataclass
class TestConfig:
    """Configuration for the stress test."""

    host: str = "http://localhost:8000"
    user_id: str = "user1"
    project_name: str = "Stress Test Project"
    session_name: str = "Stress Test Session"
    num_messages: int = 10
    timeout: int = 60
    delay_between_messages: float = 1.0
    max_retries: int = 3
    cleanup_after_test: bool = True


@dataclass
class TestResult:
    """Results from a single message test."""

    message_num: int
    question: str
    success: bool
    response_time: float
    stream_chunks: int
    total_response_size: int
    error_message: Optional[str] = None
    status_code: Optional[int] = None


@dataclass
class StressTestResults:
    """Overall results from the stress test."""

    config: TestConfig
    start_time: datetime
    end_time: datetime
    total_duration: float
    project_id: Optional[str]
    session_id: Optional[str]
    individual_results: List[TestResult]
    success_rate: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    total_chunks_received: int
    total_response_size: int
    errors: List[str]


class SendMessageStressTester:
    """Main stress tester class for the send_message endpoint."""

    # Predetermined questions for consistent testing
    PREDETERMINED_QUESTIONS = [
        "Hello, can you help me with Python programming?",
        "What is the difference between a list and a tuple in Python?",
        "How do I handle exceptions in Python?",
        "Can you explain what a decorator is?",
        "What is the difference between __str__ and __repr__?",
        "How do I create a virtual environment?",
        "What is the purpose of the __init__.py file?",
        "How do I use list comprehensions?",
        "What is the difference between deep copy and shallow copy?",
        "How do I work with JSON data in Python?",
        "What is a lambda function and when should I use it?",
        "How do I handle file I/O operations?",
        "What is the difference between synchronous and asynchronous programming?",
        "How do I use the requests library?",
        "What are context managers and how do I use them?",
        "How do I debug Python code effectively?",
        "What is the difference between a class method and a static method?",
        "How do I work with dates and times in Python?",
        "What are generators and how do they work?",
        "How do I use regular expressions in Python?",
        "What is the difference between Python 2 and Python 3?",
        "How do I install external packages with pip?",
        "What is the Python Global Interpreter Lock (GIL)?",
        "How do I write unit tests in Python?",
        "What is the difference between is and ==?",
        "How do I implement inheritance in Python?",
        "What are metaclasses and why would I use them?",
        "How do I serialize and deserialize objects in Python?",
        "What is monkey patching in Python?",
        "How do I connect to a database using Python?",
        "What is the difference between mutable and immutable types?",
        "How do I use the itertools module?",
        "What is the purpose of __slots__ in a class?",
        "How do I profile my Python code for performance?",
        "What is duck typing in Python?",
        "How do I use Python for web scraping?",
        "What are f-strings and how do they work?",
        "How do I use type hints in Python?",
        "What is the difference between bytes and str?",
        "How do I handle concurrency with asyncio?",
        "What are Python’s built-in data structures?",
        "How do I implement polymorphism in Python?",
        "What is the difference between @staticmethod and @classmethod?",
        "How do I handle environment variables in Python?",
        "What is the purpose of the with statement?",
        "How do I use Python’s logging module?",
        "What are Python namespaces and how do they work?",
        "How do I use the collections module?",
        "What is memoization and how do I implement it?",
        "How do I create a REST API with Flask?",
        "What is the difference between yield and return?",
        "How do I implement caching in Python?",
        "How do I read and write CSV files?",
        "What is the difference between multiprocessing and multithreading?",
        "How do I use Python’s built-in sorting functions?",
        "What is the difference between __new__ and __init__?",
        "How do I implement an abstract base class?",
        "What are Python’s built-in functions?",
        "How do I use Python with Docker?",
        "What is dependency injection in Python?",
        "How do I secure sensitive data in a Python project?",
        "What is method resolution order (MRO)?",
        "How do I build command-line tools in Python?",
        "What is the purpose of virtualenv vs venv?",
        "How do I parse XML data in Python?",
        "What are Python descriptors?",
        "How do I integrate Python with machine learning libraries?",
        "What is pytest and how do I use it?",
        "How do I mock objects in unit tests?",
        "What is the difference between a shallow copy and assignment?",
        "How do I work with Excel files in Python?",
        "What are Python’s magic methods?",
        "How do I handle circular imports?",
        "What is the purpose of requirements.txt?",
        "How do I package a Python project?",
        "What is the difference between compile-time and runtime in Python?",
        "How do I work with SQLite in Python?",
        "What are Python decorators used for in real projects?",
        "How do I schedule tasks with Python?",
        "What is the difference between int and float precision?",
        "How do I use virtual environments with poetry?",
        "What is the __main__ block used for?",
        "How do I implement logging best practices?",
        "What are Python dataclasses?",
        "How do I work with environment files (.env)?",
        "What is the purpose of pipenv?",
        "How do I use async/await properly?",
        "What is the difference between asyncio and threading?",
        "How do I create and use Python packages?",
        "What is dependency management in Python?",
        "How do I deploy a Python app to the cloud?",
        "What are Python’s best practices for project structure?",
        "How do I manage memory leaks in Python?",
        "What is PEP 8 and why is it important?",
        "How do I use Python with APIs?",
        "What are Python’s built-in modules?",
        "How do I optimize Python loops?",
        "What is the difference between an iterator and an iterable?",
        "How do I integrate Python with GitHub Actions?",
        "What is Python’s garbage collector?",
        "How do I contribute to open-source Python projects?",
        "What are Python wheels and why are they used?",
        "How do I measure time complexity of Python code?",
        "What is the best way to learn advanced Python concepts?",
    ]

    def __init__(self, config: TestConfig):
        self.config = config
        self.base_url = f"{config.host}"
        self.client = httpx.AsyncClient(timeout=config.timeout)
        self.project_id: Optional[str] = None
        self.session_id: Optional[str] = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    async def setup_test_environment(self) -> Tuple[str, str]:
        """Set up a project and session for testing."""
        print("🔧 Setting up test environment...")

        # Create project
        print(f"Creating project: {self.config.project_name}")
        create_project_url = f"{self.base_url}/users/{self.config.user_id}/projects"
        project_data = {"name": self.config.project_name}

        response = await self.client.post(create_project_url, json=project_data)
        if response.status_code != 200:
            raise Exception(
                f"Failed to create project: {response.status_code} - {response.text}"
            )

        project_result = response.json()
        self.project_id = project_result["project_id"]
        print(f"✅ Project created: {self.project_id}")

        # Activate project
        print("Activating project...")
        activate_url = f"{self.base_url}/users/{self.config.user_id}/projects/{self.project_id}/activate"
        response = await self.client.post(activate_url)
        if response.status_code != 200:
            raise Exception(
                f"Failed to activate project: {response.status_code} - {response.text}"
            )
        print("✅ Project activated")

        # Wait a bit for the project to be fully ready
        print("⏱️  Waiting for project to be fully ready...")
        await asyncio.sleep(5)

        # Create session
        print(f"Creating session: {self.config.session_name}")
        create_session_url = f"{self.base_url}/users/{self.config.user_id}/projects/{self.project_id}/sessions"
        session_data = {"name": self.config.session_name}

        response = await self.client.post(create_session_url, json=session_data)
        if response.status_code != 200:
            raise Exception(
                f"Failed to create session: {response.status_code} - {response.text}"
            )

        session_result = response.json()
        self.session_id = session_result["session"]["session_id"]
        print(f"✅ Session created: {self.session_id}")

        return self.project_id, self.session_id

    async def cleanup_test_environment(self):
        """Clean up the test environment."""
        if not self.config.cleanup_after_test:
            print("🔧 Cleanup disabled, keeping test resources")
            return

        print("🧹 Cleaning up test environment...")

        if self.project_id:
            try:
                delete_url = f"{self.base_url}/users/{self.config.user_id}/projects/{self.project_id}"
                response = await self.client.delete(delete_url)
                if response.status_code == 200:
                    print("✅ Test project deleted")
                else:
                    print(f"⚠️  Failed to delete project: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error during cleanup: {e}")

    async def parse_sse_stream(self, response: httpx.Response) -> Tuple[int, int]:
        """Parse Server-Sent Events stream and count chunks/size."""
        chunk_count = 0
        total_size = 0

        async for chunk in response.aiter_text():
            if chunk.strip():  # Skip empty chunks
                chunk_count += 1
                total_size += len(chunk)

                # Parse SSE format
                lines = chunk.strip().split("\\n")
                for line in lines:
                    if line.startswith("data: "):
                        try:
                            json_str = line[6:]  # Remove 'data: ' prefix
                            if json_str.strip():
                                parsed_data = json.loads(json_str)
                                # Check for completion or error signals
                                if isinstance(parsed_data, dict):
                                    if parsed_data.get("error"):
                                        print(
                                            f"⚠️  Stream error: {parsed_data['error']}"
                                        )
                                    elif parsed_data.get("type") == "completion":
                                        break
                        except json.JSONDecodeError:
                            # Non-JSON data, continue parsing
                            pass

        return chunk_count, total_size

    async def send_single_message(self, message_num: int, question: str) -> TestResult:
        """Send a single message and measure the response."""
        start_time = time.time()

        try:
            # Prepare message request
            message_url = f"{self.base_url}/users/{self.config.user_id}/projects/{self.project_id}/messages"
            message_data = {"session_id": self.session_id, "content": question}

            # Send message with streaming
            async with self.client.stream(
                "POST",
                message_url,
                json=message_data,
                headers={"Accept": "text/event-stream"},
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    return TestResult(
                        message_num=message_num,
                        question=question,
                        success=False,
                        response_time=time.time() - start_time,
                        stream_chunks=0,
                        total_response_size=0,
                        error_message=f"HTTP {response.status_code}: {error_text.decode()}",
                        status_code=response.status_code,
                    )

                # Parse the streaming response
                chunk_count, total_size = await self.parse_sse_stream(response)

                response_time = time.time() - start_time
                return TestResult(
                    message_num=message_num,
                    question=question,
                    success=True,
                    response_time=response_time,
                    stream_chunks=chunk_count,
                    total_response_size=total_size,
                    status_code=response.status_code,
                )

        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                message_num=message_num,
                question=question,
                success=False,
                response_time=response_time,
                stream_chunks=0,
                total_response_size=0,
                error_message=str(e),
            )

    async def run_stress_test(self) -> StressTestResults:
        """Run the complete stress test."""
        print(f"🚀 Starting stress test with {self.config.num_messages} messages")
        print(f"Target: {self.base_url}")
        print(f"User: {self.config.user_id}")
        print(f"Delay between messages: {self.config.delay_between_messages}s")
        print("=" * 60)

        start_time = datetime.now()
        results: List[TestResult] = []

        try:
            # Setup test environment
            await self.setup_test_environment()

            # Run the stress test
            for i in range(self.config.num_messages):
                message_num = i + 1
                question = self.PREDETERMINED_QUESTIONS[
                    i % len(self.PREDETERMINED_QUESTIONS)
                ]

                print(
                    f"📨 Message {message_num}/{self.config.num_messages}: Sending question..."
                )

                # Send message with retries
                result = None
                for attempt in range(self.config.max_retries):
                    result = await self.send_single_message(message_num, question)
                    if result.success:
                        break
                    elif attempt < self.config.max_retries - 1:
                        print(f"⚠️  Attempt {attempt + 1} failed, retrying...")
                        await asyncio.sleep(1)

                results.append(result)

                # Print result
                if result.success:
                    print(
                        f"✅ Message {message_num} completed in {result.response_time:.2f}s "
                        f"({result.stream_chunks} chunks, {result.total_response_size} bytes)"
                    )
                else:
                    print(f"❌ Message {message_num} failed: {result.error_message}")

                # Wait before next message
                if i < self.config.num_messages - 1:
                    await asyncio.sleep(self.config.delay_between_messages)

        finally:
            # Always attempt cleanup
            await self.cleanup_test_environment()

        end_time = datetime.now()

        # Calculate statistics
        successful_results = [r for r in results if r.success]
        success_rate = len(successful_results) / len(results) * 100 if results else 0

        response_times = [r.response_time for r in successful_results]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        total_chunks = sum(r.stream_chunks for r in results)
        total_size = sum(r.total_response_size for r in results)

        errors = [
            f"Message {r.message_num}: {r.error_message}"
            for r in results
            if not r.success and r.error_message
        ]

        return StressTestResults(
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            total_duration=(end_time - start_time).total_seconds(),
            project_id=self.project_id,
            session_id=self.session_id,
            individual_results=results,
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            total_chunks_received=total_chunks,
            total_response_size=total_size,
            errors=errors,
        )


def print_test_results(results: StressTestResults):
    """Print comprehensive test results."""
    print("\\n" + "=" * 60)
    print("📊 STRESS TEST RESULTS")
    print("=" * 60)

    # Test configuration
    print(f"🔧 Configuration:")
    print(f"   Host: {results.config.host}")
    print(f"   User: {results.config.user_id}")
    print(f"   Messages: {results.config.num_messages}")
    print(f"   Delay: {results.config.delay_between_messages}s")
    print(f"   Timeout: {results.config.timeout}s")

    # Test execution
    print(f"\\n⏱️  Execution:")
    print(f"   Start: {results.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End: {results.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Duration: {results.total_duration:.2f}s")

    if results.project_id:
        print(f"   Project ID: {results.project_id}")
        print(f"   Session ID: {results.session_id}")

    # Success metrics
    print(f"\\n📈 Success Metrics:")
    print(
        f"   Success Rate: {results.success_rate:.1f}% "
        f"({len([r for r in results.individual_results if r.success])}/{len(results.individual_results)})"
    )

    if results.success_rate > 0:
        print(f"   Avg Response Time: {results.avg_response_time:.2f}s")
        print(f"   Min Response Time: {results.min_response_time:.2f}s")
        print(f"   Max Response Time: {results.max_response_time:.2f}s")
        print(f"   Total Chunks: {results.total_chunks_received:,}")
        print(f"   Total Data: {results.total_response_size:,} bytes")

    # Error summary
    if results.errors:
        print(f"\\n❌ Errors ({len(results.errors)}):")
        for error in results.errors:
            print(f"   {error}")

    # Performance assessment
    print(f"\\n🎯 Performance Assessment:")
    if results.success_rate >= 95:
        print("   ✅ EXCELLENT - Very stable endpoint")
    elif results.success_rate >= 80:
        print("   ⚠️  GOOD - Mostly stable with some issues")
    elif results.success_rate >= 50:
        print("   ⚠️  POOR - Significant stability issues")
    else:
        print("   ❌ CRITICAL - Endpoint is unstable")

    if results.success_rate > 0:
        if results.avg_response_time < 5:
            print("   ⚡ Fast response times")
        elif results.avg_response_time < 15:
            print("   🐌 Moderate response times")
        else:
            print("   🐢 Slow response times")


def save_results_to_json(results: StressTestResults, filename: str):
    """Save test results to a JSON file."""
    # Convert dataclasses to dictionaries for JSON serialization
    results_dict = {
        "config": asdict(results.config),
        "start_time": results.start_time.isoformat(),
        "end_time": results.end_time.isoformat(),
        "total_duration": results.total_duration,
        "project_id": results.project_id,
        "session_id": results.session_id,
        "individual_results": [asdict(r) for r in results.individual_results],
        "success_rate": results.success_rate,
        "avg_response_time": results.avg_response_time,
        "min_response_time": results.min_response_time,
        "max_response_time": results.max_response_time,
        "total_chunks_received": results.total_chunks_received,
        "total_response_size": results.total_response_size,
        "errors": results.errors,
    }

    with open(filename, "w") as f:
        json.dump(results_dict, f, indent=2)

    print(f"📄 Results saved to: {filename}")


async def main():
    """Main function to run the stress test."""
    parser = argparse.ArgumentParser(
        description="Stress test for send_message endpoint"
    )
    parser.add_argument(
        "--host", default="http://localhost:8000", help="API host (default: localhost)"
    )
    parser.add_argument("--user", default="user1", help="User ID (default: user1)")
    parser.add_argument(
        "--messages",
        type=int,
        default=10,
        help="Number of messages to send (default: 10)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between messages in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Request timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--no-cleanup", action="store_true", help="Don't cleanup test resources"
    )
    parser.add_argument("--output", help="JSON output file for results")
    parser.add_argument("--config", help="Load configuration from JSON file")

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path) as f:
                config_data = json.load(f)
            config = TestConfig(**config_data)
        else:
            print(f"❌ Configuration file not found: {args.config}")
            return
    else:
        config = TestConfig(
            host=args.host,
            user_id=args.user,
            num_messages=args.messages,
            delay_between_messages=args.delay,
            timeout=args.timeout,
            cleanup_after_test=not args.no_cleanup,
        )

    # Run the test
    async with SendMessageStressTester(config) as tester:
        try:
            results = await tester.run_stress_test()

            # Print results
            print_test_results(results)

            # Save to file if requested
            if args.output:
                save_results_to_json(results, args.output)
            else:
                # Save with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"stress_test_results_{timestamp}.json"
                save_results_to_json(results, filename)

        except KeyboardInterrupt:
            print("\\n⚠️  Test interrupted by user")
        except Exception as e:
            print(f"\\n❌ Test failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
