# ERP System Architecture & Engineering Requirements

## Project Goal

Build an enterprise-grade ERP platform using Python/Django that is:

* Easy to maintain after deployment
* Easy to debug remotely
* Easy for AI agents (Claude Code) to understand and modify
* Safe for customer-hosted deployments
* Privacy-preserving
* Highly modular
* Fault-tolerant
* Resilient to infrastructure failures
* Scalable to 5000+ users
* Deployable on Windows Server environments
* Designed for long-term evolution without breaking existing functionality

---

# Deployment Model

## Customer Deployment

* Single-tenant deployment per customer
* Customer owns and hosts all data
* Deployment may span multiple machines
* Windows Server must be supported
* No dependency on cloud-only services

## Recommended Infrastructure

### Machine 1

Application Layer

* Django API
* Background workers
* Scheduler
* Monitoring services

### Machine 2

Database Layer

* PostgreSQL
* Backup services

### Machine 3

Document Storage Layer

* File storage
* Attachments
* Generated documents
* Import/export staging

Infrastructure failures must never corrupt customer data.

---

# Technology Stack

## Backend

* Python 3.13+
* Django
* Django REST Framework
* Pydantic
* Celery
* Redis
* PostgreSQL

## Frontend

* React
* TypeScript

## Architecture Style

Use:

* Modular Monolith

Do NOT use:

* Distributed Microservices

Reason:

* Easier maintenance
* Easier deployment
* Easier debugging
* Easier AI-assisted support

---

# Core ERP Modules

Initial modules:

* Authentication
* User Management
* Forms Builder
* Workflow Engine
* CRM
* HR
* Inventory
* Accounting
* Manufacturing
* Document Management
* Notifications
* Imports
* Exports
* Reporting
* Audit Trail
* Monitoring

---

# Modular Architecture Requirements

Each module must be isolated.

Example:

erp/
├── core/
├── auth/
├── forms/
├── workflow/
├── crm/
├── hr/
├── inventory/
├── accounting/
├── manufacturing/
├── documents/
├── notifications/
├── imports/
├── exports/
├── reporting/
├── audit/
└── monitoring/

Each module must contain:

module/
├── api/
├── domain/
├── services/
├── repositories/
├── contracts/
├── events/
├── tests/
└── docs/

Modules must not access internal implementation details of other modules.

Communication between modules must happen only through:

* Public contracts
* Events
* Service interfaces

---

# Fault Isolation Requirements

Errors in one module must not crash unrelated modules.

Examples:

Forms failure:

* Must not break CRM
* Must not break Inventory
* Must not break Accounting

Workflow failure:

* Must not break Forms
* Must not break Documents

Reporting failure:

* Must not break operational transactions

Every module must contain:

* Error boundaries
* Exception isolation
* Graceful degradation

Failures must remain localized.

---

# Event-Driven Communication

Modules communicate using domain events.

Examples:

InventoryUpdated
InvoiceCreated
EmployeeCreated
WorkflowStarted
DocumentUploaded

Consumers subscribe to events.

A failing subscriber must not affect the publisher.

Example:

Inventory publishes event.

Workflow listener crashes.

Inventory operation still succeeds.

---

# Database Safety Requirements

## Rule 1

No direct database access from business logic.

Use:

* Repository pattern

Never spread raw SQL across modules.

---

## Rule 2

All write operations must use transactions.

Use atomic operations for:

* Inventory changes
* Accounting entries
* Workflow state changes
* Form submissions

---

## Rule 3

Automatic rollback on failure.

Partial writes are forbidden.

---

## Rule 4

Code and data must be separated.

Application updates must never directly modify customer data without controlled migrations.

---

# Migration Requirements

All migrations must support:

* Validation
* Rollback
* Dry-run mode
* Backup verification

Deployment flow:

1. Backup
2. Validate
3. Deploy
4. Verify
5. Activate

Never deploy directly without rollback capability.

---

# Privacy-Preserving Support System

Customer data must never leave customer infrastructure.

Remote support must work without access to:

* Customer records
* Employee data
* Financial data
* Documents
* Personal information

Diagnostic packages may contain:

* Error ID
* Module name
* File name
* Function name
* Stack trace
* Version
* Correlation ID
* Configuration hash

