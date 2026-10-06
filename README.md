# Python Async Microservice Example

A small, anonymized example of an asynchronous Python service for integrating with external APIs.

The repository demonstrates patterns I use when working with API-driven backend services: asynchronous I/O, object-oriented design, authentication, retries, error handling and task orchestration.

## What this example demonstrates

* **Asynchronous I/O** with `asyncio` and `aiohttp`
* **OOP and separation of responsibilities**
* **External API integration**
* **Authentication** with OAuth 2.0 / JWT
* **Task orchestration** and status tracking
* **Retry logic** implemented with decorators
* **Custom exceptions**
* **Structured logging**
* Handling API errors and unsuccessful requests

## Project structure

```text
code-samples/
├── example_quest.py
├── social_quest_handler.py
└── README.md
```

The example is intentionally small. The focus is on the implementation patterns rather than on building a complete standalone application.

## Technologies

* Python 3.12+
* asyncio
* aiohttp
* REST API
* OAuth 2.0 / JWT

## Context

This code is based on a production microservice developed for a social-platform automation project.

The public version has been cleaned and anonymized:

* sensitive project names were removed
* real API endpoints were replaced with placeholders
* credentials and other private data were removed
* the code was adapted to work as a standalone example

The repository is intended to demonstrate the structure and engineering approaches used in the original service, rather than reproduce the original project in full.
