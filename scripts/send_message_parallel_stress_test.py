#!/usr/bin/env python3
"""
Parallel Stress Test for Send Message Endpoint
==============================================

This script performs parallel stress testing on the streaming send_message endpoint
by creating multiple sessions and sending messages concurrently. It tests the API's
ability to handle high concurrent load with multiple simultaneous conversations.

The test focuses on:
- Concurrent session management
- Parallel message processing
- Resource contention handling
- Scalability under load

Usage:
    python send_message_parallel_stress_test.py --help
    python send_message_parallel_stress_test.py --sessions 5 --messages-per-session 3
    python send_message_parallel_stress_test.py --config parallel_config.json

Requirements:
    pip install httpx asyncio argparse json pathlib datetime statistics
"""

import asyncio
import json
import time
import argparse
import statistics
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
import httpx


@dataclass
class ParallelTestConfig:
    """Configuration for the parallel stress test."""

    host: str = "http://localhost:8000"
    user_id: str = "user1"
    project_name: str = "Parallel Stress Test Project"
    num_sessions: int = 5
    messages_per_session: int = 3
    timeout: int = 60
    stagger_session_creation: float = 0.5  # Delay between creating sessions
    stagger_message_sending: float = 0.2  # Random delay before sending messages
    max_retries: int = 3
    cleanup_after_test: bool = True


@dataclass
class SessionResult:
    """Results from a single session's message tests."""

    session_id: str
    session_name: str
    messages_sent: int
    messages_successful: int
    total_response_time: float
    avg_response_time: float
    total_chunks: int
    total_data_size: int
    errors: List[str] = field(default_factory=list)
    creation_time: float = 0.0
    first_message_time: float = 0.0
    last_message_time: float = 0.0


@dataclass
class MessageResult:
    """Results from a single message within a session."""

    session_id: str
    message_num: int
    question: str
    success: bool
    response_time: float
    chunks_received: int
    data_size: int
    error_message: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class ParallelStressTestResults:
    """Overall results from the parallel stress test."""

    config: ParallelTestConfig
    start_time: datetime
    end_time: datetime
    total_duration: float
    project_id: Optional[str]
    session_results: List[SessionResult]
    all_message_results: List[MessageResult]

    # Aggregate metrics
    total_sessions_created: int
    total_sessions_successful: int
    total_messages_sent: int
    total_messages_successful: int
    overall_success_rate: float
    session_success_rate: float
    message_success_rate: float

    # Performance metrics
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    response_time_p95: float
    response_time_p99: float

    # Concurrency metrics
    peak_concurrent_sessions: int
    total_chunks_received: int
    total_data_transferred: int
    messages_per_second: float

    # Error analysis
    unique_errors: List[str]
    error_count_by_type: Dict[str, int]


