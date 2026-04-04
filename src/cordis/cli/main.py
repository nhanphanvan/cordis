import typer

from cordis import __version__

app = typer.Typer(help="Cordis command line interface.")


@app.callback()
def main() -> None:
    """Cordis command group."""


@app.command()
def version() -> None:
    typer.echo(f"cordis {__version__}")
