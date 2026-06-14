"""ERP modules root (modular monolith).

Every subpackage is an isolated Django app. Modules communicate only through public
contracts, service interfaces, and domain events — never by importing another module's
internal implementation details.
"""
