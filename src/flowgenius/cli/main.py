"""
FlowGenius Main CLI

This module defines the main CLI group and entry point for FlowGenius commands.
"""

import click
from .wizard import wizard
from .new import new, create


@click.group()
@click.version_option(version="0.1.0", prog_name="flowgenius")
def cli() -> None:
    """
    FlowGenius: AI-assisted learning assistant that eliminates research paralysis.
    
    FlowGenius helps you create structured, adaptive learning plans from freeform
    learning goals, saving everything as local Markdown files for long-term retention.
    """
    pass


# Register subcommands
cli.add_command(wizard)
cli.add_command(new)
cli.add_command(create)


def main() -> None:
    """Main entry point for the FlowGenius CLI."""
    cli() 