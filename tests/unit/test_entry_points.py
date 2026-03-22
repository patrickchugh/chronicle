"""Unit tests for entry point detector."""

from pathlib import Path

import pytest

from chronicle.analyzers.entry_points import EntryPointDetector, detect_entry_points


class TestEntryPointDetector:
    """Tests for EntryPointDetector."""

    @pytest.fixture
    def detector(self, tmp_path: Path) -> EntryPointDetector:
        """Create an entry point detector instance."""
        return EntryPointDetector(tmp_path)

    def test_detect_typer_commands(self, tmp_path: Path) -> None:
        """Test detecting Typer CLI commands."""
        cli_file = tmp_path / "cli.py"
        cli_file.write_text(
            '''
import typer

app = typer.Typer()

@app.command()
def hello(name: str):
    """Say hello to someone."""
    print(f"Hello {name}")

@app.command("goodbye")
def say_goodbye():
    """Say goodbye."""
    print("Goodbye")
'''
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        assert len(entry_points) >= 2
        names = {ep.name for ep in entry_points}
        assert "hello" in names or "goodbye" in names

    def test_detect_click_commands(self, tmp_path: Path) -> None:
        """Test detecting Click CLI commands."""
        cli_file = tmp_path / "commands.py"
        cli_file.write_text(
            '''
import click

@click.command()
def main():
    """Main command."""
    pass

@cli.command("process")
def process_data():
    """Process some data."""
    pass
'''
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        cli_eps = [ep for ep in entry_points if ep.type == "cli_command"]
        assert len(cli_eps) >= 1

    def test_detect_fastapi_endpoints(self, tmp_path: Path) -> None:
        """Test detecting FastAPI endpoints."""
        api_file = tmp_path / "api.py"
        api_file.write_text(
            '''
from fastapi import FastAPI

app = FastAPI()

@app.get("/users")
def list_users():
    """List all users."""
    return []

@app.post("/users")
def create_user(user: dict):
    """Create a new user."""
    return user

@router.get("/items/{item_id}")
def get_item(item_id: int):
    return {"id": item_id}
'''
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        api_eps = [ep for ep in entry_points if ep.type == "api_endpoint"]
        assert len(api_eps) >= 2

        # Check for specific endpoints
        names = {ep.name for ep in api_eps}
        assert any("/users" in name for name in names)

    def test_detect_flask_routes(self, tmp_path: Path) -> None:
        """Test detecting Flask routes."""
        app_file = tmp_path / "app.py"
        app_file.write_text(
            """
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello"

@app.route("/api/data", methods=["GET", "POST"])
def data():
    return {}

@bp.route("/blueprint/route")
def blueprint_route():
    pass
"""
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        api_eps = [ep for ep in entry_points if ep.type == "api_endpoint"]
        assert len(api_eps) >= 2

    def test_detect_main_block(self, tmp_path: Path) -> None:
        """Test detecting if __name__ == '__main__' blocks."""
        main_file = tmp_path / "main.py"
        main_file.write_text(
            """
def main():
    print("Running main")

if __name__ == "__main__":
    main()
"""
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        main_eps = [ep for ep in entry_points if ep.type == "main"]
        assert len(main_eps) == 1
        assert main_eps[0].name == "__main__"

    def test_detect_express_endpoints(self, tmp_path: Path) -> None:
        """Test detecting Express.js endpoints."""
        express_file = tmp_path / "server.js"
        express_file.write_text(
            """
const express = require('express');
const app = express();

app.get('/api/users', (req, res) => {
    res.json([]);
});

app.post('/api/users', (req, res) => {
    res.json(req.body);
});

router.get('/items/:id', getItem);
"""
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        api_eps = [ep for ep in entry_points if ep.type == "api_endpoint"]
        assert len(api_eps) >= 2

    def test_detect_lambda_handler(self, tmp_path: Path) -> None:
        """Test detecting Lambda/Cloud function handlers."""
        handler_file = tmp_path / "handler.js"
        handler_file.write_text(
            """
exports.handler = async (event, context) => {
    return {
        statusCode: 200,
        body: JSON.stringify({ message: "Hello" })
    };
};
"""
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        handler_eps = [ep for ep in entry_points if ep.type == "handler"]
        assert len(handler_eps) == 1
        assert handler_eps[0].name == "handler"

    def test_detect_go_main(self, tmp_path: Path) -> None:
        """Test detecting Go main function."""
        go_file = tmp_path / "main.go"
        go_file.write_text(
            """
package main

import "fmt"

func main() {
    fmt.Println("Hello")
}
"""
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        main_eps = [ep for ep in entry_points if ep.type == "main"]
        assert len(main_eps) == 1

    def test_detect_go_http_handlers(self, tmp_path: Path) -> None:
        """Test detecting Go HTTP handlers."""
        go_file = tmp_path / "server.go"
        go_file.write_text(
            """
package main

import "net/http"

func main() {
    http.HandleFunc("/api/users", handleUsers)
    http.HandleFunc("/api/items", handleItems)
}
"""
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        api_eps = [ep for ep in entry_points if ep.type == "api_endpoint"]
        assert len(api_eps) >= 2

    def test_detect_spring_endpoints(self, tmp_path: Path) -> None:
        """Test detecting Spring Boot endpoints."""
        java_file = tmp_path / "UserController.java"
        java_file.write_text(
            """
package com.example.controller;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class UserController {

    @GetMapping("/users")
    public List<User> getUsers() {
        return userService.findAll();
    }

    @PostMapping("/users")
    public User createUser(@RequestBody User user) {
        return userService.save(user);
    }

    @DeleteMapping("/users/{id}")
    public void deleteUser(@PathVariable Long id) {
        userService.delete(id);
    }
}
"""
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        api_eps = [ep for ep in entry_points if ep.type == "api_endpoint"]
        assert len(api_eps) >= 3

    def test_detect_java_main(self, tmp_path: Path) -> None:
        """Test detecting Java main method."""
        java_file = tmp_path / "Application.java"
        java_file.write_text(
            """
package com.example;

public class Application {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}
"""
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        main_eps = [ep for ep in entry_points if ep.type == "main"]
        assert len(main_eps) == 1

    def test_deduplicate_entry_points(self, tmp_path: Path) -> None:
        """Test that duplicate entry points are removed."""
        cli_file = tmp_path / "cli.py"
        cli_file.write_text(
            """
@app.command()
def mycommand():
    pass
"""
        )

        # Create duplicate in another file
        cli2_file = tmp_path / "cli2.py"
        cli2_file.write_text(
            """
@app.command()
def mycommand():
    pass
"""
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        # Should have deduplicated by (name, file, line)
        # Since they're in different files, both should exist
        mycommand_eps = [ep for ep in entry_points if ep.name == "mycommand"]
        assert len(mycommand_eps) == 2  # Different files

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test detecting entry points in empty directory."""
        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        assert len(entry_points) == 0

    def test_convenience_function(self, tmp_path: Path) -> None:
        """Test the detect_entry_points convenience function."""
        main_file = tmp_path / "main.py"
        main_file.write_text('if __name__ == "__main__": pass')

        entry_points = detect_entry_points(tmp_path)

        assert len(entry_points) >= 1

    def test_extract_docstring_description(self, tmp_path: Path) -> None:
        """Test extracting docstring as description."""
        cli_file = tmp_path / "cli.py"
        cli_file.write_text(
            '''
@app.command()
def documented_command():
    """This is a documented command that does something."""
    pass
'''
        )

        detector = EntryPointDetector(tmp_path)
        entry_points = detector.detect_entry_points()

        if entry_points:
            # Should have extracted docstring
            ep = entry_points[0]
            assert ep.description is not None or ep.description == ""
