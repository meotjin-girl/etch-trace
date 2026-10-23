# Copyright 2026 TRACE contributors
# Message reducer signature for the application's typed checkpoint messages.

from langchain_core.messages import AnyMessage

def add_messages(left: list[AnyMessage], right: list[AnyMessage]) -> list[AnyMessage]: ...
