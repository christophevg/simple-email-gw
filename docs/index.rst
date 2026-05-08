.. simple-email-gw documentation master file

Simple Email Gateway
====================

.. image:: https://img.shields.io/pypi/v/simple-email-gw.svg
   :target: https://pypi.org/project/simple-email-gw/
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/simple-email-gw.svg
   :target: https://pypi.org/project/simple-email-gw/
   :alt: Python versions

.. image:: https://img.shields.io/github/license/christophevg/simple-email-gw.svg
   :target: https://github.com/christophevg/simple-email-gw/blob/main/LICENSE
   :alt: License

.. image:: https://github.com/christophevg/simple-email-gw/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/christophevg/simple-email-gw/actions/workflows/ci.yml
   :alt: CI

.. image:: https://img.shields.io/badge/code%20style-ruff-blue.svg
   :target: https://github.com/astral-sh/ruff
   :alt: Code style: ruff

.. image:: https://img.shields.io/badge/type%20checked-mypy-blue.svg
   :target: https://mypy.readthedocs.io/
   :alt: Type checked: mypy

.. image:: https://img.shields.io/readthedocs/simple-email-gw.svg
   :target: https://simple-email-gw.readthedocs.io/
   :alt: Read the Docs

.. image:: https://img.shields.io/badge/workflow-agentic-blueviolet?style=flat-square
   :target: https://christophe.vg/about/Coding-Agent
   :alt: Agentic workflow

A simple email gateway with IMAP/SMTP clients, connection pooling, and MCP server for AI assistant integration.

.. note::

   This package provides both async and sync APIs. Async clients are recommended for async applications. Use sync wrapper clients (SyncIMAPClient, SyncSMTPClient) for simpler synchronous code.

**Why Simple Email Gateway?**

- **Async-first**: Built on aioimaplib and aiosmtplib for modern async Python
- **Sync support**: SyncIMAPClient and SyncSMTPClient wrappers for simpler synchronous usage
- **Production-ready**: Connection pooling, rate limiting, audit logging
- **Security-focused**: TLS 1.2+ minimum, CRLF injection prevention, recipient whitelisting
- **AI-ready**: MCP server for seamless AI assistant integration
- **Well-tested**: Comprehensive test suite with type checking

This project was built using an agentic workflow — for the full story, see :doc:`rationale`.

Quick Links
-----------

- `GitHub Repository <https://github.com/christophevg/simple-email-gw>`_
- `PyPI Package <https://pypi.org/project/simple-email-gw/>`_
- `Report an Issue <https://github.com/christophevg/simple-email-gw/issues>`_
- :doc:`installation` - Get started in minutes
- :doc:`rationale` - Why this project exists

Features
--------

- Async IMAP and SMTP clients (aioimaplib, aiosmtplib)
- Connection pooling with automatic management
- Token bucket rate limiting
- Audit logging for security compliance
- CRLF injection prevention
- Recipient whitelist enforcement
- TLS 1.2+ minimum encryption
- MCP server for AI assistant integration

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   rationale
   sync-clients
   api

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   configuration
   security
   mcp-tools

.. toctree::
   :maxdepth: 2
   :caption: Development

   development

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`