Diagnostic packages must never contain business data.

---

# Error Identification System

Every error must generate:

* Error ID
* Module ID
* Correlation ID

Example:

ERR-2026-001245

Generated metadata:

* Module
* File
* Function
* Line
* Version
* Stack trace

This allows remote diagnosis without exposing data.

---

# Claude Code Compatibility Requirements

The codebase must be optimized for AI-assisted maintenance.

Generate automatically:

architecture/
├── modules.md
├── dependencies.md
├── events.md
├── database.md
├── api.md
├── workflows.md
└── error-catalog.md

---

# Error Catalog

Every known error must have:

Error Code
Description
Module
File
Function
Possible Causes
Recommended Fix

Example:

WF-001

Description:
Approval node not found

Module:
Workflow

File:
approval_engine.py

Function:
execute_node()

---

# Correlation ID Requirements

Every operation must generate a correlation ID.

Examples:

* API request
* Workflow execution
* Import job
* Export job
* Report generation

The correlation ID must appear in:

* Logs
* Error reports
* Audit records
* Monitoring dashboards

This enables full traceability.

---

# Structured Logging

Use structured logs only.

Every log entry should include:

* Timestamp
* Module
* Function
* Correlation ID
* Severity
* Error Code

Example:

{
"module":"workflow",
"function":"execute_node",
"error":"WF-001",
"correlation_id":"ABC123"
}

Avoid unstructured text logs.

---

# Monitoring Requirements

Built-in monitoring dashboard required.

Must monitor:

* Database
* Redis
* Background workers
* Queue status
* Storage
* Workflow engine
* Import engine
* Export engine

Status levels:

* Healthy
* Warning
* Critical

---

# Health Check Requirements

Provide system health endpoints.

Examples:

/health
/system-check

Must report:

* DB connectivity
* Queue connectivity
* Storage connectivity
* Worker health
* Service health

---

# Import Engine Requirements

Imports must be resumable.

Track:

* Job ID
* Current status
* Last processed record
* Progress percentage

If interrupted by:

* Power outage
* Server restart
* Application crash
* Network failure

The import must continue from the last checkpoint.

Never restart from the beginning unless explicitly requested.

---

# Export Engine Requirements

Exports must also support:

* Resume
* Retry
* Recovery

Partial exports must continue after interruption.

---

# Background Job Requirements

All long-running operations must use a job queue.

Examples:

* Imports
* Exports
* Reporting
* Notifications
* Workflow execution

Jobs must be:

* Retryable
* Observable
* Recoverable

---

# Infrastructure Failure Requirements

Application failures must never corrupt:

* Database
* Documents
* Audit logs

Examples:

Power outage:

* Recover safely

Server restart:

* Recover safely

Worker crash:

* Recover safely

Network interruption:

* Recover safely

Unexpected shutdown:

* Recover safely

---

# Audit Trail Requirements

Every business action must be auditable.

Track:

* User
* Timestamp
* Action
* Entity
* Result
* Correlation ID

Audit data must be immutable.

---

# Module Versioning

Every module must have independent versioning.

Example:

Forms 2.1.4
Workflow 1.8.2
CRM 3.0.1

This enables targeted patching.

---

# Hot Fix Requirements

Fixes should target individual modules whenever possible.

A workflow fix must not require:

* CRM redeployment
* Inventory redeployment
* Accounting redeployment

Module boundaries must support isolated updates.

---

# Testing Requirements

Every module must include:

* Unit tests
* Integration tests
* Contract tests

Critical business flows must include end-to-end tests.

---

# Documentation Requirements

Every module must contain:

* Purpose
* Public APIs
* Events emitted
* Events consumed
* Dependencies
* Error catalog
* Data ownership

Documentation must be maintained automatically where possible.

---

# Non-Negotiable Principle

Every feature, module, API endpoint, workflow action, import/export operation, background job, and infrastructure process must:

* Be traceable
* Generate structured logs
* Support correlation IDs
* Expose health status
* Produce privacy-safe diagnostics
* Support safe recovery
* Prevent data corruption
* Remain understandable to Claude Code and future AI maintenance systems

The architecture must prioritize maintainability, observability, fault isolation, recoverability, privacy, and long-term evolution over short-term implementation speed.
