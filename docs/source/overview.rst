Overview
========

The Platform repository is the central hub for shared services and packages
used across all applications in the ecosystem.

Purpose
-------

- **Code Reuse**: Shared functionality across BFAgent, TravelBeat, and other apps
- **Consistency**: Unified interfaces for common operations
- **Maintainability**: Single source of truth for core services

Packages
--------

creative-services
~~~~~~~~~~~~~~~~~

AI-powered creative writing services with:

- Unified LLM client (OpenAI, Anthropic, Groq, Ollama)
- Dynamic tier-based model selection
- Usage tracking and cost management
- Django adapters for ORM integration

Ecosystem
---------

.. code-block:: text

   ┌─────────────────────────────────────────────────────────┐
   │                      Platform                           │
   │  ┌─────────────────────────────────────────────────┐   │
   │  │              creative-services                   │   │
   │  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │   │
   │  │  │LLMClient │ │LLMRegistry│ │  UsageTracker   │ │   │
   │  │  └──────────┘ └──────────┘ └──────────────────┘ │   │
   │  └─────────────────────────────────────────────────┘   │
   └─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │   BFAgent   │ │ TravelBeat  │ │   MCP-Hub   │
   │  (Django)   │ │  (Django)   │ │   (MCP)     │
   └─────────────┘ └─────────────┘ └─────────────┘

Installation
------------

Install creative-services in your project:

.. code-block:: bash

   # From local development
   pip install -e /path/to/platform/packages/creative-services
   
   # With optional providers
   pip install -e "/path/to/platform/packages/creative-services[openai,anthropic]"