class ParallelMessageStressTester:
    """Main parallel stress tester class."""

    # Extended question pool for more diverse concurrent testing
    QUESTION_POOL = [
        # Basic Python concepts
        "What is the difference between a list and a tuple?",
        "How do you handle exceptions in Python?",
        "Explain Python decorators with an example.",
        "What is a lambda function in Python?",
        "How does Python's garbage collection work?",
        # Data structures and algorithms
        "How do you implement a binary search in Python?",
        "What are the time complexities of different sorting algorithms?",
        "How do you reverse a linked list in Python?",
        "Explain the difference between BFS and DFS.",
        "How do you detect a cycle in a linked list?",
        # Web development
        "How do you build a REST API with FastAPI?",
        "What is the difference between GET and POST requests?",
        "How do you handle CORS in a web application?",
        "Explain JWT authentication in web apps.",
        "How do you implement rate limiting in an API?",
        # Data science
        "How do you handle missing data in pandas?",
        "What is the difference between supervised and unsupervised learning?",
        "How do you implement linear regression from scratch?",
        "Explain the concept of overfitting in machine learning.",
        "How do you evaluate a classification model?",
        # System design
        "How would you design a URL shortening service?",
        "What is the difference between SQL and NoSQL databases?",
        "How do you implement caching in a web application?",
        "Explain the concept of microservices architecture.",
        "How do you handle database transactions?",
        # Advanced Python
        "How do metaclasses work in Python?",
        "What is the Global Interpreter Lock (GIL)?",
        "How do you implement a context manager?",
        "Explain Python's async/await functionality.",
        "How do generators work in Python?",
        # DevOps and deployment
        "How do you containerize a Python application with Docker?",
        "What is the difference between Docker and virtual machines?",
        "How do you implement CI/CD pipelines?",
        "Explain infrastructure as code concepts.",
        "How do you monitor application performance?",
        # Security
        "How do you prevent SQL injection attacks?",
        "What are common web application vulnerabilities?",
        "How do you implement secure password hashing?",
        "Explain OAuth 2.0 flow.",
        "How do you handle sensitive data in applications?",
    ]

    def __init__(self, config: ParallelTestConfig):
        self.config = config
        self.base_url = f"{config.host}"
        self.project_id: Optional[str] = None
        self.session_ids: List[str] = []

    async def create_http_client(self) -> httpx.AsyncClient:
        """Create a new HTTP client with appropriate timeout."""
        return httpx.AsyncClient(timeout=self.config.timeout)

    async def setup_test_project(self) -> str:
        """Create and activate a test project."""
        print("🔧 Setting up test project...")

        async with await self.create_http_client() as client:
            # Create project
            print(f"Creating project: {self.config.project_name}")
            create_project_url = f"{self.base_url}/users/{self.config.user_id}/projects"
            project_data = {"name": self.config.project_name}

            response = await client.post(
                create_project_url, json=project_data, timeout=120
            )
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
            response = await client.post(activate_url)
            if response.status_code != 200:
                raise Exception(
                    f"Failed to activate project: {response.status_code} - {response.text}"
                )
            print("✅ Project activated")

            # Wait for project to be fully ready
            print("⏱️  Waiting for project to be fully ready...")
            await asyncio.sleep(8)  # Longer wait for stability under load

        return self.project_id

    async def create_session(self, session_name: str) -> Tuple[str, float]:
        """Create a single session and return its ID and creation time."""
        start_time = time.time()

        async with await self.create_http_client() as client:
            create_session_url = f"{self.base_url}/users/{self.config.user_id}/projects/{self.project_id}/sessions"
            session_data = {"name": session_name}

            response = await client.post(create_session_url, json=session_data)
            if response.status_code != 200:
                raise Exception(
                    f"Failed to create session {session_name}: {response.status_code} - {response.text}"
                )

            session_result = response.json()
            session_id = session_result["session"]["session_id"]
            creation_time = time.time() - start_time

        return session_id, creation_time

    async def parse_sse_stream(self, response: httpx.Response) -> Tuple[int, int]:
        """Parse SSE stream and return chunk count and total size."""
        chunk_count = 0
        total_size = 0

        try:
            async for chunk in response.aiter_text():
                if chunk.strip():
                    chunk_count += 1
                    total_size += len(chunk)

                    # Parse SSE format
                    lines = chunk.strip().split("\\n")
                    for line in lines:
                        if line.startswith("data: "):
                            try:
                                json_str = line[6:]
                                if json_str.strip():
                                    parsed_data = json.loads(json_str)
                                    if isinstance(parsed_data, dict):
                                        if parsed_data.get("type") == "completion":
                                            return chunk_count, total_size
                            except json.JSONDecodeError:
                                continue
        except Exception:
            # Handle any streaming errors gracefully
            pass

        return chunk_count, total_size

    async def send_message_to_session(
        self, session_id: str, message_num: int, question: str
    ) -> MessageResult:
        """Send a single message to a specific session."""
        timestamp = time.time()
        start_time = time.time()

        try:
            message_url = f"{self.base_url}/users/{self.config.user_id}/projects/{self.project_id}/messages"
            message_data = {"session_id": session_id, "content": question}

            async with await self.create_http_client() as client:
                async with client.stream(
                    "POST",
                    message_url,
                    json=message_data,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        return MessageResult(
                            session_id=session_id,
                            message_num=message_num,
                            question=question,
                            success=False,
                            response_time=time.time() - start_time,
                            chunks_received=0,
                            data_size=0,
                            error_message=f"HTTP {response.status_code}: {error_text.decode()}",
                            timestamp=timestamp,
                        )

                    # Parse streaming response
                    chunk_count, total_size = await self.parse_sse_stream(response)

                    return MessageResult(
                        session_id=session_id,
                        message_num=message_num,
                        question=question,
                        success=True,
                        response_time=time.time() - start_time,
                        chunks_received=chunk_count,
                        data_size=total_size,
                        timestamp=timestamp,
                    )

        except Exception as e:
            return MessageResult(
                session_id=session_id,
                message_num=message_num,
                question=question,
                success=False,
                response_time=time.time() - start_time,
                chunks_received=0,
                data_size=0,
                error_message=str(e),
                timestamp=timestamp,
            )

    async def run_session_messages(
        self, session_id: str, session_name: str, session_num: int
    ) -> SessionResult:
        """Run all messages for a single session."""
        print(
            f"🔄 Session {session_num}: Starting {self.config.messages_per_session} messages..."
        )

        session_start_time = time.time()
        message_results: List[MessageResult] = []

        # Add random stagger to message sending
        if self.config.stagger_message_sending > 0:
            stagger_delay = random.uniform(0, self.config.stagger_message_sending)
            await asyncio.sleep(stagger_delay)

        # Send messages for this session
        for msg_num in range(1, self.config.messages_per_session + 1):
            question = random.choice(self.QUESTION_POOL)
            result = await self.send_message_to_session(session_id, msg_num, question)
            message_results.append(result)

            if result.success:
                print(
                    f"  ✅ Session {session_num}, Message {msg_num}: {result.response_time:.2f}s"
                )
            else:
                print(
                    f"  ❌ Session {session_num}, Message {msg_num}: {result.error_message}"
                )

        # Calculate session statistics
        successful_messages = [r for r in message_results if r.success]
        session_result = SessionResult(
            session_id=session_id,
            session_name=session_name,
            messages_sent=len(message_results),
            messages_successful=len(successful_messages),
            total_response_time=sum(r.response_time for r in message_results),
            avg_response_time=(
                sum(r.response_time for r in successful_messages)
                / len(successful_messages)
                if successful_messages
                else 0
            ),
            total_chunks=sum(r.chunks_received for r in message_results),
            total_data_size=sum(r.data_size for r in message_results),
            errors=[r.error_message for r in message_results if r.error_message],
            creation_time=0.0,  # Will be set by caller
            first_message_time=message_results[0].timestamp if message_results else 0,
            last_message_time=message_results[-1].timestamp if message_results else 0,
        )

        print(
            f"✅ Session {session_num} completed: {len(successful_messages)}/{len(message_results)} messages successful"
        )
        return session_result, message_results

    async def create_sessions_parallel(self) -> List[Tuple[str, str, float]]:
        """Create multiple sessions in parallel with optional staggering."""
        print(f"🔧 Creating {self.config.num_sessions} sessions...")

        session_tasks = []
        for i in range(self.config.num_sessions):
            session_name = f"Parallel Test Session {i+1}"

            # Add staggering delay
            if i > 0 and self.config.stagger_session_creation > 0:
                await asyncio.sleep(self.config.stagger_session_creation)

            task = asyncio.create_task(self.create_session(session_name))
            session_tasks.append((task, session_name))

        # Wait for all sessions to be created
        session_info = []
        for i, (task, session_name) in enumerate(session_tasks):
            try:
                session_id, creation_time = await task
                session_info.append((session_id, session_name, creation_time))
                print(
                    f"✅ Session {i+1}/{self.config.num_sessions} created: {session_id}"
                )
            except Exception as e:
                print(f"❌ Failed to create session {i+1}: {e}")
                session_info.append((None, session_name, 0.0))

        return session_info

    async def run_send_message_parallel_stress_test(self) -> ParallelStressTestResults:
        """Run the complete parallel stress test."""
        print(f"🚀 Starting parallel stress test")
        print(f"Target: {self.base_url}")
        print(f"Sessions: {self.config.num_sessions}")
        print(f"Messages per session: {self.config.messages_per_session}")
        print(
            f"Total messages: {self.config.num_sessions * self.config.messages_per_session}"
        )
        print("=" * 70)

        start_time = datetime.now()

        try:
            # Setup project
            await self.setup_test_project()

            # Create all sessions
            session_info = await self.create_sessions_parallel()
            successful_sessions = [
                (sid, name, ct) for sid, name, ct in session_info if sid is not None
            ]

            if not successful_sessions:
                raise Exception("No sessions were successfully created")

            print(
                f"\\n🚀 Running messages in parallel across {len(successful_sessions)} sessions..."
            )

            # Run messages in parallel across all sessions
            message_tasks = []
            for i, (session_id, session_name, creation_time) in enumerate(
                successful_sessions
            ):
                task = asyncio.create_task(
                    self.run_session_messages(session_id, session_name, i + 1)
                )
                message_tasks.append((task, session_id, session_name, creation_time))

            # Wait for all message tasks to complete
            session_results = []
            all_message_results = []

            for i, (task, session_id, session_name, creation_time) in enumerate(
                message_tasks
            ):
                try:
                    session_result, message_results = await task
                    session_result.creation_time = creation_time
                    session_results.append(session_result)
                    all_message_results.extend(message_results)
                except Exception as e:
                    print(f"❌ Session {i+1} failed: {e}")
                    # Create a failed session result
                    failed_result = SessionResult(
                        session_id=session_id or f"failed_{i+1}",
                        session_name=session_name,
                        messages_sent=0,
                        messages_successful=0,
                        total_response_time=0,
                        avg_response_time=0,
                        total_chunks=0,
                        total_data_size=0,
                        errors=[str(e)],
                        creation_time=creation_time,
                    )
                    session_results.append(failed_result)

        finally:
            # Cleanup
            await self.cleanup_test_environment()

        end_time = datetime.now()

        # Calculate comprehensive statistics
        return self._calculate_results(
            start_time, end_time, session_results, all_message_results
        )

    def _calculate_results(
        self,
        start_time: datetime,
        end_time: datetime,
        session_results: List[SessionResult],
        all_message_results: List[MessageResult],
    ) -> ParallelStressTestResults:
        """Calculate comprehensive test results."""

        total_duration = (end_time - start_time).total_seconds()
        successful_sessions = [s for s in session_results if s.messages_successful > 0]
        successful_messages = [m for m in all_message_results if m.success]

        # Basic counts
        total_sessions_created = len(session_results)
        total_sessions_successful = len(successful_sessions)
        total_messages_sent = len(all_message_results)
        total_messages_successful = len(successful_messages)

        # Success rates
        session_success_rate = (
            (total_sessions_successful / total_sessions_created * 100)
            if total_sessions_created > 0
            else 0
        )
        message_success_rate = (
            (total_messages_successful / total_messages_sent * 100)
            if total_messages_sent > 0
            else 0
        )
        overall_success_rate = (session_success_rate + message_success_rate) / 2

        # Response time statistics
        response_times = [m.response_time for m in successful_messages]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        # Percentiles
        if response_times:
            sorted_times = sorted(response_times)
            p95_idx = int(0.95 * len(sorted_times))
            p99_idx = int(0.99 * len(sorted_times))
            response_time_p95 = (
                sorted_times[p95_idx]
                if p95_idx < len(sorted_times)
                else max_response_time
            )
            response_time_p99 = (
                sorted_times[p99_idx]
                if p99_idx < len(sorted_times)
                else max_response_time
            )
        else:
            response_time_p95 = response_time_p99 = 0

        # Concurrency and throughput metrics
        total_chunks = sum(s.total_chunks for s in session_results)
        total_data = sum(s.total_data_size for s in session_results)
        messages_per_second = (
            total_messages_successful / total_duration if total_duration > 0 else 0
        )

        # Error analysis
        all_errors = []
        for session in session_results:
            all_errors.extend(session.errors)
        for message in all_message_results:
            if message.error_message:
                all_errors.append(message.error_message)

        unique_errors = list(set(all_errors))
        error_count_by_type = {}
        for error in all_errors:
            error_type = error.split(":")[0] if ":" in error else error
            error_count_by_type[error_type] = error_count_by_type.get(error_type, 0) + 1

        return ParallelStressTestResults(
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            project_id=self.project_id,
            session_results=session_results,
            all_message_results=all_message_results,
            total_sessions_created=total_sessions_created,
            total_sessions_successful=total_sessions_successful,
            total_messages_sent=total_messages_sent,
            total_messages_successful=total_messages_successful,
            overall_success_rate=overall_success_rate,
            session_success_rate=session_success_rate,
            message_success_rate=message_success_rate,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            response_time_p95=response_time_p95,
            response_time_p99=response_time_p99,
            peak_concurrent_sessions=total_sessions_successful,
            total_chunks_received=total_chunks,
            total_data_transferred=total_data,
            messages_per_second=messages_per_second,
            unique_errors=unique_errors,
            error_count_by_type=error_count_by_type,
        )

    async def cleanup_test_environment(self):
        """Clean up test resources."""
        if not self.config.cleanup_after_test:
            print("🔧 Cleanup disabled, keeping test resources")
            return

        print("🧹 Cleaning up test environment...")

        if self.project_id:
            try:
                async with await self.create_http_client() as client:
                    delete_url = f"{self.base_url}/users/{self.config.user_id}/projects/{self.project_id}"
                    response = await client.delete(delete_url)
                    if response.status_code == 200:
                        print("✅ Test project deleted")
                    else:
                        print(f"⚠️  Failed to delete project: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error during cleanup: {e}")


def print_parallel_test_results(results: ParallelStressTestResults):
    """Print comprehensive parallel test results."""
    print("\\n" + "=" * 70)
    print("📊 PARALLEL STRESS TEST RESULTS")
    print("=" * 70)

    # Configuration
    print(f"🔧 Configuration:")
    print(f"   Host: {results.config.host}")
    print(f"   User: {results.config.user_id}")
    print(f"   Sessions: {results.config.num_sessions}")
    print(f"   Messages per session: {results.config.messages_per_session}")
    print(
        f"   Total expected messages: {results.config.num_sessions * results.config.messages_per_session}"
    )

    # Execution summary
    print(f"\\n⏱️  Execution:")
    print(f"   Start: {results.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End: {results.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Duration: {results.total_duration:.2f}s")
    if results.project_id:
        print(f"   Project ID: {results.project_id}")

    # Success metrics
    print(f"\\n📈 Success Metrics:")
    print(f"   Overall Success Rate: {results.overall_success_rate:.1f}%")
    print(
        f"   Session Success: {results.total_sessions_successful}/{results.total_sessions_created} ({results.session_success_rate:.1f}%)"
    )
    print(
        f"   Message Success: {results.total_messages_successful}/{results.total_messages_sent} ({results.message_success_rate:.1f}%)"
    )

    # Performance metrics
    if results.total_messages_successful > 0:
        print(f"\\n⚡ Performance Metrics:")
        print(f"   Avg Response Time: {results.avg_response_time:.2f}s")
        print(f"   Min Response Time: {results.min_response_time:.2f}s")
        print(f"   Max Response Time: {results.max_response_time:.2f}s")
        print(f"   95th Percentile: {results.response_time_p95:.2f}s")
        print(f"   99th Percentile: {results.response_time_p99:.2f}s")
        print(f"   Throughput: {results.messages_per_second:.1f} messages/second")

    # Data transfer metrics
    print(f"\\n📡 Data Transfer:")
    print(f"   Total Chunks: {results.total_chunks_received:,}")
    print(
        f"   Total Data: {results.total_data_transferred:,} bytes ({results.total_data_transferred/1024:.1f} KB)"
    )

    # Concurrency metrics
    print(f"\\n🔄 Concurrency:")
    print(f"   Peak Concurrent Sessions: {results.peak_concurrent_sessions}")
    print(f"   Session Creation Stagger: {results.config.stagger_session_creation}s")
    print(f"   Message Send Stagger: {results.config.stagger_message_sending}s")

    # Per-session breakdown
    if results.session_results:
        print(f"\\n📋 Session Breakdown:")
        for i, session in enumerate(results.session_results, 1):
            success_rate = (
                (session.messages_successful / session.messages_sent * 100)
                if session.messages_sent > 0
                else 0
            )
            print(
                f"   Session {i}: {session.messages_successful}/{session.messages_sent} messages ({success_rate:.1f}%), "
                f"Avg: {session.avg_response_time:.2f}s"
            )

    # Error analysis
    if results.unique_errors:
        print(f"\\n❌ Error Analysis ({len(results.unique_errors)} unique errors):")
        for error_type, count in sorted(
            results.error_count_by_type.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"   {error_type}: {count} occurrences")

    # Performance assessment
    print(f"\\n🎯 Performance Assessment:")
    if results.overall_success_rate >= 95:
        print("   ✅ EXCELLENT - System handles concurrent load very well")
    elif results.overall_success_rate >= 80:
        print("   ⚠️  GOOD - System mostly stable under concurrent load")
    elif results.overall_success_rate >= 50:
        print("   ⚠️  POOR - Significant issues under concurrent load")
    else:
        print("   ❌ CRITICAL - System struggles with concurrent load")

    if results.total_messages_successful > 0:
        if results.messages_per_second > 2:
            print("   ⚡ High throughput - Good concurrent processing")
        elif results.messages_per_second > 1:
            print("   🐌 Moderate throughput - Acceptable concurrent processing")
        else:
            print("   🐢 Low throughput - Poor concurrent processing")

        if results.response_time_p95 < 10:
            print("   📈 Consistent response times under load")
        else:
            print("   📉 Variable response times under load")


def save_parallel_results_to_json(results: ParallelStressTestResults, filename: str):
    """Save parallel test results to JSON file."""
    results_dict = {
        "config": asdict(results.config),
        "start_time": results.start_time.isoformat(),
        "end_time": results.end_time.isoformat(),
        "total_duration": results.total_duration,
        "project_id": results.project_id,
        "session_results": [asdict(s) for s in results.session_results],
        "all_message_results": [asdict(m) for m in results.all_message_results],
        "total_sessions_created": results.total_sessions_created,
        "total_sessions_successful": results.total_sessions_successful,
        "total_messages_sent": results.total_messages_sent,
        "total_messages_successful": results.total_messages_successful,
        "overall_success_rate": results.overall_success_rate,
        "session_success_rate": results.session_success_rate,
        "message_success_rate": results.message_success_rate,
        "avg_response_time": results.avg_response_time,
        "min_response_time": results.min_response_time,
        "max_response_time": results.max_response_time,
        "response_time_p95": results.response_time_p95,
        "response_time_p99": results.response_time_p99,
        "peak_concurrent_sessions": results.peak_concurrent_sessions,
        "total_chunks_received": results.total_chunks_received,
        "total_data_transferred": results.total_data_transferred,
        "messages_per_second": results.messages_per_second,
        "unique_errors": results.unique_errors,
        "error_count_by_type": results.error_count_by_type,
    }

    with open(filename, "w") as f:
        json.dump(results_dict, f, indent=2)

    print(f"📄 Parallel test results saved to: {filename}")


async def main():
    """Main function to run the parallel stress test."""
    parser = argparse.ArgumentParser(
        description="Parallel stress test for send_message endpoint"
    )
    parser.add_argument(
        "--host", default="http://localhost:8000", help="API host (default: localhost)"
    )
    parser.add_argument("--user", default="user1", help="User ID (default: user1)")
    parser.add_argument(
        "--sessions",
        type=int,
        default=15,
        help="Number of concurrent sessions (default: 15)",
    )
    parser.add_argument(
        "--messages-per-session",
        type=int,
        default=1,
        help="Messages per session (default: 1)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--session-stagger",
        type=float,
        default=0.5,
        help="Delay between session creation (default: 0.5)",
    )
    parser.add_argument(
        "--message-stagger",
        type=float,
        default=0.2,
        help="Max random delay before sending messages (default: 0.2)",
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
            config = ParallelTestConfig(**config_data)
        else:
            print(f"❌ Configuration file not found: {args.config}")
            return
    else:
        config = ParallelTestConfig(
            host=args.host,
            user_id=args.user,
            num_sessions=args.sessions,
            messages_per_session=args.messages_per_session,
            timeout=args.timeout,
            stagger_session_creation=args.session_stagger,
            stagger_message_sending=args.message_stagger,
            cleanup_after_test=not args.no_cleanup,
        )

    # Run the parallel test
    tester = ParallelMessageStressTester(config)
    try:
        results = await tester.run_send_message_parallel_stress_test()

        # Print results
        print_parallel_test_results(results)

        # Save to file
        if args.output:
            save_parallel_results_to_json(results, args.output)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"send_message_parallel_stress_test_results_{timestamp}.json"
            save_parallel_results_to_json(results, filename)

    except KeyboardInterrupt:
        print("\\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
