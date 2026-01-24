"""Tests for script executor."""

import pytest

from wren_backend.core.executor import Executor
from wren_backend.models.run import RunStatus


@pytest.mark.asyncio
async def test_execute_simple_script(executor):
    """Test executing a simple script."""
    script = '''
def hello():
    print("Hello, world!")
    return "done"
'''
    result = await executor.execute(script, "hello")

    assert result.status == RunStatus.SUCCESS
    assert result.exit_code == 0
    assert "Hello, world!" in result.stdout


@pytest.mark.asyncio
async def test_execute_script_with_return_value(executor):
    """Test that return values are printed."""
    script = '''
def get_data():
    return {"key": "value"}
'''
    result = await executor.execute(script, "get_data")

    assert result.status == RunStatus.SUCCESS
    assert "key" in result.stdout


@pytest.mark.asyncio
async def test_execute_script_with_error(executor):
    """Test executing a script that raises an error."""
    script = '''
def failing():
    raise ValueError("Something went wrong")
'''
    result = await executor.execute(script, "failing")

    assert result.status == RunStatus.FAILED
    assert result.exit_code == 1
    assert "ValueError" in result.stderr
    assert "Something went wrong" in result.stderr


@pytest.mark.asyncio
async def test_execute_script_with_syntax_error(executor):
    """Test executing a script with syntax errors."""
    script = '''
def broken(
    print("missing closing paren"
'''
    result = await executor.execute(script, "broken")

    assert result.status == RunStatus.FAILED
    assert "SyntaxError" in result.stderr


@pytest.mark.asyncio
async def test_execute_with_env_vars(executor):
    """Test that environment variables are passed to script."""
    script = '''
import os
def check_env():
    val = os.environ.get("TEST_VAR", "not found")
    print(f"TEST_VAR={val}")
'''
    result = await executor.execute(
        script, "check_env", env={"TEST_VAR": "hello123"}
    )

    assert result.status == RunStatus.SUCCESS
    assert "TEST_VAR=hello123" in result.stdout


@pytest.mark.asyncio
async def test_execute_timeout():
    """Test that scripts timeout correctly."""
    executor = Executor(timeout_seconds=1)
    script = '''
import time
def slow():
    time.sleep(10)
'''
    result = await executor.execute(script, "slow")

    assert result.status == RunStatus.TIMEOUT
    assert "timed out" in result.error_message.lower()


@pytest.mark.asyncio
async def test_execute_undefined_function(executor):
    """Test executing a non-existent function."""
    script = '''
def existing():
    pass
'''
    result = await executor.execute(script, "nonexistent")

    assert result.status == RunStatus.FAILED
    assert "nonexistent" in result.stderr.lower() or result.exit_code != 0


@pytest.mark.asyncio
async def test_execute_script_with_imports(executor):
    """Test executing a script with standard library imports."""
    script = '''
import json
import datetime

def process():
    data = {"timestamp": str(datetime.datetime.now())}
    print(json.dumps(data))
'''
    result = await executor.execute(script, "process")

    assert result.status == RunStatus.SUCCESS
    assert "timestamp" in result.stdout


@pytest.mark.asyncio
async def test_execute_script_stderr(executor):
    """Test that stderr is captured separately."""
    script = '''
import sys

def with_stderr():
    print("stdout message")
    print("stderr message", file=sys.stderr)
'''
    result = await executor.execute(script, "with_stderr")

    assert result.status == RunStatus.SUCCESS
    assert "stdout message" in result.stdout
    assert "stderr message" in result.stderr
